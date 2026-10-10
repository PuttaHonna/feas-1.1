# Dockerfile for Forensic Evidence Analysis System (FEAS)
# Target Hardware: NVIDIA T4 / A100 (CUDA 12.x, PyTorch 2.1+)

FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install system dependencies for OpenCV, ExifTool, and ReportLab
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libexif-dev \
    libmagic1 \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set up Python virtual environment
RUN python3.11 -m venv /opt/venv

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Initialize directories & database
RUN mkdir -p storage reports temp data

EXPOSE 8000 8501

CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port 8000 & streamlit run src/ui/app.py --server.port 8501 --server.address 0.0.0.0"]
