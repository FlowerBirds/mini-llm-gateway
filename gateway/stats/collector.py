import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from filelock import FileLock

DATA_DIR = Path(__file__).parent.parent.parent / "data"
STATS_FILE = DATA_DIR / "stats.json"

MAX_HISTORY = 100000


class StatsCollector:
    _instance: Optional["StatsCollector"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._data: Dict[str, Any] = self._load()

    @classmethod
    def get_instance(cls) -> "StatsCollector":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _load(self) -> Dict[str, Any]:
        if not STATS_FILE.exists():
            return self._default_data()
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._migrate(data)

    def _default_data(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cache_read_tokens": 0,
                "total_cache_creation_tokens": 0,
                "total_duration": 0.0,
                "avg_throughput": 0.0
            },
            "by_model": {},
            "history": []
        }

    def _migrate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "summary" not in data:
            data["summary"] = {}
        if "total_cache_read_tokens" not in data["summary"]:
            data["summary"]["total_cache_read_tokens"] = 0
        if "total_cache_creation_tokens" not in data["summary"]:
            data["summary"]["total_cache_creation_tokens"] = 0
        if "total_duration" not in data["summary"]:
            data["summary"]["total_duration"] = 0.0
        if "avg_throughput" not in data["summary"]:
            data["summary"]["avg_throughput"] = 0.0

        for model_id, stats in data.get("by_model", {}).items():
            if "cache_read_tokens" not in stats:
                stats["cache_read_tokens"] = 0
            if "cache_creation_tokens" not in stats:
                stats["cache_creation_tokens"] = 0
            if "total_duration" not in stats:
                stats["total_duration"] = 0.0
            if "avg_throughput" not in stats:
                stats["avg_throughput"] = 0.0

        for h in data.get("history", []):
            if "cache_read_tokens" not in h:
                h["cache_read_tokens"] = 0
            if "cache_creation_tokens" not in h:
                h["cache_creation_tokens"] = 0
            if "duration" not in h:
                h["duration"] = 0.0
            if "throughput" not in h:
                h["throughput"] = 0.0

        return data

    def _save(self):
        lock_path = str(STATS_FILE) + ".lock"
        with FileLock(lock_path):
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)

    def record_request(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        error: bool = False,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
        duration: float = 0.0,
        throughput: float = 0.0
    ):
        self._data["summary"]["total_requests"] += 1
        self._data["summary"]["total_input_tokens"] += input_tokens
        self._data["summary"]["total_output_tokens"] += output_tokens
        self._data["summary"]["total_cache_read_tokens"] += cache_read_tokens
        self._data["summary"]["total_cache_creation_tokens"] += cache_creation_tokens
        self._data["summary"]["total_duration"] += duration

        total_tokens = self._data["summary"]["total_input_tokens"] + self._data["summary"]["total_output_tokens"]
        total_dur = self._data["summary"]["total_duration"]
        self._data["summary"]["avg_throughput"] = round(total_tokens / total_dur, 2) if total_dur > 0 else 0.0

        if model_id not in self._data["by_model"]:
            self._data["by_model"][model_id] = {
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "errors": 0,
                "cache_read_tokens": 0,
                "cache_creation_tokens": 0,
                "total_duration": 0.0,
                "avg_throughput": 0.0
            }

        self._data["by_model"][model_id]["requests"] += 1
        self._data["by_model"][model_id]["input_tokens"] += input_tokens
        self._data["by_model"][model_id]["output_tokens"] += output_tokens
        self._data["by_model"][model_id]["cache_read_tokens"] += cache_read_tokens
        self._data["by_model"][model_id]["cache_creation_tokens"] += cache_creation_tokens
        self._data["by_model"][model_id]["total_duration"] += duration
        model_in = self._data["by_model"][model_id]["input_tokens"]
        model_out = self._data["by_model"][model_id]["output_tokens"]
        model_dur = self._data["by_model"][model_id]["total_duration"]
        self._data["by_model"][model_id]["avg_throughput"] = round((model_in + model_out) / model_dur, 2) if model_dur > 0 else 0.0
        if error:
            self._data["by_model"][model_id]["errors"] += 1

        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "error": error,
            "cache_read_tokens": cache_read_tokens,
            "cache_creation_tokens": cache_creation_tokens,
            "duration": round(duration, 3),
            "throughput": throughput
        }
        self._data["history"].append(history_entry)

        if len(self._data["history"]) > MAX_HISTORY:
            self._data["history"] = self._data["history"][-MAX_HISTORY:]

        self._save()

    def get_stats(self) -> Dict[str, Any]:
        return self._data

    def get_summary(self) -> Dict[str, Any]:
        return self._data.get("summary", {})

    def get_model_stats(self, model_id: str) -> Optional[Dict[str, Any]]:
        return self._data.get("by_model", {}).get(model_id)

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        history = self._data.get("history", [])
        return history[-limit:] if limit > 0 else history

    def get_hourly_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        history = self._data.get("history", [])
        hourly: Dict[str, Dict[str, Any]] = {}

        cutoff = None
        if history:
            latest_ts = history[-1].get("timestamp", "")
            if latest_ts:
                latest = datetime.fromisoformat(latest_ts)
                cutoff = latest - timedelta(hours=hours)

        for entry in history:
            ts_str = entry.get("timestamp", "")
            if not ts_str:
                continue
            ts = datetime.fromisoformat(ts_str)
            if cutoff and ts < cutoff:
                continue
            hour_key = ts.strftime("%Y-%m-%dT%H:00:00")
            if hour_key not in hourly:
                hourly[hour_key] = {
                    "hour": hour_key,
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_duration": 0.0
                }
            hourly[hour_key]["requests"] += 1
            hourly[hour_key]["input_tokens"] += entry.get("input_tokens", 0)
            hourly[hour_key]["output_tokens"] += entry.get("output_tokens", 0)
            hourly[hour_key]["total_duration"] += entry.get("duration", 0.0)

        for h in hourly.values():
            h["avg_throughput"] = round((h["input_tokens"] + h["output_tokens"]) / h["total_duration"], 2) if h["total_duration"] > 0 else 0.0

        return sorted(hourly.values(), key=lambda x: x["hour"])

    def reset(self):
        with self._lock:
            self._data = self._default_data()
            self._save()

    def reload(self):
        with self._lock:
            self._data = self._load()


def get_stats_collector() -> StatsCollector:
    return StatsCollector.get_instance()
