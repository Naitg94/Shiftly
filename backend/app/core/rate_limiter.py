import time
import threading
from typing import Dict, List, Tuple, Optional
from abc import ABC, abstractmethod
from fastapi import Request, HTTPException, status, Depends
from app.core.config import settings
from app.core.auth import AuthenticatedUser, get_current_user, get_optional_current_user


class RateLimitExceededException(HTTPException):
    def __init__(self, retry_after: int, detail: Optional[str] = None):
        msg = detail or f"Rate limit exceeded. Please wait {retry_after} seconds before trying again."
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=msg,
            headers={"Retry-After": str(retry_after)},
        )
        self.retry_after = retry_after


class BaseRateLimiter(ABC):
    @abstractmethod
    def check_rate_limit(
        self, key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int]:
        """
        Returns (allowed: bool, retry_after_seconds: int).
        """
        pass

    @abstractmethod
    def reset(self):
        """Resets rate limiter state (useful for tests)."""
        pass


class InMemoryRateLimiter(BaseRateLimiter):
    """
    Thread-safe sliding-window rate limiter.
    Maintains timestamp logs per client key within the active time window.
    Designed for zero-cost ($0) single-instance deployment, with extensible interface
    to support Redis or distributed caches if horizontal scaling is required.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._records: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()

    def _cleanup_stale(self, current_time: float, max_idle: float = 300.0):
        """Purge keys that have no activity within max_idle seconds."""
        if current_time - self._last_cleanup < 60.0:
            return
        self._last_cleanup = current_time
        stale_keys = [
            k for k, timestamps in self._records.items()
            if not timestamps or (current_time - timestamps[-1] > max_idle)
        ]
        for k in stale_keys:
            del self._records[k]

    def check_rate_limit(
        self, key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int]:
        current_time = time.time()
        window_start = current_time - window_seconds

        with self._lock:
            self._cleanup_stale(current_time)

            timestamps = self._records.get(key, [])
            # Filter timestamps within active sliding window
            active_timestamps = [t for t in timestamps if t > window_start]

            if len(active_timestamps) >= max_requests:
                oldest_in_window = active_timestamps[0]
                retry_after = max(1, int(oldest_in_window + window_seconds - current_time) + 1)
                self._records[key] = active_timestamps
                return False, retry_after

            active_timestamps.append(current_time)
            self._records[key] = active_timestamps
            return True, 0

    def reset(self):
        with self._lock:
            self._records.clear()
            self._last_cleanup = time.time()


# Global rate limiter instance (singleton)
rate_limiter = InMemoryRateLimiter()


def get_client_identifier(request: Request, user: Optional[AuthenticatedUser] = None) -> str:
    """
    Resolves client identifier for rate limiting:
    - Authenticated users: user ID (`user:<user_id>`)
    - Unauthenticated/Guests: client IP (`ip:<client_ip>`)
    """
    if user and user.id:
        return f"user:{user.id}"

    # Extract client IP from proxy header or direct connection
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    return f"ip:{client_ip}"


def create_rate_limiter_dependency(
    scope: str,
    max_requests: int,
    window_seconds: int = 60,
    allow_unauthenticated: bool = False,
):
    """
    Factory creating a FastAPI dependency for rate limiting a specific route.
    """
    if allow_unauthenticated:
        async def dependency(
            request: Request,
            current_user: Optional[AuthenticatedUser] = Depends(get_optional_current_user),
        ):
            ident = get_client_identifier(request, current_user)
            key = f"{ident}:{scope}"
            allowed, retry_after = rate_limiter.check_rate_limit(
                key=key,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )
            if not allowed:
                raise RateLimitExceededException(
                    retry_after=retry_after,
                    detail=f"Rate limit exceeded for {scope}. Please wait {retry_after} seconds before trying again.",
                )
            return True

        return dependency

    async def dependency(
        request: Request,
        current_user: AuthenticatedUser = Depends(get_current_user),
    ):
        ident = get_client_identifier(request, current_user)
        key = f"{ident}:{scope}"
        allowed, retry_after = rate_limiter.check_rate_limit(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
        if not allowed:
            raise RateLimitExceededException(
                retry_after=retry_after,
                detail=f"Rate limit exceeded for {scope}. Please wait {retry_after} seconds before trying again.",
            )
        return True

    return dependency


# Standard pre-configured rate limit dependencies
rate_limit_analyze = create_rate_limiter_dependency(
    scope="ai_analyze",
    max_requests=getattr(settings, "RATE_LIMIT_ANALYZE_PER_MINUTE", 10),
    window_seconds=60,
    allow_unauthenticated=True,
)

rate_limit_projects_write = create_rate_limiter_dependency(
    scope="projects_write",
    max_requests=getattr(settings, "RATE_LIMIT_PROJECTS_WRITE_PER_MINUTE", 30),
    window_seconds=60,
    allow_unauthenticated=False,
)
