# FEAS 2.0 & Deep Learning Forensics Investigator

> **Educational & Research Forensic Video & Image Analysis Suite**
> 
> *Disclaimer: This software is an educational and research prototype. Model outputs are strictly advisory and require human expert review. It does not claim court admissibility or automated suspect identification, and strictly preserves original digital evidence without destructive modification or generative hallucination.*

---

## 📌 Project Overview

This repository contains a full-stack forensic engineering and computer vision platform designed for digital forensics investigation and CCTV video analysis:

1. **Deep Learning Forensic Investigator (`deep_learning_forensic_investigator/`)**:
   - **CCTV Video Analysis**: Integrity hash computation (SHA-256), working copy generation, CLAHE & Bilateral enhancement, YOLOv8 object detection, multi-object tracking, forensic event extraction, annotated video rendering, and full JSON audit trail export.
   - **Image Tampering Detection**: ELA (Error Level Analysis), Noise Variance analysis, Copy-Move forgery detection, and Deep Learning tampering segmentation.
   - **Video Tampering Detection**: Frame insertion/deletion, temporal anomaly detection, and optical flow variance analysis.

2. **FEAS Forensic Engine & Workstation (`FEAS/`)**:
   - **FastAPI Backend (`src/api`)**: High-throughput REST API with automated forensic jobs, health checks, metrics, and CCTV analysis endpoint (`/api/v1/cctv/analyze`).
   - **Streamlit Forensic Workstation (`src/ui`)**: Multi-tab investigator interface including Evidence Locker, Tampering Diagnostics, CCTV Video Pipeline, and Export Engine.
   - **Interactive 3D Dashboard (`forensic_react_dashboard/`)**: Modern web dashboard with 3D canvas and live forensic metrics visualization.

---

## 🚀 Universal Cross-Platform Quick Start

FEAS 2.0 provides cross-platform launchers that automatically configure and run on **Windows, macOS, Linux, and Docker**:

### 1. Unified Launchers (Recommended)

| Operating System | Native Command | Python Command |
|---|---|---|
| **Windows (CMD / PowerShell)** | `run.bat` or `.\run.ps1` | `python run.py` |
| **Linux / macOS** | `./run.sh` | `python3 run.py` |
| **Docker (Any OS)** | `docker compose up` | `python run.py docker` |

### 2. Available Run Commands

```bash
# 1. Inspect platform, dependencies, and GPU/MPS acceleration
python run.py doctor

# 2. Run all services simultaneously (API + Workstation + Investigator)
python run.py all

# 3. Or launch individual components:
python run.py api           # FEAS FastAPI Backend (:8000)
python run.py workstation   # FEAS Forensic Workstation UI (:8501)
python run.py investigator  # Deep Learning Investigator UI (:8502)
python run.py frontend      # Forensic 3D React Dashboard

# 4. Run automated test suite across all modules (94+ tests)
python run.py test
```

Interactive API documentation available at: `http://127.0.0.1:8000/docs`
For complete OS-specific details (Ubuntu, Apple Silicon Metal, Docker), see [PLATFORMS.md](file:///c:/Users/user/projects/FEAS%202.0%20(2)/FEAS%202.0/PLATFORMS.md).

---

## 🧪 Testing

Run automated test suites across both modules:

```powershell
# CCTV Pipeline Test Suite
pytest deep_learning_forensic_investigator/tests/test_cctv_pipeline.py -v

# FEAS Core Forensic Suite (41 tests)
pytest FEAS/tests -v
```

---

## 📜 Ethical & Prototype Constraints
- **Preservation of Original Evidence**: Original files are read-only; analysis strictly operates on derived working copies.
- **No Generative AI Hallucinations**: Zero generative inpainting, face hallucination, or synthetic modifications.
- **Traceability**: All processing steps log cryptographic hashes (SHA-256), timestamps, and parameter metadata in compliance with digital evidence preservation principles.
