import logging
from typing import Optional

import coloredlogs


def get_logger(
    name: str, level: str = "INFO", fmt: Optional[str] = None
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))

    fmt = fmt or (
        "[%(asctime)s] %(levelname)s - %(funcName)s:%(lineno)d - %(module)s - %(message)s"
    )
    coloredlogs.install(fmt=fmt, level=level, logger=logger)
    return logger


get_logger(
    "discord", "WARN", fmt="[[ discord ]] [%(asctime)s] %(levelname)s - %(message)s"
)
