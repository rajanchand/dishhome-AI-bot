"""
DishHome AI Voice Bot - Main Application
FastAPI entry point with all routes, middleware, and lifecycle management.
"""

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from config.settings import settings
from app.models.database import init_db
from app.core.voice_pipeline import voice_pipeline
from app.services.knowledge_base import knowledge_base
from app.api.routes import voice, calls, analytics, health, admin


# ── Logging Setup ───────────────────────────────────────────
logger.remove()
logger.add(sys.stderr, level=settings.log_level, colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")

os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)
logger.add(settings.log_file, rotation="10 MB", retention="7 days",
           level=settings.log_level)


# ── Application Lifecycle ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("=" * 60)
    logger.info("  DishHome AI Voice Bot - Starting Up")
    logger.info("=" * 60)

    # Initialize database
    await init_db()

    # Load knowledge base
    knowledge_base.load()

    # Initialize voice pipeline
    await voice_pipeline.initialize()

    logger.success("All systems initialized. Ready to serve!")
    logger.info(f"Dashboard: http://{settings.app_host}:{settings.app_port}")
    logger.info(f"API Docs:  http://{settings.app_host}:{settings.app_port}/docs")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await voice_pipeline.shutdown()
    logger.info("DishHome AI Voice Bot stopped.")


# ── FastAPI Application ─────────────────────────────────────
app = FastAPI(
    title="DishHome AI Voice Bot",
    description="AI-powered bilingual voice bot for DishHome ISP call center",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routes ─────────────────────────────────────────
app.include_router(voice.router)
app.include_router(calls.router)
app.include_router(analytics.router)
app.include_router(health.router)
app.include_router(admin.router)

# ── Static Files (Frontend Dashboard) ───────────────────────
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def serve_dashboard():
    """Serve the agent dashboard."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "DishHome AI Voice Bot API", "docs": "/docs"}


@app.get("/dashboard")
async def dashboard_redirect():
    """Redirect to dashboard."""
    return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/admin")
async def admin_page():
    """Serve the admin dashboard."""
    admin_path = os.path.join(frontend_dir, "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return {"message": "Admin Page not found"}


# ── Run Server ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower(),
    )
