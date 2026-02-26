"""Small experiment logger.

Append JSON-lines records to `experiments/log.jsonl`. Each record should
contain at least: model, task, prompt_strategy, program, validation_status,
evaluation (summary), and timestamps.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any
import pandas as pd


LOG_PATH = os.path.join(os.path.dirname(__file__), "log.jsonl")


def _ensure_dir():
    d = os.path.dirname(LOG_PATH)
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

# Change extension to .jsonl to reflect the actual file format
LOG_PATH = os.path.join(os.path.dirname(__file__), "log.jsonl")


def log_result(record: dict):
    """
    Appends a record to the log.
    Improved to handle nested errors and ensure directory safety.
    """
    _ensure_dir()

    # Flattening critical metrics for easier CSV conversion later
    entry = {"timestamp": datetime.utcnow().isoformat() + "Z", **record}

    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")
    except IOError as e:
        print(f"Failed to write log: {e}")


def get_performance_dataframe():
    """
    Helper to quickly convert logs to a Pandas DataFrame
    for the Analysis Report.
    """

    data = read_all()
    # Flattening the nested dictionary for a clean table
    flat_data = []
    for d in data:
        row = {
            "strategy": d.get("prompt_strategy"),
            "task": d.get("task"),
            "completeness": d.get("metrics", {}).get("completeness"),
            "hallucination": d.get("metrics", {}).get("hallucination_rate"),
            "fidelity": d.get("metrics", {}).get("fidelity"),
        }
        flat_data.append(row)
    return pd.DataFrame(flat_data)


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
