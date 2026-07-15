from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.v1 import auth, upload, features


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="StudyMate AI HUB",
    version="2.0.0",
    description="Academic productivity web application powered by Google Gemini AI",
    lifespan=lifespan,
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

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}
