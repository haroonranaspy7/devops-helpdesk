import json
import logging
import sys
from datetime import datetime, timezone


STANDARD_LOG_RECORD_ATTRIBUTES = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName"
}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }

        for key, value in record.__dict__.items():
            if (
                key not in
                STANDARD_LOG_RECORD_ATTRIBUTES
            ):
                log_entry[key] = value

        if record.exc_info:
            log_entry["exception"] = (
                self.formatException(
                    record.exc_info
                )
            )

        return json.dumps(
            log_entry,
            default=str
        )


def configure_logging():
    handler = logging.StreamHandler(
        sys.stdout
    )

    handler.setFormatter(
        JsonFormatter()
    )

    root_logger = logging.getLogger()

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
