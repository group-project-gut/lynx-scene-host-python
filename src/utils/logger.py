import logging
import typing as tp

map_level = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR
}

DEFAULT_LOGGER_LEVEL = logging.DEBUG


def setup_logger(name: str, logger_level: str) -> tp.NoReturn:
    """
    Setup the logger for the application
    :param name: The name of the logger
    :param logger_level: The level of the logger
    """
    level = map_level.get(logger_level, DEFAULT_LOGGER_LEVEL) if logger_level else DEFAULT_LOGGER_LEVEL
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s [%(process)s] [%(levelname)s] - %(message)s')
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(handler)
