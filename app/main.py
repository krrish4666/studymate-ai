from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine
from app.models.base import Base
from app.api.v1 import auth, upload, features, history, export, profile


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="StudyMate AI HUB",
    version="2.0.0",
    description="Academic productivity web application powered by Google Gemini AI",
    lifespan=lifespan,
)

import uuid
import time
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main")

@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Add request_id to request state so other parts of the app could use it
    request.state.request_id = request_id
    
    logger.info(f"Req [{request_id}] started {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    logger.info(f"Req [{request_id}] completed {response.status_code} in {duration:.3f}s")
    
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Req [{request_id}] Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred."},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(features.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("static/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    file_path = Path("static") / (full_path if full_path else "index.html")
    if not file_path.is_file():
        file_path = Path("static") / f"{full_path or 'index'}.html"
    if not file_path.is_file():
        file_path = Path("static") / "index.html"

    return FileResponse(
        file_path,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
