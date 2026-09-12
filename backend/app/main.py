import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.middleware import (
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
    SafeLoggingFilter,
    request_id_ctx,
)
from app.core.rate_limiter import RateLimitExceededException
from app.api.v1.endpoints import health, analyze, projects, recovery, plans

# Setup structured logging with correlation ID and secret redaction
logging_handler = logging.StreamHandler()
logging_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] [req:%(request_id)s] %(name)s: %(message)s")
)
logging_handler.addFilter(SafeLoggingFilter())

root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
root_logger.handlers = [logging_handler]

logger = logging.getLogger("shiftly.main")

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Shiftly — Find what matters. Backend API for communication intelligence layer.",
    version=settings.VERSION,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
)

# 1. Security Headers Middleware (outermost for security on all responses)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "PATCH", "PUT"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["X-Request-ID", "Retry-After", "X-Response-Time"],
)

# 3. Request Correlation ID Middleware
app.add_middleware(CorrelationIdMiddleware)


# Global Exception Handlers
@app.exception_handler(RateLimitExceededException)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededException):
    req_id = request_id_ctx.get() or "unknown"
    headers = {"Retry-After": str(exc.retry_after), "X-Request-ID": req_id}
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": exc.detail, "request_id": req_id},
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = request_id_ctx.get() or "unknown"
    # Provide sanitized error messages without echoing sensitive payloads
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        errors.append(f"{loc}: {err.get('msg')}")
    detail_msg = "; ".join(errors) if errors else "Invalid request payload."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail_msg, "request_id": req_id},
        headers={"X-Request-ID": req_id},
    )




@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = request_id_ctx.get() or "unknown"
    headers = dict(exc.headers) if exc.headers else {}
    headers["X-Request-ID"] = req_id
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": req_id},
        headers=headers,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    req_id = request_id_ctx.get() or "unknown"
    logger.exception(f"Unhandled server exception: {exc}")
    # Never leak Python stack traces, internal paths, or credentials in responses
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please contact support or try again later.",
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id},
    )


# Register routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(recovery.router, prefix="/api", tags=["recovery"])
app.include_router(plans.router, prefix="/api", tags=["plans"])


@app.get("/", summary="Root Endpoint")
def read_root():
    return {
        "service": settings.PROJECT_NAME,
        "tagline": settings.TAGLINE,
        "version": settings.VERSION,
        "endpoints": {
            "health": "/api/health",
            "ready": "/api/ready",
            "analyze": "/api/analyze",
            "projects": "/api/projects",
            "plans": "/api/plans",
        },
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT != "production",
    )

