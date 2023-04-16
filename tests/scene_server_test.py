import asyncio

import pytest
from httpx import AsyncClient
from lynx.common.object import Object
from lynx.common.scene import Scene

from src.scene_server import SceneServer


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
            object = Object(id=i, tick=f"move(Vector({i},{i}))")
            task = asyncio.create_task(TestSceneServer.post(
                ac, "/add_object", {'serialized_object': object.serialize()}))
            tasks.append(task)
        res = await asyncio.gather(*tasks)
        return res

    @pytest.mark.asyncio
    async def test_spam_objects(self):
        server = SceneServer()
        async with AsyncClient(app=server.app, base_url="http://test") as ac:
            response = await TestSceneServer.fetch(ac, "/?tick_number=-1")
            await TestSceneServer.spam_objects(ac, 100)
            await TestSceneServer.post(ac, "/tick")
            await TestSceneServer.post(ac, "/tick")
            await TestSceneServer.post(ac, "/tick")

            response = await TestSceneServer.fetch(ac, "/?tick_number=-1")
            scene = Scene.deserialize(response['scene'])

        server.teardown()
