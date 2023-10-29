import sys  
import logging


ROOT_LEN = len(__file__) - len("lib/log.py")


def get_logger(file_path: str) -> logging.Logger:
    short_path = file_path[ROOT_LEN:]
    logger = logging.getLogger(short_path)
    logger = init_logger(logger)
    return logger


def init_logger(
        logger: logging.Logger,
        level: int = logging.DEBUG,
) -> logging.Logger:
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    # Add the handler to the logger
    logger.addHandler(handler)
    return logger