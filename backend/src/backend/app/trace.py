"""Trace and timing helpers for EG-VIA backend requests."""

from __future__ import annotations

import time
import uuid


def new_request_id() -> str:
    """Create a UUID4 request identifier."""

    return str(uuid.uuid4())


def start_timer() -> float:
    """Start a monotonic timer."""

    return time.perf_counter()


def elapsed_ms(start_time: float) -> int:
    """Return elapsed milliseconds from `start_time` (minimum 1ms)."""

    return max(1, int((time.perf_counter() - start_time) * 1000))


def elapsed_between_ms(start_time: float, end_time: float) -> int:
    """Return elapsed milliseconds between two timer marks (minimum 1ms)."""

    return max(1, int((end_time - start_time) * 1000))
