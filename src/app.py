#  __   __   __       __           __   __  ___      __      ___       __
# (__' /  ` |__ |\ | |__ ___ |__| /  \ (__'  |  ___ |__) \_/  |  |__| /  \ |\ |
# .__) \__, |__ | \| |__     |  | \__/ .__)  |      |     |   |  |  | \__/ | \|

import asyncio
from contextlib import asynccontextmanager
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

#  __    _   ___   _       __  ___  __        __  ___       __   __  __
# |  \  /_\   |   /_\     (__'  |  |__) |  | /  `  |  |  | |__) |__ (__'
# |__/ /   \  |  /   \    .__)  |  |  \ \__/ \__,  |  \__/ |  \ |__ .__)


@dataclass
class GlobalState:
    scene: Scene = None,
    processes: Dict = None,
    transitions: Dict = None,
    tick_number: int = 0


@dataclass
class ProcessData:
    process: AioProcess = None
    pipe: AioConnection = None


class AddObjectRequest(BaseModel):
    serialized_object: str

#   _    __   __      __   __  ___          ___    __
#  /_\  |__) |__)    |  \ |__ |__  | |\ | |  |  | /  \ |\ |
# /   \ |    |       |__/ |__ |    | | \| |  |  | \__/ | \|

state = GlobalState(Scene(), {}, [[]], 0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    state.processes = {}
    yield
    close_processes()

app = FastAPI(lifespan=lifespan)

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
    for process_data in state.processes.values():
        future_actions.append(process_data.pipe.coro_recv())

    serialized_actions = await asyncio.gather(*future_actions)
    return [Entity.deserialize(serialized_action) for serialized_action in serialized_actions]


def apply_actions(actions: List[Entity]) -> List[str]:
    # Not sure if we should use `str` or `Action`
    applied_actions: List[str] = []
    for action in actions:
        if action.satisfies_requirements(state.scene):
            action.apply(state.scene)
            applied_actions.append(action.serialize())
        else:
            # Log that requirements were not satisfied
            pass

    return applied_actions


async def send_scene():
    serialized_scene = state.scene.serialize()
    future_sends = []
    for process_data in state.processes.values():
        future_sends.append(process_data.pipe.coro_send(serialized_scene))

    await asyncio.gather(*future_sends)

def close_processes():
    for process_data in state.processes.values():
        process_data.process.terminate()

#  __   __       ___  __  __
# |__) /  \ |  |  |  |__ (__'
# |  \ \__/ \__/  |  |__ .__)


@app.get("/")
async def get(tick_number: int) -> Dict[str, Union[int, str, List[List[str]]]]:
    # if player has no scene or player tick number is incorrect
    # TODO remove tick number and use scene hash instead e.g. if player_scene_hash not in self.states.keys():
    if tick_number < 0 or tick_number > state.tick_number:
        return {"tick_number": state.tick_number, "scene": state.scene.serialize()}
    else:
        return {"tick_number": state.tick_number, "deltas": json.dumps(calculate_deltas(tick_number, state.tick_number, state.transitions))}


@app.post("/add_object")
async def add(r: AddObjectRequest):
    object = Object.deserialize(r.serialized_object)
    state.scene.add_entity(object)
    if object.tick != "":
        parent_conn, child_conn = AioPipe()
        p = AioProcess(target=execution_runtime,
                       args=(child_conn, object.id,))
        p.start()

        # I'm not 100% sure if we should await it or not
        await parent_conn.coro_send(state.scene.serialize())
        state.processes[object.id] = ProcessData(
            process=p, pipe=parent_conn)

    return {"serialized_object": object.serialize()}


@app.post("/tick")
async def tick():
    actions = await fetch_actions()
    actions.extend([Entity.deserialize(pending_action)
                   for pending_action in state.scene.pending_actions])
    state.scene.pending_actions.clear()
    applied_actions = apply_actions(actions)
    state.transitions.append(applied_actions)
    state.tick_number += 1
    await send_scene()

    return {"tick_number": state.tick_number}


@app.post("/clear")
async def clear():
    state = GlobalState(Scene(), {}, [[]], 0)


@app.post("/populate")
async def populate():
    await clear()
    opensimplex.seed(1234)
    id = 0
    for (x, y) in itertools.product(range(100), range(10)):
        state.scene.add_entity(Object(id=id, name="Grass",
                                      position=Vector(x, y), walkable=True))
        id += 1
        if opensimplex.noise2(x, y) > .3:
            state.scene.add_entity(
                Object(id=id, name="Tree", position=Vector(x, y), walkable=False))
            id += 1

    return {"id": id}

# Teardown is necessary to close all subprocesses
# I tired using FastAPI `lifespan` but it might not work
# with apps that are not top-level


@app.post('/teardown')
async def teardown():
    close_processes()
    return {"status": "done"}

@app.get('/health')
async def health():
    return {"state": "working"}
