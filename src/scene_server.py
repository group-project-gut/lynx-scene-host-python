import asyncio
import time
from typing import List, Dict, Union

from aioprocessing import AioPipe, AioProcess
from aioprocessing.connection import AioConnection
from attr import dataclass
from fastapi import FastAPI
from lynx.common.object import Object
from lynx.common.scene import Scene
from lynx.common.enitity import Entity
from pydantic import BaseModel


def execution_runtime(pipe: AioConnection, object_id: int):
    from lynx.common.actions.move import Move
    from lynx.common.vector import Vector
    from lynx.common.actions.action import Action

    scene_serialized = pipe.recv()
    scene: Scene = Scene.deserialize(scene_serialized)

    def send(action: Action):
        pipe.send(action.serialize())
        scene_serialized = pipe.recv()
        scene = Scene.deserialize(scene_serialized)

    builtins = {
        'move': lambda vector: send(Move(object_id, vector)),
        'Vector': Vector,
    }

    while (True):
        # Sure, I know exec bad
        # pylint: disable=exec-used
        exec(
            scene.get_object_by_id(object_id).tick,
            {'__builtins__': builtins},
        )


@dataclass
class ProcessData:
    process: AioProcess = None
    pipe: AioConnection = None


def calculate_deltas(from_tick_number: int, to_tick_number: int, actions_in_ticks: List[List[Union[str]]]) -> List[List[str]]:
    deltas = []
    for actions_in_tick in actions_in_ticks[(from_tick_number + 1):to_tick_number]:
        deltas = deltas + actions_in_tick
    return deltas


class SceneServer:
    def __init__(self) -> None:
        self.app = FastAPI()
        self.scene = Scene()
        self.processes = {}
        self.tick_number = 0
        # each element represents actions applied in a consecutive tick
        # TODO change to states = {self.scene.hash(): [None]}
        self.applied_actions = [[]]

        @self.app.get("/")
        async def get(tick_number: int) -> Dict[str, Union[int, str, List[List[str]]]]:
            # if player has no scene or player tick number is incorrect
            # TODO remove tick number and use scene hash instead e.g. if player_scene_hash not in self.states.keys():
            if tick_number < 0 or tick_number > self.tick_number:
                return {"tick_number": self.tick_number, "scene": self.scene.serialize()}
            else:
                return {"tick_number": self.tick_number, "deltas": calculate_deltas(self.tick_number, tick_number, self.applied_actions)}

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
                
                # I'm not 100% sure if we should await it or not
                await parent_conn.coro_send(self.scene.serialize())
                self.processes[object.id] = ProcessData(
                    process=p, pipe=parent_conn)

            return {"serialized_object": object.serialize()}

        @self.app.post("/tick")
        async def tick():
            future_actions = []
            for process_data in self.processes.values():
                future_actions.append(process_data.pipe.coro_recv())

            serialized_actions = await asyncio.gather(*future_actions)

            # Apply changes
            for serialized_action in serialized_actions:
                action = Entity.deserialize(serialized_action)
                action.apply(self.scene)

            self.applied_actions.append(serialized_actions)
            self.tick_number += 1

            serialized_scene = self.scene.serialize()
            future_sends = []
            for process_data in self.processes.values():
                future_sends.append(process_data.pipe.coro_send(serialized_scene))

            await asyncio.gather(*future_sends)

            return {"scene": serialized_scene}

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
