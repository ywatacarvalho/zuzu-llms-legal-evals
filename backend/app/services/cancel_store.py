"""
In-memory cancellation flag store.

When a user requests a stop, the evaluation ID is added here.
The pipeline checks this flag at each major transition and exits
early without overwriting the failed status set by the stop endpoint.
"""

_cancelled: set[str] = set()


def cancel(evaluation_id: str) -> None:
    _cancelled.add(str(evaluation_id))


def is_cancelled(evaluation_id: str) -> bool:
    return str(evaluation_id) in _cancelled


def clear(evaluation_id: str) -> None:
    _cancelled.discard(str(evaluation_id))
