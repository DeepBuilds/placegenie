"""Slows down password guessing.

Too many failed logins for one email, or from one network address, within a time window are refused with 429
until the oldest failure leaves the window. A successful login clears that email's failures.

The counts live in memory (per server process): simple, and no table is needed. With several worker processes each
keeps its own count, which still caps guessing at a few attempts per window.
"""
import threading
import time
from collections import defaultdict, deque


class LoginLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _recent(self, key: str, now: float, window: float) -> deque[float]:
        q = self._failures[key]
        while q and q[0] <= now - window:
            q.popleft()
        if not q:
            del self._failures[key]  # keep memory bounded to keys with recent failures
            return deque()
        return q

    def retry_after(self, limits: list[tuple[str, int]], window: float, now: float | None = None) -> int | None:
        """Seconds to wait if any key has reached its limit, else None."""
        now = time.monotonic() if now is None else now
        with self._lock:
            waits = [int(q[0] + window - now) + 1 for key, limit in limits if len(q := self._recent(key, now, window)) >= limit]
        return max(waits) if waits else None

    def record_failure(self, keys: list[str], now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            for key in keys:
                self._failures[key].append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = LoginLimiter()
