#!/usr/bin/env python3

import uvicorn
from src.server import Server


server = Server()

if __name__ == "__main__":
    uvicorn.run("scene-host-python:server.app", host="0.0.0.0", port=8555, workers=1)