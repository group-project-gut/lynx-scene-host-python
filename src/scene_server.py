from multiprocessing.connection import Connection
from attr import dataclass
from fastapi import FastAPI
from lynx.common.scene import Scene
from lynx.common.object import Object
from lynx.common.actions.move import Move
from lynx.common.vector import Vector
from pydantic import BaseModel
from multiprocessing import Pipe, Process


def execution_runtime(pipe: Connection, object_id: int):
    scene_serialzied = pipe.recv()
    scene = Scene.deserialize(scene_serialzied)
    action = Move(object_id=1, vector=Vector(10, 10))
    pipe.send([action.serialize()])


@dataclass
class ProcessData():
    process: Process = None
    pipe: Connection = None


class SceneServer():
    def __init__(self) -> None:
        self.app = FastAPI()
        self.scene = Scene()
        self.processes = {}

        @self.app.get("/")
        async def get():
            return {"scene": self.scene.serialize()}

        class AddObjectRequest(BaseModel):
            serialized_object: str

        @self.app.post("/add_object")
        async def add(r: AddObjectRequest):
            object = Object.deserialize(r.serialized_object)
            self.scene.add_entity(object)

            if object.tick != "":
                parent_conn, child_conn = Pipe()
                p = Process(target=execution_runtime,
                            args=(child_conn, object.id,))
                p.start()
                self.processes[object.id] = ProcessData(
                    process=p, pipe=parent_conn)

            return {"serialized_object": object.serialize()}

        @self.app.post("/tick")
        async def tick():
            actions = []
            # I guess it should be async but no idea how it works with send and recv
            for process_data in self.processes.values():
                serialized_scene = self.scene.serialize()
                process_data.pipe.send(serialized_scene)
                actions += process_data.pipe.recv()

            return {"actions": actions}
