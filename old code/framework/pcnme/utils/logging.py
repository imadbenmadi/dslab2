from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import structlog


def configure_logging(*, log_dir: Optional[Path] = None, level: int = logging.INFO) -> structlog.BoundLogger:
    log_dir = log_dir or Path("results") / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger("pcnme")
