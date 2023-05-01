import asyncio
import itertools
import json
from typing import Dict, List, Optional, Union

import opensimplex
from aioprocessing import AioPipe, AioProcess
from aioprocessing.connection import AioConnection
from attr import dataclass
from fastapi import FastAPI
from lynx.common.enitity import Entity
from lynx.common.object import Object
from lynx.common.scene import Scene
from lynx.common.vector import Vector
from pydantic import BaseModel

from src.execution_runtime import execution_runtime


@dataclass
class ProcessData:
    process: AioProcess = None
    pipe: AioConnection = None


def calculate_deltas(from_tick_number: int, to_tick_number: int, actions_in_ticks: List[List[Optional[str]]]) -> List[Optional[str]]:
    deltas = []
    for actions_in_tick in actions_in_ticks[(from_tick_number + 1):(to_tick_number + 1)]:
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
                return {"tick_number": self.tick_number, "deltas": json.dumps(calculate_deltas(tick_number, self.tick_number, self.applied_actions))}

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

        async def fetch_actions() -> List[Entity]:
            future_actions = []
            for process_data in self.processes.values():
                future_actions.append(process_data.pipe.coro_recv())

            serialized_actions = await asyncio.gather(*future_actions)
            return [Entity.deserialize(serialized_action) for serialized_action in serialized_actions]

        def apply_actions(actions: List[Entity]) -> List[str]:
            # Not sure if we should use `str` or `Action`
            applied_actions: List[str] = []
            for action in actions:
                if action.satisfies_requirements(self.scene):
                    action.apply(self.scene)
                    applied_actions.append(action.serialize())
                else:
                    # Log that requirements were not satisfied
                    pass

            return applied_actions

        async def send_scene():
            serialized_scene = self.scene.serialize()
            future_sends = []
            for process_data in self.processes.values():
                future_sends.append(process_data.pipe.coro_send(serialized_scene))

            await asyncio.gather(*future_sends) 

        @self.app.post("/tick")
        async def tick():
            actions = await fetch_actions()
            applied_actions = apply_actions(actions)
            self.applied_actions.append(applied_actions)
            self.tick_number += 1
            await send_scene()

            return {"tick_number": self.tick_number}
        
        @self.app.post("/clear")
        async def clear():
            self.scene = Scene()

        @self.app.post("/populate")
        async def populate():
            await clear()
            opensimplex.seed(1234)
            id = 0
            for (x,y) in itertools.product(range(100), range(10)):
                self.scene.add_entity(Object(id=id, name="Grass", position=Vector(x,y), walkable=True))
                id += 1
                if opensimplex.noise2(x,y) > .3:
                    self.scene.add_entity(Object(id=id, name="Tree", position=Vector(x,y), walkable=False))
                    id += 1

            return {"id": id}
        
        @self.app.post('/teardown')
        async def teardown():
            self.teardown()

    # Teardown is necessary to close all subprocesses
    # I tired using FastAPI `lifespan` but it might not work
    # with apps that are not top-level
    def teardown(self):
        for process_data in self.processes.values():
            process_data.process.terminate()

