#  __   __   __       __           __   __  ___      __      ___       __
# (__' /  ` |__ |\ | |__ ___ |__| /  \ (__'  |  ___ |__) \_/  |  |__| /  \ |\ |
# .__) \__, |__ | \| |__     |  | \__/ .__)  |      |     |   |  |  | \__/ | \|

import asyncio
import itertools
import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import httpx
import opensimplex
from aioprocessing import AioPipe, AioProcess
from aioprocessing.connection import AioConnection
from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from lynx.common.actions.create_object import CreateObject
from lynx.common.actions.remove_object import RemoveObject
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
    last_tick_time: float = 0.0


@dataclass
class ProcessData:
    object_id: int = -1
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
app.add_middleware(GZipMiddleware, minimum_size=100)

#       __      __   __  __      ___            __  ___    __        __
# |__| |__ |   |__) |__ |__)    |__  |  | |\ | /  `  |  | /  \ |\ | (__'
# |  | |__ |__ |    |__ |  \    |    \__/ | \| \__,  |  | \__/ | \| .__)


async def post(url: str, payload):
    async with httpx.AsyncClient() as client:
        result = await client.post(url, json=payload)
    return result


def calculate_deltas(from_tick_number: int, to_tick_number: int, actions_in_ticks: List[List[Optional[str]]]) -> List[Optional[str]]:
    deltas = []
    for actions_in_tick in actions_in_ticks[(from_tick_number + 1):(to_tick_number + 1)]:
        deltas = deltas + actions_in_tick
    return deltas


async def fetch_actions_from_process(process_data: ProcessData) -> str:
    try:
        return await process_data.pipe.coro_recv()
    except Exception as e:
        state.processes.pop(process_data.object_id)
        return RemoveObject(process_data.object_id).serialize()


async def fetch_actions() -> List[Entity]:
    future_actions = []
    for process_data in state.processes.values():
        future_actions.append(fetch_actions_from_process(process_data))

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


async def send_scene_to_process(process_data: ProcessData, serialized_scene: str) -> str:
    try:
        return await process_data.pipe.coro_send(serialized_scene)
    except Exception as e:
        # TODO: Not used right now
        state.processes.remove(process_data.object_id)
        RemoveObject(process_data.object_id).serialize()


async def send_scene():
    serialized_scene = state.scene.serialize()
    future_sends = []
    for process_data in state.processes.values():
        future_sends.append(send_scene_to_process(process_data, serialized_scene))

    await asyncio.gather(*future_sends)


def close_processes():
    for process_data in state.processes.values():
        process_data.process.terminate()


async def tick_trigger():
    if time.time() - state.last_tick_time >= 1:
        await tick()
        state.last_tick_time = time.time()


async def wait_for_next_tick():
    next_tick_number = state.tick_number + 1
    while state.tick_number != next_tick_number:
        await asyncio.sleep(0.1)


async def spawn_process_for_new_agent(object: Object):
    await wait_for_next_tick()

    parent_connection, child_connection = AioPipe()
    process = AioProcess(target=execution_runtime, args=(child_connection, object.id,))
    process.start()

    await parent_connection.coro_send(state.scene.serialize())
    state.processes[object.id] = ProcessData(object_id=object.id, process=process, pipe=parent_connection)


#  __   __       ___  __  __
# |__) /  \ |  |  |  |__ (__'
# |  \ \__/ \__/  |  |__ .__)


@app.get("/")
async def get(tick_number: int, background_tasks: BackgroundTasks) -> Dict[str, Union[int, str, List[List[str]]]]:
    background_tasks.add_task(tick_trigger)
    # if player has no scene or player tick number is incorrect
    # TODO remove tick number and use scene hash instead e.g. if player_scene_hash not in self.states.keys():
    if tick_number < 0 or tick_number > state.tick_number:
        return {"tick_number": state.tick_number, "scene": state.scene.serialize()}
    else:
        return {"tick_number": state.tick_number, "deltas": json.dumps(calculate_deltas(tick_number, state.tick_number, state.transitions))}


@app.post("/add_object")
async def add(r: AddObjectRequest, background_tasks: BackgroundTasks):
    object = Object.deserialize(r.serialized_object)
    state.scene.add_to_pending_actions(CreateObject(r.serialized_object).serialize())
    if object.tick != "":
        background_tasks.add_task(spawn_process_for_new_agent, object)
    return {"serialized_object": object.serialize()}


@app.post("/tick")
async def tick():
    actions = await fetch_actions()
    actions.extend([Entity.deserialize(pending_action) for pending_action in state.scene.pending_actions])
    state.scene.pending_actions.clear()
    applied_actions = apply_actions(actions)
    state.transitions.append(applied_actions)
    state.tick_number += 1
    await send_scene()

    return {"tick_number": state.tick_number}


@app.post("/clear")
async def clear():
    state.scene = Scene()
    state.processes = {}
    state.transitions = [[]]
    state.tick_number = 0


@app.post("/populate")
async def populate():
    await clear()
    opensimplex.seed(1234)
    id = 0
    for (x, y) in itertools.product(range(100), range(10)):
        state.scene.add_entity(Object(id=id, name="Grass",
                                      position=Vector(x, y), tags= ['walkable']))
        id += 1
        if opensimplex.noise2(x, y) > .3:
            entity_name = "Tree"
            if id % 2 == 0:
               entity_name = "Rock"
            state.scene.add_entity(
                Object(id=id, name= entity_name, position=Vector(x, y)))
            id += 1

    return {"id": id}


@app.post("/generate_scene")
async def generate_scene():
    import os

    url = os.getenv('LYNX_SCENE_GENERATOR_URL')

    if url == None:
        url = 'https://scene-generator.kubernetes.blazej-smorawski.com/get_scene'

    await clear()
    response = await post(url, payload={"seed": "test", "width": 128, "height": 128})
    state.scene = Scene.deserialize(response.text)


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
