"""
In-memory pipeline log store.

Stores timestamped log lines per evaluation so the frontend can
poll GET /evaluations/{id}/logs to display a live console view.
Lines persist until the process restarts (sufficient for a single-server setup).
"""

import time
from collections import defaultdict

_store: dict[str, list[str]] = defaultdict(list)


def log(evaluation_id: str, message: str) -> None:
    ts = time.strftime("%H:%M:%S")
    _store[str(evaluation_id)].append(f"[{ts}] {message}")


def get_lines(evaluation_id: str, offset: int = 0) -> list[str]:
    return list(_store.get(str(evaluation_id), [])[offset:])


def total(evaluation_id: str) -> int:
    return len(_store.get(str(evaluation_id), []))


def clear(evaluation_id: str) -> None:
    _store.pop(str(evaluation_id), None)
