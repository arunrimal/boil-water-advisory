import os
import logging
from datetime import datetime

# Folder where log files will be stored
LOG_FOLDER = "logs"


def setup_logger():
    """
    This Function creates the logs folder if it doesn't exist, then sets up a logger with:
    - A console handler (INFO and above)
    - A file handler writing to logs/scrape_YYYY-MM-DD_HH-MM-SS.log (INFO and above)
    """

    os.makedirs(LOG_FOLDER, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(LOG_FOLDER, f"pipeline_{timestamp}.log")

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # logger = logging.getLogger(__name__)
    logger = logging.getLogger("kdhe_pipeline")
    logger.setLevel(logging.INFO)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger