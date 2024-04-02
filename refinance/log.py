import logging
import logging.config
from os import environ

from yaml import safe_load


def configure_logging() -> None:
    """Configure logging from environment variables."""
    log_config_path = environ.get("LOG_CONFIG", None)
    if log_config_path is None:
        log_level = environ.get("LOG_LEVEL", "INFO").upper()
        if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {log_level}")
        log_format = environ.get("LOG_FORMAT", "%(asctime)s   %(name)-25s %(levelname)-8s %(message)s")
        log_file = environ.get("LOG_FILE", None)

        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file) if log_file else logging.NullHandler(),
            ],
        )
    else:
        with open(log_config_path, "r") as f:
            logging_config = safe_load(f.read())
        logging.config.dictConfig(logging_config)
