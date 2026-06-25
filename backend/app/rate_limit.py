"""Minimal in-memory brute-force guard for login endpoints.

Counts FAILED login attempts per client IP within a sliding window; once the
limit is hit, further attempts get a 429 until the window clears. Successful
logins reset the counter. Only failures are counted, so normal use (and the
test suite) is unaffected.

Single uvicorn worker → in-memory state is sufficient. Behind Caddy the real
client IP comes from X-Forwarded-For.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class LoginGuard:
    def __init__(self, max_failures: int = 10, window_seconds: float = 300.0):
        self.max = max_failures
        self.window = window_seconds
        self._fails: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, dq: deque[float], now: float) -> None:
        while dq and now - dq[0] > self.window:
            dq.popleft()

    def check(self, ip: str) -> None:
        now = time.monotonic()
        dq = self._fails[ip]
        self._prune(dq, now)
        if len(dq) >= self.max:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too many failed attempts; please wait a few minutes and try again",
            )

    def fail(self, ip: str) -> None:
        self._fails[ip].append(time.monotonic())

    def reset(self, ip: str) -> None:
        self._fails.pop(ip, None)

    def reset_all(self) -> None:
        self._fails.clear()


login_guard = LoginGuard()


def client_ip(request: Request) -> str:
    """Real client IP — first X-Forwarded-For entry (set by Caddy), else peer."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
