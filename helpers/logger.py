import os
import sys
import logging
from loguru import logger


LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


class InterceptHandler(logging.Handler):
    def emit(self, record):
        logger.opt(depth=6, exception=record.exc_info).log(
            record.levelname, record.getMessage()
        )

logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

logger.remove()
logger.add(
    sys.stdout,
    format="<green>[{time:YYYY-MM-DD HH:mm:ss}][<level>{level}</level>]</green> {name}:{function} -> {message}",
    level=LOG_LEVEL
)
