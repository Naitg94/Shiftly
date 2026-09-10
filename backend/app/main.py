import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Shiftly API",
    description="Shiftly — Find what matters. Backend API for communication intelligence layer.",
    version="0.1.0",
)

# CORS configuration
allowed_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
allowed_origins: List[str] = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/", summary="Root Endpoint")
def read_root():
    return {
        "service": "Shiftly API",
        "tagline": "Find what matters.",
        "health_endpoint": "/api/health",
    }


@app.get("/api/health", response_model=HealthResponse, summary="Health Check Endpoint")
def get_health():
    return HealthResponse(
        status="ok",
        service="shiftly-backend",
        version="0.1.0",
    )
