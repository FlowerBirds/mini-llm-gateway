import argparse
import logging
import uvicorn
from uvicorn.logging import DefaultFormatter

from .config import get_config


class TimestampFormatter(DefaultFormatter):
    def format(self, record):
        if not hasattr(record, "levelprefix") or record.levelprefix is None:
            record.levelprefix = ""
        return super().format(record)


def main():
    config = get_config()
    parser = argparse.ArgumentParser(prog="mini-llm-gateway")
    parser.add_argument("--host", default=config.host)
    parser.add_argument("--port", type=int, default=config.port)
    args = parser.parse_args()

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
    }

    uvicorn.run(
        "gateway.main:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_config=LOG_CONFIG,
    )


if __name__ == "__main__":
    main()
