import json
import logging
import time
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": round(time.time(), 3),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        })


def get_logger(name="pipeline", log_path="logs/pipeline.log"):
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)

    if log.handlers:
        return log

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(path)
    handler.setFormatter(JsonFormatter())
    log.addHandler(handler)

    return log