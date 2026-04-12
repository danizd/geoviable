"""
GeoViable — FastAPI Application Entry Point

Creates the FastAPI app, configures CORS, sets up the database session,
registers API routers, and attaches middleware for upload size limiting
and structured JSON logging.
"""

import logging
import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database import engine, get_db
from app.api.router import api_router

# ── Load configuration ──
settings = get_settings()

# ── Structured JSON logger ──
# In production, logs go to stdout (captured by Docker).
# In development, a simple stream logger is sufficient.
logger = logging.getLogger("geoviable")
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
)
logger.addHandler(handler)


# ── Application lifespan ──
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Runs on startup and shutdown.

    On startup: verify database connectivity.
    On shutdown: dispose of the connection pool.
    """
    # Startup: test DB connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified on startup.")
    except Exception:
        logger.exception("Failed to connect to the database on startup.")
        raise

    yield

    # Shutdown: clean up pool
    engine.dispose()
    logger.info("Database connection pool disposed.")


# ── Create FastAPI app ──
app = FastAPI(
    title="GeoViable API",
    description=(
        "Environmental feasibility assessment API. "
        "Analyses user polygons against official environmental layers "
        "(Red Natura 2000, flood zones, DPH, etc.) and generates PDF reports."
    ),
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ── Upload Size Limiter Middleware ──
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    """
    Reject requests with a body larger than the configured maximum.

    Applied to all methods that can carry a body (POST).
    GET requests skip this check.
    """
    content_length = request.headers.get("content-length")
    if content_length:
        size_bytes = int(content_length)
        if size_bytes > settings.max_upload_size_bytes:
            logger.warning(
                "Payload too large: %s bytes (max %s)",
                size_bytes,
                settings.max_upload_size_bytes,
            )
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": (
                            f"Request body exceeds the maximum allowed size "
                            f"of {settings.max_upload_size_mb} MB."
                        ),
                    }
                },
            )
    return await call_next(request)


# ── Request Logging Middleware ──
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log every incoming request with method, path, and response time.
    """
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "%s %s — %d (%.0f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ── Register API router ──
# Mount under /api/v1 so all routes are prefixed accordingly.
app.include_router(api_router, prefix="/api/v1")


# ── Health Check (outside the versioned router for simplicity) ──
@app.get("/api/v1/health")
async def health_check():
    """
    Docker health check and monitoring endpoint.

    Returns the application status and database connectivity.
    """
    db_status = "disconnected"
    http_status = 200
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        http_status = 503

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "version": "1.0.0",
    }
