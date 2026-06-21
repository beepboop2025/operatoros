"""
OperatorOS — AuditMind API

FastAPI application entry-point: middleware, routers, lifecycle events.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import uuid as _uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import get_settings
from app.database import engine

settings = get_settings()

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("operatoros")


# ── Lifecycle ────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    logger.info("OperatorOS API starting up (env=%s)", settings.ENVIRONMENT)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)
        raise

    yield

    # Shutdown
    logger.info("OperatorOS API shutting down")
    await engine.dispose()
    logger.info("Database engine disposed")


# ── Application ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="OperatorOS - AuditMind API",
    version="1.0.0",
    description="AI-powered audit and compliance platform for CA firms",
    lifespan=lifespan,
)

# ── Request ID Middleware ─────────────────────────────────────────────────────


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request/response for traceability."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(_uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)

# ── Audit Middleware ─────────────────────────────────────────────────────────

from app.middleware.audit import AuditMiddleware  # noqa: E402

app.add_middleware(AuditMiddleware)

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
# Each router is imported lazily so circular-import issues are avoided.
# Routes that do not yet exist will be registered once their modules are created.

_ROUTER_CONFIG: list[tuple[str, str, str]] = [
    ("app.routes.auth", "router", "/api/auth"),
    ("app.routes.clients", "router", "/api/clients"),
    ("app.routes.documents", "router", "/api/documents"),
    ("app.routes.queries", "router", "/api/queries"),
    ("app.routes.compliance", "router", "/api/compliance"),
    ("app.routes.compute", "router", "/api/compute"),
    ("app.routes.notices", "router", "/api/notices"),
    ("app.routes.draft", "router", "/api/draft"),
    ("app.routes.dashboard", "router", "/api/dashboard"),
    ("app.routes.workflow", "router", "/api/workflow"),
    ("app.routes.audit", "router", "/api/audit"),
    ("app.routes.tasks_status", "router", "/api/tasks"),
    ("app.routes.firms", "router", "/api/firms"),
    ("app.routes.nri", "router", "/api/nri"),
    ("app.routes.notifications", "router", "/api/notifications"),
    ("app.routes.tax_intel", "router", "/api/tax-intel"),
]


def _register_routers() -> None:
    import importlib

    for module_path, attr_name, prefix in _ROUTER_CONFIG:
        try:
            mod = importlib.import_module(module_path)
            router = getattr(mod, attr_name)
            app.include_router(router, prefix=prefix)
            logger.info("Registered router %s at %s", module_path, prefix)
        except (ModuleNotFoundError, AttributeError) as exc:
            logger.warning("Skipping router %s: %s", module_path, exc)


_register_routers()

# ── Health & Root ────────────────────────────────────────────────────────────


@app.get("/api/health", tags=["health"])
async def health_check() -> dict:
    """Lightweight liveness probe — checks database and Redis."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    # Check Redis — reuse the shared pool from dependency injection
    redis_status = "healthy"
    try:
        from app.dependencies import _redis_pool
        if _redis_pool is not None:
            await _redis_pool.ping()
        else:
            # Pool not yet initialised; create it via the standard path
            import redis.asyncio as aioredis
            _pool = aioredis.from_url(
                settings.REDIS_URL, decode_responses=True, max_connections=20,
            )
            try:
                await _pool.ping()
            finally:
                await _pool.aclose()
    except Exception:
        redis_status = "unhealthy"

    overall = "ok" if db_status == "healthy" and redis_status == "healthy" else "degraded"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
        "environment": settings.ENVIRONMENT,
        "version": app.version,
    }


@app.get("/", tags=["root"])
async def root() -> dict:
    """API information."""
    return {
        "name": app.title,
        "version": app.version,
        "docs": "/docs",
        "health": "/api/health",
    }
