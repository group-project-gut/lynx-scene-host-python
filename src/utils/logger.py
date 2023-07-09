import logging


def get_logger() -> logging.Logger:
    """
    Get the logger for the application and set it up
    :return: logger
    """
    logger = logging.getLogger("lynx")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(process)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger