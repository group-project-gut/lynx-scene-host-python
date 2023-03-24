import asyncio
import time

from aioprocessing import AioPipe, AioProcess
from aioprocessing.connection import AioConnection
from attr import dataclass
from fastapi import FastAPI
from lynx.common.object import Object
from lynx.common.scene import Scene
from pydantic import BaseModel


def execution_runtime(pipe: AioConnection, object_id: int):
    from lynx.common.actions.move import Move
    from lynx.common.vector import Vector

    while (True):
        scene_serialzied = pipe.recv()
        scene = Scene.deserialize(scene_serialzied)
        action = Move(object_id=object_id, vector=Vector(10, 10))
        time.sleep(1)
        pipe.send([action.serialize()])


@dataclass
class ProcessData():
    process: AioProcess = None
    pipe: AioConnection = None


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
                parent_conn, child_conn = AioPipe()
                p = AioProcess(target=execution_runtime,
                               args=(child_conn, object.id,))
                p.start()
                self.processes[object.id] = ProcessData(
                    process=p, pipe=parent_conn)

            return {"serialized_object": object.serialize()}

        async def run_object(serialized_scene: str, process_data: ProcessData):
            await process_data.pipe.coro_send(serialized_scene)
            return await process_data.pipe.coro_recv()

        @self.app.post("/tick")
        async def tick():
            serialized_scene = self.scene.serialize()
            tasks = []
            for process_data in self.processes.values():
                task = asyncio.create_task(
                    run_object(serialized_scene, process_data))
                tasks.append(task)

            actions = await asyncio.gather(*tasks)
            return {"actions": actions}
        
        @self.app.post("/tick_sync")
        async def tick_sync():
            actions = []
            serialized_scene = self.scene.serialize()

            # Sequential approach
            start = time.perf_counter()
            for process_data in self.processes.values():
                process_data.pipe.send(serialized_scene)
                actions += process_data.pipe.recv()
            stop = time.perf_counter()
            seq_time = stop - start

            return {"actions": actions}
