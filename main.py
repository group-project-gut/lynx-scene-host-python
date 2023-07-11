#!/usr/bin/env python3

from configparser import ConfigParser

import uvicorn

from src.utils.logger import setup_logger

config = ConfigParser()
config.read("config.ini")

if __name__ == "__main__":
    setup_logger(config["GENERAL"]["APPLICATION_NAME"], config["LOGGING"]["LOGGER_LEVEL"])
    uvicorn.run("src.app:app", host="0.0.0.0", port=8555, workers=1)
