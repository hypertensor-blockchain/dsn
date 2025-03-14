import os

from hypermind.utils import logging as hm_logging
from hypermind.utils.logging import CustomFormatter
import logging.handlers

def initialize_logs():
    """Initialize Petals logging tweaks. This function is called when you import the `petals` module."""

    # Env var PETALS_LOGGING=False prohibits Petals do anything with logs
    if os.getenv("PETALS_LOGGING", "True").lower() in ("false", "0"):
        return

    hm_logging.use_hypermind_log_handler("in_root_logger")

    # We suppress asyncio error logs by default since they are mostly not relevant for the end user,
    # unless there is env var PETALS_ASYNCIO_LOGLEVEL
    asyncio_loglevel = os.getenv("PETALS_ASYNCIO_LOGLEVEL", "FATAL" if hm_logging.loglevel != "DEBUG" else "DEBUG")
    hm_logging.get_logger("asyncio").setLevel(asyncio_loglevel)

    # custom logs

    logger = hm_logging.logging.getLogger("hypermind")
    logger.propagate = False
    logger.setLevel(hm_logging.logging.DEBUG)

    # file_handler = hm_logging.logging.FileHandler('logs.log')
    # file_handler = hm_logging.logging.RotatingFileHandler("logs.log", maxBytes=5 * 1024 * 1024, backupCount=15)
    # saves the last 8 (n) days of logs and prunes n+1
    file_handler = logging.handlers.TimedRotatingFileHandler(
        "logs.log", when="D", interval=1, backupCount=8
    )

    file_handler.setLevel(hm_logging.logging.DEBUG)

    console_handler = hm_logging.logging.StreamHandler()
    console_handler.setLevel(hm_logging.logging.INFO)

    formatter = hm_logging.logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    file_handler.setFormatter(formatter)

    console_formatter = CustomFormatter(
        fmt="{asctime}.{msecs:03.0f} [{bold}{levelcolor}{levelname}{reset}]{caller_block} {message}",
        style="{",
        datefmt="%b %d %H:%M:%S",
    )

    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)