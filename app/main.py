"""
DishHome AI Call Center — FastAPI entry point.
"""

import os
import sys
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger
from slowapi.errors import RateLimitExceeded

from config.settings import settings

# Models / DB
from app.models import init_db

# Core
from app.core.voice_pipeline import voice_pipeline
from app.services.knowledge_base import knowledge_base
from app.services.cache_service import cache_service
from app.services.search_service import search_service
from app.services.storage_service import storage_service
from app.core.function_caller import function_caller

# Middleware
from app.api.middleware.security_headers import SecurityHeadersMiddleware
from app.api.middleware.audit import AuditMiddleware
from app.api.middleware.rate_limiter import limiter, rate_limit_handler

# Routes
from app.api.routes import (
    voice, calls, analytics, health, admin,
    auth, customers, packages, billing, tickets, vendors, network, agent, portal,
)


# ── Logging ──────────────────────────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stderr, level=settings.log_level, colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
)
os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
logger.add(settings.log_file, rotation="10 MB", retention="7 days", level=settings.log_level)


# ── Sentry (only if DSN configured) ──────────────────────────────────────────
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        environment=settings.app_env,
    )
    logger.info("Sentry initialized")


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("  DishHome AI Call Center — Starting Up")
    logger.info("=" * 60)

    try:
        await init_db()
    except Exception as e:
        logger.warning(f"DB init skipped (already migrated?): {e}")

    try:
        await search_service.initialize()
    except Exception as e:
        logger.warning(f"Elasticsearch init skipped: {e}")

    try:
        storage_service.ensure_buckets()
    except Exception as e:
        logger.warning(f"S3/MinIO init skipped: {e}")

    knowledge_base.load()
    function_caller.knowledge_base = knowledge_base

    await voice_pipeline.initialize()

    # OpenTelemetry FastAPI instrumentation
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry instrumentation enabled")
    except Exception as e:
        logger.debug(f"OpenTelemetry skipped: {e}")

    logger.success("All systems initialized")
    logger.info(f"API Docs:  http://{settings.app_host}:{settings.app_port}/docs")
    logger.info(f"Dashboard: http://{settings.app_host}:{settings.app_port}")

    yield

    logger.info("Shutting down...")
    await voice_pipeline.shutdown()
    await cache_service.close()
    await search_service.close()
    logger.info("DishHome AI Call Center stopped.")


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="AI-powered enterprise call center for DishHome ISP — voice, chat, CRM, billing, network, tickets",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Middleware (order matters — outermost first) ─────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)


# ── Prometheus instrumentation ───────────────────────────────────────────────
if settings.enable_prometheus:
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
        logger.info("Prometheus metrics enabled at /metrics")
    except Exception as e:
        logger.debug(f"Prometheus skipped: {e}")


# ── Routes ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(voice.router)
app.include_router(calls.router)
app.include_router(analytics.router)
app.include_router(customers.router)
app.include_router(packages.router)
app.include_router(billing.router)
app.include_router(tickets.router)
app.include_router(vendors.router)
app.include_router(network.router)
app.include_router(agent.router)
app.include_router(portal.router)
app.include_router(admin.router)


# ── Static / Dashboard ───────────────────────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def serve_dashboard():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "DishHome AI Call Center API",
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.get("/admin")
async def admin_page():
    admin_path = os.path.join(frontend_dir, "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return JSONResponse({"detail": "Admin page not found"}, status_code=404)


# ── Run Server ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower(),
    )
