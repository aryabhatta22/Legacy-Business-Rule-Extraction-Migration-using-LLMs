"""Small experiment logger.

Append JSON-lines records to `experiments/log.jsonl`. Each record should
contain at least: model, task, prompt_strategy, program, validation_status,
evaluation (summary), and timestamps.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any


LOG_PATH = os.path.join(os.path.dirname(__file__), "log.json")


def _ensure_dir():
    d = os.path.dirname(LOG_PATH)
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def log_result(record: Dict[str, Any]):
    """Append a record (dict) to the experiments log file as JSONL."""
    _ensure_dir()
    entry = dict(record)
    entry.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")


def read_all() -> list:
    if not os.path.exists(LOG_PATH):
        return []
    out = []
    with open(LOG_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out
