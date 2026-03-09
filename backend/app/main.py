"""
OperatorOS — AuditMind API

FastAPI application entry-point: middleware, routers, lifecycle events.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

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

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Lightweight liveness probe."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
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
