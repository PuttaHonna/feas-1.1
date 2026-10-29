# 🌐 FEAS 2.0 - Cross-Platform Execution Guide

FEAS 2.0 and the Deep Learning Forensics Investigator Suite are engineered to run seamlessly across **all major operating systems and environments**:

- 🪟 **Microsoft Windows** (10 / 11 / Server / WSL2)
- 🍏 **Apple macOS** (Apple Silicon M1/M2/M3/M4 & Intel x86_64)
- 🐧 **Linux** (Ubuntu, Debian, Fedora, RHEL, Arch, CentOS)
- 🐳 **Docker & Docker Compose** (Containerized Zero-Setup)
- ☁️ **Cloud & Google Colab** (NVIDIA T4 / A100 / H100)

---

## ⚡ 1-Command Universal Launchers

FEAS 2.0 includes platform-specific native scripts that automatically detect Python, configure your environment, and start services:

| Platform | Native Command | Equivalent Python Command |
|---|---|---|
| **Windows (CMD)** | `run.bat` | `python run.py` |
| **Windows (PowerShell)** | `.\run.ps1` | `python run.py` |
| **Linux / macOS** | `./run.sh` | `python3 run.py` |
| **Docker** | `docker compose up` | `python run.py docker` |

Run without arguments to access the **Interactive Menu**, or supply a command like:
```bash
python run.py all          # Start API + Workstation + Investigator simultaneously
python run.py test         # Run 94+ automated unit & integration tests
python run.py doctor       # Check system tools, ports, and hardware acceleration
```

---

## 🪟 Platform 1: Microsoft Windows

### Requirements
- **Python**: 3.10, 3.11, or 3.12 (from [python.org](https://www.python.org/downloads/); check *"Add Python to PATH"* during install).
- *(Optional)* **NVIDIA GPU Driver & CUDA Toolkit**: If using an NVIDIA GPU for real-time YOLOv8 object tracking.

### Setup & Run
Open PowerShell or Command Prompt:

```powershell
# 1. Clone & Enter Directory
cd "FEAS 2.0"

# 2. Setup Virtual Environment (Recommended)
python -m venv .venv
.venv\Scripts\activate

# 3. Install Universal Dependencies
python run.py setup

# 4. Verify System Readiness
python run.py doctor

# 5. Launch All Services
python run.py all
```

---

## 🍏 Platform 2: Apple macOS (Apple Silicon & Intel)

FEAS 2.0 natively supports **Apple Silicon (M1/M2/M3/M4) Metal Performance Shaders (MPS)** for GPU-accelerated tensor math without requiring CUDA.

### Requirements
- Install Python and FFmpeg via [Homebrew](https://brew.sh):
  ```bash
  brew install python@3.11 ffmpeg
  ```

### Setup & Run
Open Terminal:

```bash
# 1. Clone & Enter Directory
cd "FEAS 2.0"

# 2. Make launcher executable
chmod +x run.sh

# 3. Setup Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# 4. Install Dependencies
python3 run.py setup

# 5. Check System & MPS Acceleration
python3 run.py doctor

# 6. Launch All Services
./run.sh all
```

---

## 🐧 Platform 3: Linux (Ubuntu / Debian / Fedora / Arch)

### System Libraries
OpenCV and PyTorch require standard Linux media libraries:

```bash
# Ubuntu / Debian
sudo apt-get update && sudo apt-get install -y \
    python3-pip python3-venv ffmpeg libgl1 libglib2.0-0 sqlite3 curl

# Fedora / RHEL
sudo dnf install -y python3-pip ffmpeg mesa-libGL glib2 sqlite

# Arch Linux
sudo pacman -S python-pip ffmpeg mesa glib2 sqlite
```

### Setup & Run
```bash
cd "FEAS 2.0"
chmod +x run.sh

python3 -m venv .venv
source .venv/bin/activate

python3 run.py setup
python3 run.py doctor
./run.sh all
```

---

## 🐳 Platform 4: Docker & Docker Compose (Any OS)

Run the entire suite with zero local dependency management on Windows Docker Desktop, macOS Docker, or Linux Docker Engine.

### 1. Standard (Universal CPU / Apple Silicon / x86_64)
```bash
# Build & Start all services
docker compose up --build

# Run in background (detached)
docker compose up -d
```

### 2. NVIDIA GPU Acceleration (Linux / Windows WSL2)
For dedicated NVIDIA GPU passthrough:
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

---

## 🌐 Service Ports & Access URLs

Once launched, the suite exposes the following endpoints:

| Service | Port | Local URL | Purpose |
|---|---|---|---|
| **FEAS REST API Docs** | `8000` | [http://localhost:8000/docs](http://localhost:8000/docs) | OpenAPI / Swagger interactive documentation |
| **FEAS Web Dashboard** | `8000` | [http://localhost:8000/dashboard](http://localhost:8000/dashboard) | High-graphics forensic 3D dashboard |
| **FEAS Workstation UI** | `8501` | [http://localhost:8501](http://localhost:8501) | Streamlit multi-tab forensic investigator |
| **DL Investigator UI** | `8502` | [http://localhost:8502](http://localhost:8502) | Deep learning tampering & CCTV suite |

---

## 🧪 Testing Across Platforms

FEAS 2.0 provides a single test command that runs all 94+ tests across the entire codebase while maintaining strict isolation between subpackages:

```bash
python run.py test
```
