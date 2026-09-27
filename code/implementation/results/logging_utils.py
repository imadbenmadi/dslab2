"""Centralized structured logging utilities for the smart-city runtime."""

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any, Dict


def setup_application_logger(name: str = "smart_city", log_dir: str = "results/logs") -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    text_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "system.log"),
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    text_handler.setLevel(logging.INFO)
    text_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )

    logger.addHandler(text_handler)
    logger.propagate = False
    return logger


def write_json_event(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")
