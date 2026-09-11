import time
import re
import uuid
import logging
from contextvars import ContextVar
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("shiftly.access")

# Context variable to hold request correlation ID across async execution
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id_ctx", default=None)

SAFE_REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Ensures every HTTP request has a clean, validated correlation ID (X-Request-ID).
    Measures execution duration, attaches X-Response-Time header, and emits structured
    operational access logs on request completion.
    """

    async def dispatch(self, request: Request, call_next):
        raw_id = request.headers.get("X-Request-ID")
        if raw_id and SAFE_REQUEST_ID_PATTERN.match(raw_id.strip()):
            correlation_id = raw_id.strip()
        else:
            correlation_id = str(uuid.uuid4())

        token = request_id_ctx.set(correlation_id)
        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            response.headers["X-Request-ID"] = correlation_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            # Metadata-only operational log (never logs user text or bodies)
            logger.info(
                "request_finished method=%s path=%s status=%d duration_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                "request_failed method=%s path=%s error=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                type(exc).__name__,
                duration_ms,
            )
            raise
        finally:
            request_id_ctx.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Attaches defense-in-depth HTTP security headers to API responses.
    Modern header allocation:
    - X-Content-Type-Options: nosniff (FastAPI responsibility)
    - X-Frame-Options: DENY (FastAPI responsibility)
    - Referrer-Policy: strict-origin-when-cross-origin (FastAPI responsibility)
    - Permissions-Policy: geolocation=(), camera=(), microphone=() (FastAPI responsibility)
    - Content-Security-Policy: frame-ancestors 'none'; (FastAPI anti-framing scope; full HTML CSP is Next.js responsibility)
    - Note: X-XSS-Protection is intentionally omitted as it is obsolete/deprecated by modern standards.
    - Note: Strict-Transport-Security (HSTS) is delegated to the HTTPS hosting/reverse-proxy layer.
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

        # Anti-framing policy for API endpoints without blocking docs or legitimate clients
        if not response.headers.get("Content-Security-Policy"):
            response.headers["Content-Security-Policy"] = "frame-ancestors 'none';"

        return response



class SafeLoggingFilter(logging.Filter):
    """
    Logging filter that:
    1. Injects the active correlation request_id into the log record.
    2. Redacts Bearer tokens, API keys, and connection strings from log output.
    """

    TOKEN_REDACTION_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9-_=.]+", re.IGNORECASE)
    KEY_REDACTION_PATTERN = re.compile(r"((?:apikey|key|secret|password)=)[A-Za-z0-9-_]+", re.IGNORECASE)

    def filter(self, record: logging.LogRecord) -> bool:
        # Inject correlation ID
        req_id = request_id_ctx.get()
        record.request_id = req_id if req_id else "-"

        # Redact secrets in message if present
        if isinstance(record.msg, str):
            record.msg = self.TOKEN_REDACTION_PATTERN.sub(r"\1[REDACTED]", record.msg)
            record.msg = self.KEY_REDACTION_PATTERN.sub(r"\1[REDACTED]", record.msg)

        return True
