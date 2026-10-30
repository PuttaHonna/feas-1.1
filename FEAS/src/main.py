"""
Forensic Evidence Analysis System (FEAS) - FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import torch

# Optimize PyTorch thread pool for memory-constrained cloud environments (e.g. 512MB RAM)
try:
    torch.set_num_threads(1)
    if hasattr(torch, "set_num_interop_threads"):
        torch.set_num_interop_threads(1)
except Exception:
    pass

from src.api.routes import router as api_router
from src.api.firebase_routes import router as firebase_router
from src.config import REPORTS_DIR, STORAGE_DIR, TEMP_DIR, RESULTS_DIR
from src.db.audit import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to handle database initialization on startup."""
    init_db()
    yield


app = FastAPI(
    title="Forensic Evidence Analysis System (FEAS)",
    description="Court-Admissible Computer Vision & Forensic Integrity Pipeline (Phase 1)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
origins = [
    "https://feas-forensics.web.app",
    "https://feas-forensics.firebaseapp.com",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.web\.app|https://.*\.firebaseapp\.com|http://localhost:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Directories for Media & Reports
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")
app.mount("/temp", StaticFiles(directory=str(TEMP_DIR)), name="temp")
app.mount("/results", StaticFiles(directory=str(RESULTS_DIR)), name="results")

# Mount High-Graphics Web Dashboard if built
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/dashboard", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="dashboard")
    if (FRONTEND_DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    if (FRONTEND_DIST / "samples").exists():
        app.mount("/samples", StaticFiles(directory=str(FRONTEND_DIST / "samples")), name="samples")

# Include API Router
app.include_router(api_router)
app.include_router(firebase_router)


@app.get("/")
async def root(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and FRONTEND_DIST.exists():
        return RedirectResponse(url="/dashboard/")
    return {
        "system": "Forensic Evidence Analysis System (FEAS)",
        "version": "1.0.0",
        "docs_url": "/docs",
        "dashboard_url": "/dashboard/",
        "api_prefix": "/api/v1"
    }


@app.get("/favicon.svg", include_in_schema=False)
async def favicon_svg():
    f = FRONTEND_DIST / "favicon.svg"
    if f.exists():
        return FileResponse(str(f))
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/icons.svg", include_in_schema=False)
async def icons_svg():
    f = FRONTEND_DIST / "icons.svg"
    if f.exists():
        return FileResponse(str(f))
    raise HTTPException(status_code=404, detail="Icons not found")


@app.get("/healthz")
@app.get("/health")
async def healthz():
    return {
        "status": "ok",
        "version": "2.4.2",
        "device": "cpu",
        "easyocr_disabled": os.getenv("DISABLE_EASYOCR", "1") == "1",
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
