#!/usr/bin/env python3

import uvicorn
from src.scene_server import SceneServer


server = SceneServer()

if __name__ == "__main__":
    uvicorn.run("scene-host-python:server.app", host="127.0.0.1", port=8555, workers=1)
    server.teardown()