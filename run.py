#!/usr/bin/env python3
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gateway.main import app
from gateway.config import get_config
from uvicorn.logging import DefaultFormatter


class TimestampFormatter(DefaultFormatter):
    def format(self, record):
        if not hasattr(record, "levelprefix") or record.levelprefix is None:
            record.levelprefix = ""
        return super().format(record)


if __name__ == "__main__":
    config = get_config()
    import uvicorn
    LOG_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": f"{__name__}.TimestampFormatter",
                "fmt": "%(asctime)s %(levelprefix)s %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["default"],
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["default"],
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["default"],
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
    }
    uvicorn.run(
        "gateway.main:app",
        host=config.host,
        port=config.port,
        reload=True,
        log_config=LOG_CONFIG,
    )
