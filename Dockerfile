# ====================================================================
# FEAS 2.0 - Production Dockerfile Optimized for 512MB RAM
# Multi-Platform: linux/amd64 & linux/arm64
# ====================================================================

FROM python:3.11-slim

# Prevent interactive prompts during package install & optimize CPU threads
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KMP_DUPLICATE_LIB_OK=TRUE \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    TORCH_NUM_THREADS=1 \
    DISABLE_EASYOCR=1

# Install minimal OS libraries required for OpenCV and FFmpeg video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Step 1: Install CPU-only PyTorch & Torchvision first (saves ~2.5 GB download and ~200MB RAM)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Step 2: Install dependencies (leveraging pre-installed CPU torch)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Step 3: Copy repository structure (respecting .dockerignore)
COPY . /app/

# Ensure all runtime evidence, storage, and report directories exist and are writable by any user UID
RUN mkdir -p /app/data/evidence_vault \
             /app/data/working_copies \
             /app/data/artifacts \
             /app/FEAS/storage \
             /app/FEAS/reports \
             /app/FEAS/temp \
             /app/FEAS/results \
             /app/FEAS/data && \
    chmod -R 777 /app

EXPOSE 7860 8000 10000

ENV PYTHONPATH=/app/FEAS
WORKDIR /app/FEAS

# Healthcheck targeting FastAPI REST health endpoint (supports Render:10000 and Hugging Face:7860)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/health || exit 1

# Default command: Launches single-process FastAPI backend on $PORT with minimal RAM
CMD ["sh", "-c", "exec python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
