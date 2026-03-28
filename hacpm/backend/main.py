"""
HACPM - Home Assistant Chores, Plants & Maintenance
Main FastAPI application with WebSocket support.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import init_db
from .routers import tasks, users, labels, analytics, photos
from .services.sync import manager

logger = logging.getLogger("hacpm")

INGRESS_PATH = os.environ.get("HACPM_INGRESS_PATH", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    logger.info("Initializing HACPM database...")
    await init_db()
    logger.info("HACPM is ready!")
    yield


app = FastAPI(
    title="HACPM - Home Assistant Chores, Plants & Maintenance",
    version="0.1.0",
    lifespan=lifespan,
    root_path=INGRESS_PATH,
)

# ── Register API routers ──
app.include_router(tasks.router)
app.include_router(users.router)
app.include_router(labels.router)
app.include_router(analytics.router)
app.include_router(photos.router)


# ── WebSocket endpoint for real-time sync ──

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int = Query(default=None),
):
    """WebSocket connection for real-time task updates."""
    await manager.connect(websocket, user_id=user_id)
    try:
        while True:
            # Keep connection alive; clients send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"event":"pong","data":null}')
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id=user_id)


# ── Serve frontend static files ──

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Mount static files
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the main frontend page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
