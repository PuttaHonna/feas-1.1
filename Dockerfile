# ====================================================================
# FEAS 2.0 & Deep Learning Forensic Investigator
# Multi-Platform Production Dockerfile (linux/amd64 & linux/arm64)
# Compatible with Windows Docker Desktop, macOS Docker (Apple Silicon),
# and Linux Docker Engine.
# ====================================================================

FROM python:3.11-slim

# Prevent interactive prompts during package install
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KMP_DUPLICATE_LIB_OK=TRUE

# Install OS libraries for OpenCV, Video Decoding, and PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    sqlite3 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy unified requirements first to leverage Docker layer caching
COPY requirements.txt /app/

# Install Python dependencies (universal wheels)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy complete repository structure
COPY . /app/

# Ensure all evidence vault, storage, and report directories exist
RUN mkdir -p /app/data/evidence_vault \
             /app/data/working_copies \
             /app/data/artifacts \
             /app/FEAS/storage \
             /app/FEAS/reports \
             /app/FEAS/temp \
             /app/FEAS/data

# Ports:
# 8000: FEAS FastAPI Backend & Swagger Docs
# 8501: FEAS Forensic Workstation UI (Streamlit)
# 8502: Deep Learning Forensic Investigator UI (Streamlit)
EXPOSE 8000 8501 8502

# Healthcheck targeting FastAPI REST health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: Launches all services via cross-platform run.py
CMD ["python", "run.py", "all"]
