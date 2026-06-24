import time
from collections import defaultdict, deque

from fastapi import HTTPException


class SlidingWindowRateLimiter:
    """A tiny in-memory, per-process sliding-window limiter.

    Used for the admin endpoints only (a single operator, never the shared-NAT
    student traffic), so a leaked or guessed admin password cannot be brute
    forced quickly. State is per-app-instance and resets on restart, which is
    fine for slowing an attacker on a small single-instance pilot.
    """

    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def hit(self, key: str) -> None:
        now = time.monotonic()
        bucket = self._hits[key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many attempts. Please wait a minute and try again.",
            )
        bucket.append(now)
