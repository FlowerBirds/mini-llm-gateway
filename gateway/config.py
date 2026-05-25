import threading
import yaml
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = BASE_DIR / "config.yaml"


class Config:
    _instance: Optional["Config"] = None
    _lock = threading.Lock()

    def __init__(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = {}

    @classmethod
    def get_instance(cls) -> "Config":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @property
    def host(self) -> str:
        return self._data.get("host", "0.0.0.0")

    @property
    def port(self) -> int:
        return self._data.get("port", 8080)

    @property
    def log_level(self) -> str:
        return self._data.get("log_level", "info")

    @property
    def cors_origins(self) -> list:
        return self._data.get("cors", {}).get("allow_origins", ["localhost", "127.0.0.1"])


def get_config() -> Config:
    return Config.get_instance()
