#  __   __   __       __           __   __  ___      __      ___       __
# (__' /  ` |__ |\ | |__ ___ |__| /  \ (__'  |  ___ |__) \_/  |  |__| /  \ |\ |
# .__) \__, |__ | \| |__     |  | \__/ .__)  |      |     |   |  |  | \__/ | \|

import asyncio
from dataclasses import dataclass
import itertools
import json
from typing import Dict, List, Optional, Union
from fastapi import FastAPI

import opensimplex
from aioprocessing import AioPipe, AioProcess
from aioprocessing.connection import AioConnection
from lynx.common.enitity import Entity
from lynx.common.object import Object
from lynx.common.scene import Scene
from lynx.common.vector import Vector
from pydantic import BaseModel

from src.runtime import execution_runtime

#   _    __   __      __   __  ___          ___    __
#  /_\  |__) |__)    |  \ |__ |__  | |\ | |  |  | /  \ |\ |
# /   \ |    |       |__/ |__ |    | | \| |  |  | \__/ | \|

app = FastAPI()
scene = Scene()
processes = {}
tick_number = 0
# each element represents actions applied in a consecutive tick
# TODO change to states = {self.scene.hash(): [None]}
applied_actions = [[]]

#  __    _   ___   _       __  ___  __        __  ___       __   __  __
# |  \  /_\   |   /_\     (__'  |  |__) |  | /  `  |  |  | |__) |__ (__'
# |__/ /   \  |  /   \    .__)  |  |  \ \__/ \__,  |  \__/ |  \ |__ .__)


@dataclass
class ProcessData:
    process: AioProcess = None
    pipe: AioConnection = None


class AddObjectRequest(BaseModel):
    serialized_object: str

#       __      __   __  __      ___            __  ___    __        __
# |__| |__ |   |__) |__ |__)    |__  |  | |\ | /  `  |  | /  \ |\ | (__'
# |  | |__ |__ |    |__ |  \    |    \__/ | \| \__,  |  | \__/ | \| .__)


def calculate_deltas(from_tick_number: int, to_tick_number: int, actions_in_ticks: List[List[Optional[str]]]) -> List[Optional[str]]:
    deltas = []
    for actions_in_tick in actions_in_ticks[(from_tick_number + 1):(to_tick_number + 1)]:
        deltas = deltas + actions_in_tick
    return deltas


async def fetch_actions() -> List[Entity]:
    future_actions = []
    for process_data in processes.values():
        future_actions.append(process_data.pipe.coro_recv())

    serialized_actions = await asyncio.gather(*future_actions)
    return [Entity.deserialize(serialized_action) for serialized_action in serialized_actions]


def apply_actions(actions: List[Entity]) -> List[str]:
    # Not sure if we should use `str` or `Action`
    applied_actions: List[str] = []
    for action in actions:
        if action.satisfies_requirements(scene):
            action.apply(scene)
            applied_actions.append(action.serialize())
        else:
            # Log that requirements were not satisfied
            pass

    return applied_actions


async def send_scene():
    serialized_scene = scene.serialize()
    future_sends = []
    for process_data in processes.values():
        future_sends.append(process_data.pipe.coro_send(serialized_scene))

    await asyncio.gather(*future_sends)

#  __   __       ___  __  __
# |__) /  \ |  |  |  |__ (__'
# |  \ \__/ \__/  |  |__ .__)


@app.get("/")
async def get(tick_number: int) -> Dict[str, Union[int, str, List[List[str]]]]:
    # if player has no scene or player tick number is incorrect
    # TODO remove tick number and use scene hash instead e.g. if player_scene_hash not in self.states.keys():
    if tick_number < 0 or tick_number > tick_number:
        return {"tick_number": tick_number, "scene": scene.serialize()}
    else:
        return {"tick_number": tick_number, "deltas": json.dumps(calculate_deltas(tick_number, tick_number, applied_actions))}


@app.post("/add_object")
async def add(r: AddObjectRequest):
    object = Object.deserialize(r.serialized_object)
    scene.add_entity(object)
    if object.tick != "":
        parent_conn, child_conn = AioPipe()
        p = AioProcess(target=execution_runtime,
                       args=(child_conn, object.id,))
        p.start()

        # I'm not 100% sure if we should await it or not
        await parent_conn.coro_send(scene.serialize())
        processes[object.id] = ProcessData(
            process=p, pipe=parent_conn)

    return {"serialized_object": object.serialize()}


@app.post("/tick")
async def tick():
    global tick_number
    
    actions = await fetch_actions()
    actions.extend([Entity.deserialize(pending_action)
                   for pending_action in scene.pending_actions])
    applied_actions = apply_actions(actions)
    applied_actions.append(applied_actions)
    tick_number += 1
    await send_scene()

    return {"tick_number": tick_number}


@app.post("/clear")
async def clear():
    scene = Scene()


@app.post("/populate")
async def populate():
    await clear()
    opensimplex.seed(1234)
    id = 0
    for (x, y) in itertools.product(range(100), range(10)):
        scene.add_entity(Object(id=id, name="Grass",
                         position=Vector(x, y), walkable=True))
        id += 1
        if opensimplex.noise2(x, y) > .3:
            scene.add_entity(
                Object(id=id, name="Tree", position=Vector(x, y), walkable=False))
            id += 1

    return {"id": id}

# Teardown is necessary to close all subprocesses
# I tired using FastAPI `lifespan` but it might not work
# with apps that are not top-level


@app.post('/teardown')
async def teardown():
    for process_data in processes.values():
        process_data.process.terminate()
