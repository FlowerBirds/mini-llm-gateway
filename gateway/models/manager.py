import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from filelock import FileLock

DATA_DIR = Path(__file__).parent.parent.parent / "data"
MODELS_FILE = DATA_DIR / "models.json"


class ModelManager:
    _instance: Optional["ModelManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._data: Dict[str, Any] = self._load()

    @classmethod
    def get_instance(cls) -> "ModelManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _load(self) -> Dict[str, Any]:
        if not MODELS_FILE.exists():
            return {"active_model": None, "models": []}
        with open(MODELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self):
        lock_path = str(MODELS_FILE) + ".lock"
        with FileLock(lock_path):
            with open(MODELS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get_models(self) -> List[Dict[str, Any]]:
        return self._data.get("models", [])

    def get_active_model(self) -> Optional[Dict[str, Any]]:
        active = self._data.get("active_model")
        if active:
            for model in self._data.get("models", []):
                if model.get("id") == active and model.get("enabled"):
                    return model
        for model in self._data.get("models", []):
            if model.get("enabled"):
                return model
        return None

    def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        for model in self._data.get("models", []):
            if model.get("id") == model_id:
                return model
        return None

    def add_model(self, model: Dict[str, Any]) -> Dict[str, Any]:
        models = self._data.get("models", [])
        for m in models:
            if m.get("id") == model.get("id"):
                m.update(model)
                self._save()
                return m
        models.append(model)
        self._data["models"] = models
        if not self._data.get("active_model"):
            self._data["active_model"] = model.get("id")
        self._save()
        return model

    def update_model(self, model_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        models = self._data.get("models", [])
        for i, m in enumerate(models):
            if m.get("id") == model_id:
                models[i].update(updates)
                self._save()
                return models[i]
        return None

    def delete_model(self, model_id: str) -> bool:
        models = self._data.get("models", [])
        original_len = len(models)
        models = [m for m in models if m.get("id") != model_id]
        if len(models) < original_len:
            self._data["models"] = models
            if self._data.get("active_model") == model_id:
                self._data["active_model"] = None
            self._save()
            return True
        return False

    def set_active_model(self, model_id: str) -> bool:
        model = self.get_model_by_id(model_id)
        if model and model.get("enabled"):
            self._data["active_model"] = model_id
            self._save()
            return True
        return False

    def toggle_model(self, model_id: str, enabled: bool) -> Optional[Dict[str, Any]]:
        return self.update_model(model_id, {"enabled": enabled})

    def reload(self):
        with self._lock:
            self._data = self._load()


def get_model_manager() -> ModelManager:
    return ModelManager.get_instance()
