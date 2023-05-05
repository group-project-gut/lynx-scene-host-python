import asyncio
import time

import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient
from lynx.common.object import Object
from lynx.common.scene import Scene

from src.app import app


class TestSceneServer():
    """ Test the app class. """

    async def fetch(ac: AsyncClient, url):
        response = await ac.get(url)
        if response.status_code != 200:
            response.raise_for_status()
        return response.json()

    async def post(ac: AsyncClient, url, payload={}):
        response = await ac.post(url, json=payload)
        if response.status_code != 200:
            response.raise_for_status()
        return response.json()

    async def spam_objects(ac: AsyncClient, count: int):
        tasks = []
        for i in range(count):
            object = Object(id=i, tick=f"")
            task = asyncio.create_task(TestSceneServer.post(
                ac, "/add_object", {'serialized_object': object.serialize()}))
            tasks.append(task)
        res = await asyncio.gather(*tasks)
        return res

    @pytest.mark.asyncio
    async def test_spam_objects(self):
        start_time = time.time()
        async with LifespanManager(app):
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await TestSceneServer.fetch(ac, "/?tick_number=-1")
                await TestSceneServer.spam_objects(ac, 100)

                await TestSceneServer.post(ac, "/populate")
                agent = Object(id=1000, tick=f"move(Vector(1,0))")
                await TestSceneServer.post(ac, "/add_object", {'serialized_object': agent.serialize()})

                response = await TestSceneServer.fetch(ac, "/?tick_number=-1")
                response = await TestSceneServer.fetch(ac, "/?tick_number=0")
                # scene = Scene.deserialize(response['scene'])

            elapsed = time.time() - start_time
        assert elapsed < 50
