import asyncio
from multiprocessing import Process
from time import perf_counter

import aiohttp
import asynctest
import uvicorn

from lynx.common.object import Object
from lynx.common.scene import Scene
from src.scene_server import SceneServer


class TestSceneServer(asynctest.TestCase):
    """ Test the app class. """

    async def setUp(self):
        """ Bring server up. """
        server = SceneServer()
        self.proc = Process(target=uvicorn.run,
                            args=(server.app,),
                            kwargs={
                                "host": "127.0.0.1",
                                "port": 8555,
                                "log_level": "info",
                                "workers": 1
                            },
                            daemon=True)
        self.proc.start()
        await asyncio.sleep(0.1)  # time for the server to start

    async def tearDown(self):
        """ Shutdown the app. """
        self.proc.terminate()

    async def fetch(s, url):
        async with s.get(url) as r:
            if r.status != 200:
                r.raise_for_status()
            return await r.json()

    async def post(s, url, payload):
        async with s.post(url, json=payload) as r:
            if r.status != 200:
                r.raise_for_status()
            return await r.json()

    async def spam_objects(session, count: int):
        tasks = []
        for i in range(count):
            object = Object(id=i)
            task = asyncio.create_task(TestSceneServer.post(
                session, "http://0.0.0.0:8555/add_object", {'serialized_object': object.serialize()}))
            tasks.append(task)
        res = await asyncio.gather(*tasks)
        return res

    async def test_spam_objects(self):
        """ Fetch an endpoint from the app. """
        async with aiohttp.ClientSession() as session:
            data = await TestSceneServer.spam_objects(session, 100)

        async with aiohttp.ClientSession() as session:
            response = await TestSceneServer.fetch(session, "http://0.0.0.0:8555/?tick_number=-1")
        scene = Scene.deserialize(response['scene'])
        # TODO: assert scene contents
