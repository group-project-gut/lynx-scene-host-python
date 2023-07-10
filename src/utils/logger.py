import logging
import sys
import typing as tp

map_level = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR
}

APPLICATION_NAME = "lynx-scene-host-python"
DEFAULT_LOGGER_LEVEL = logging.DEBUG
logger_level = map_level.get(sys.argv[1], DEFAULT_LOGGER_LEVEL) if len(sys.argv) > 1 else DEFAULT_LOGGER_LEVEL


def get_logger(name: str) -> logging.Logger:
    """
    Get the logger for the application
    :param name: name of the logger
    :return: logger
    """
    return logging.getLogger(f"{APPLICATION_NAME}.{name}")


def setup_logger(name: str) -> tp.NoReturn:
    """
    Setup the logger for the application
    :param name: name of the logger
    """
    logger = logging.getLogger(f"{APPLICATION_NAME}.{name}")
    logger.setLevel(logger_level)
    formatter = logging.Formatter('%(asctime)s [%(process)s] [%(levelname)s] - %(message)s')
    handler = logging.StreamHandler()
    handler.setLevel(logger_level)
    handler.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(handler)
