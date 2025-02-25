import logging
from hypermind.utils.logging import get_logger

def setup_logging():
    log_file = "debug.log"

    # Get root logger (captures ALL logs)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Create a file handler for logging
    file_handler = logging.FileHandler(log_file, mode="a")  # 'a' to append logs
    file_handler.setLevel(logging.DEBUG)  # Ensure all logs are captured

    # Standard log format
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # Avoid duplicate handlers
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)

    # Ensure hypermind logs also propagate
    logging.getLogger("hypermind").propagate = True  

    print("Logging setup complete. Logs will be saved to:", log_file)

# Call this **before** importing other parts of the application
setup_logging()

# Now, get a logger for the application
logger = get_logger(__name__)
logger.debug("Application started")