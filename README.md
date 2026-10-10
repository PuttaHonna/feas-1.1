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

## 🚀 Quick Start

### 1. Environment Setup
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r FEAS/requirements.txt
pip install -r deep_learning_forensic_investigator/requirements.txt
```

### 2. Running Services

#### Deep Learning Forensic Investigator UI (Port 8502)
```powershell
cd deep_learning_forensic_investigator
streamlit run app.py --server.port 8502
```

#### FEAS Forensic Workstation UI (Port 8501)
```powershell
cd FEAS
streamlit run src/ui/app.py --server.port 8501
```

#### FEAS FastAPI Backend (Port 8000)
```powershell
cd FEAS
uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Interactive API documentation available at: `http://127.0.0.1:8000/docs`

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
