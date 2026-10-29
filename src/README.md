# Deep Learning Forensics Investigator — Core Engine

> **Notice:** Experimental model output — requires qualified human review.
> This software is an experimental digital-forensics research prototype. Model outputs are strictly advisory and require qualified human review. It does not claim court admissibility, legal conclusions, guilt, suspect identity, firearm identification, wound diagnosis, cause of death, or bullet caliber.

---

## 🏛️ Stage 1: Evidence Integrity & Common Architecture

### 1. Architectural Principles
1. **Preservation of Original Evidence**: Original files are placed in `data/evidence_vault/` and made read-only (`0o444`). Cryptographic SHA-256 hashes are verified before and after copying.
2. **Derived Working Copies**: All computational pipelines operate exclusively on derived working copies in `data/working_copies/`.
3. **Append-Only SQLite Audit Trail**: Uses SQLite in Write-Ahead Logging (`WAL`) mode (`PRAGMA journal_mode=WAL;`). Every run, evidence intake, and intermediate artifact hash is logged to `evidence_ledger`, `processing_runs`, and `audit_events`.
4. **Pre-Inference Quality Gate**: Strictly validates images for resolution, Laplacian variance blur threshold (`>= 25.0`), and exposure (`15.0 <= mean luminance <= 245.0`). Rejects poor quality inputs safely without making speculative predictions.
5. **No Hallucinated Data**: Only measured metadata, calculated hashes, and empirical metrics are recorded.

---

## 🧪 Testing

Run the automated test suite from the repository root:

```powershell
# Windows
python -m pytest tests -v

# Linux / Google Colab
python3 -m pytest tests -v
```

---

## 📁 Implemented Modules (`src/common`)

- [`src/common/config.py`](file:///src/common/config.py): Storage paths, deterministic random seeds, and forensic disclaimer constants.
- [`src/common/hashing.py`](file:///src/common/hashing.py): Chunked SHA-256 streaming hashing and perceptual hashing (pHash/dHash).
- [`src/common/file_validation.py`](file:///src/common/file_validation.py): Extension checking, magic byte inspection, and stream decodability validation.
- [`src/common/audit_db.py`](file:///src/common/audit_db.py): Append-only SQLite WAL database interface.
- [`src/common/quality_gate.py`](file:///src/common/quality_gate.py): Laplacian blur, luminance, and resolution gates.
- [`src/common/utils.py`](file:///src/common/utils.py): Evidence vault preservation, working-copy cloning, and random seed setting.

---

## 🔍 Stage 2: Module 1 — Image Tampering Detection

### 1. Components
- [`src/tampering/dataset_registry.json`](file:///src/tampering/dataset_registry.json): Records legitimate, public, documented datasets (CASIA v2.0, CoMoFoD, Columbia), licenses, counts, and limitations.
- [`src/tampering/dataset_audit.py`](file:///src/tampering/dataset_audit.py): Audits datasets, removes corrupt files, clusters exact duplicates (SHA-256) and near-duplicates (pHash), checks for class leakage, and creates non-overlapping train/val/test splits.
- [`src/tampering/train.py`](file:///src/tampering/train.py): PyTorch training for ResNet18 and EfficientNet-B0 with train-only augmentations, class weights, early stopping, and validation F1 checkpointing.
- [`src/tampering/evaluate.py`](file:///src/tampering/evaluate.py): Single-pass test evaluation and robustness stress testing (JPEG recompression Q60, blur, brightness, rescaling).
- [`src/tampering/predict.py`](file:///src/tampering/predict.py): Safe inference pipeline with pre-inference quality gating, uncertainty thresholding (`0.65`), and strictly advisory wording.
- [`src/tampering/explain.py`](file:///src/tampering/explain.py): Grad-CAM explanatory overlay with mandatory non-evidentiary banner.
- [`src/tampering/run_tampering.py`](file:///src/tampering/run_tampering.py): Unified CLI tool for audit, train, evaluate, and predict commands.

### 2. CLI Execution Examples
```powershell
# 1. Audit a dataset directory
python src/tampering/run_tampering.py audit --dataset-dir path/to/dataset --output-manifest data/splits.json

# 2. Train baseline ResNet18
python src/tampering/run_tampering.py train --manifest data/splits.json --output-dir data/checkpoints/tampering --arch resnet18 --epochs 10

# 3. Evaluate on untouched test data & run robustness tests
python src/tampering/run_tampering.py evaluate --checkpoint data/checkpoints/tampering/tampering_resnet18_best.pt --manifest data/splits.json --output-report data/tampering_eval.json

# 4. Predict on a single image with Grad-CAM
python src/tampering/run_tampering.py predict --checkpoint data/checkpoints/tampering/tampering_resnet18_best.pt --image path/to/evidence.jpg
```

---

## 📹 Stage 3: Module 2 — CCTV Video Enhancement, Object Detection & Tracking

### 1. Evidentiary Preservation
- **Original Preservation**: Original footage is verified via SHA-256 and stored read-only in `data/evidence_vault/`.
- **Derived Working Copy**: Analysis runs solely on working copies in `data/working_copies/`.
- **Zero Hallucination / Generative Modification**: Only deterministic OpenCV filters are applied (gamma LUT, CLAHE on luminance, bilateral filter, unsharp mask).
- **Mandatory Watermark Banner**: Every derived frame is stamped:
  `"Derived working image for visualization and automated analysis. Original footage remains unchanged."`
- **Restricted COCO Classes Only**: Strictly limited to 10 standard surveillance objects (`person`, `bicycle`, `car`, `motorcycle`, `bus`, `truck`, `backpack`, `handbag`, `suitcase`, `cell phone`).
- **Forbidden Categorization**: Strictly excludes face recognition, identity, weapons, crime detection, suspicious behaviour, emotion, or intent.
- **Objective Surveillance Events**: Only records factual events (`first_detected`, `entered_frame`, `exited_frame`, `duration_threshold_exceeded`, `roi_entered`, `roi_exited`).

### 2. CLI Execution Examples
```powershell
# Run full forensic CCTV pipeline
python src/cctv/run_cctv.py --video path/to/surveillance.mp4 --output-dir data/cctv_output --conf-threshold 0.35 --duration-threshold 5.0
```

---

## 🩹 Stage 4: Module 3 — Wound Image Classification (Research Protocol Only)

### 1. Safety Rules & Legal Guardrails
- **Research/Educational Prototype Only**: Strictly not a medical device, diagnostic tool, forensic pathology instrument, or triage aid.
- **Mandatory Consent / Provenance Gate**: Unconsented user uploads are rejected by policy (`verify_research_provenance`). Only documented, consented research datasets are accepted.
- **Permitted Visual Categories Only**:
  `abrasion`, `bruise/contusion`, `laceration`, `incision`, `puncture`, `burn`, `no visible wound`, `unknown / uncertain`.
- **Prohibited Inferences Enforced**:
  Zero gunshot determination, zero stab determination, zero wound age estimation, zero severity estimation, zero body-location inference, zero cause-of-injury inference, zero medical treatment recommendations, zero legal conclusions.
- **Patient/Subject-Level Disjoint Splitting**: Images are split by `patient_id` / `source_id`, preventing images from the same person from appearing across train/val/test splits.
- **Mandatory Warning Wording on Every Prediction**:
  `"Experimental visual-category prediction. This output is not a diagnosis and must not be used for medical, legal, or forensic decisions."`

### 2. CLI Execution Examples
```powershell
# 1. Train on consented research dataset manifest
python src/wound_research/run_wound.py train --manifest path/to/patient_manifest.json --output-dir data/checkpoints/wound_research --arch resnet18 --epochs 10

# 2. Evaluate on untouched patient-level test split
python src/wound_research/run_wound.py evaluate --checkpoint data/checkpoints/wound_research/wound_resnet18_best.pt --manifest path/to/patient_manifest.json --output-report data/wound_eval.json

# 3. Predict on research image with verified consent metadata
python src/wound_research/run_wound.py predict --checkpoint data/checkpoints/wound_research/wound_resnet18_best.pt --image path/to/research_image.png --research-metadata path/to/consent.json
```

---

## 🔬 Stage 5: Module 4 — Bullet & Toolmark Visual Similarity Retrieval

### 1. Safety & Legal Guardrails
- **Research-Only Similarity Retrieval**: Not a firearm identification or ballistics tool.
- **Strictly Prohibited Claims**:
  Zero firearm attribution, zero bullet caliber determination, zero firearm manufacturer identification, zero rifling pattern assertion, zero common-source determination, zero criminal linkage.
- **Controlled Lab Input Only**: Operates strictly on laboratory images (e.g., NIST NBTRD) with documented provenance.
- **Working-Copy Standardization**: Standardizes lighting, square center cropping, and scale on working copies only; original files remain intact and read-only.
- **Top-K Similarity Retrieval**: Returns nearest visual references with cosine similarity scores, L2 distance, reference hashes, and dataset IDs.
- **Safe Fallback**: Reports `"insufficient reference data"` when no candidates meet the reliability threshold (`0.45`).
- **Mandatory Non-Attribution Warning**:
  `"Experimental visual similarity retrieval. Similarity does not establish common source, firearm attribution, caliber, manufacturer, or legal conclusion."`

### 2. CLI Execution Examples
```powershell
# 1. Build laboratory reference index
python src/toolmark_research/run_toolmark.py index --manifest path/to/lab_reference_manifest.json --output-dir data/indices/toolmark

# 2. Query index for Top-K visually similar reference items
python src/toolmark_research/run_toolmark.py retrieve --index-dir data/indices/toolmark --query-image path/to/sample.png --top-k 5

# 3. Evaluate retrieval Recall@K and mAP against ground-truth lab benchmark
python src/toolmark_research/run_toolmark.py evaluate --index-dir data/indices/toolmark --test-manifest path/to/test_queries.json --output-report data/toolmark_eval.json
```

---

## 🌐 Stage 6: Final Integration — Streamlit, FastAPI, Docker & Factual Reports

### 1. Components
- [`src/api/main.py`](file:///src/api/main.py): High-throughput FastAPI backend implementing:
  - `GET /health`: Health status and disclaimers.
  - `POST /api/v1/evidence/upload`: Evidence intake, SHA-256 calculation, read-only vaulting, and working-copy generation.
  - `POST /api/v1/cctv/process`: CCTV surveillance processing.
  - `GET /api/v1/evidence/{id}/audit-trail`: Chronological audit query from SQLite WAL.
  - `POST /api/v1/reports/generate`: Generates verifiable factual technical PDF report.
- [`src/app/streamlit_app.py`](file:///src/app/streamlit_app.py): Unified 6-tab Streamlit investigator workstation:
  1. **Evidence Locker**: File validation, SHA-256 cryptographic fingerprint, read-only status.
  2. **Tampering Detection**: Pre-inference quality gate, calibrated probabilities, Grad-CAM attention overlay.
  3. **CCTV Surveillance**: Video enhancement filters, YOLO COCO detection, tracking, objective events, video player.
  4. **Wound Research**: Research consent protocol verification, visual category probabilities, medical disclaimer.
  5. **Toolmark Retrieval**: Lab reference index search, Top-K nearest visual matches, non-attribution notices.
  6. **Audit & Report**: SQLite WAL audit inspector and verifiable PDF report generator & downloader.
- [`src/common/report_generator.py`](file:///src/common/report_generator.py): ReportLab technical PDF generator strictly using empirical findings. Missing modules are stamped `Module not run.` No placeholders or invented conclusions.
- [`Dockerfile.forensics`](file:///Dockerfile.forensics): Multi-service production Docker container running FastAPI on port 8000 and Streamlit on port 8501.

### 2. Execution Commands

#### Run FastAPI Backend (Port 8000)
```powershell
# Windows PowerShell
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload

# Linux / Google Colab
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```
Interactive Swagger API docs available at: `http://127.0.0.1:8000/docs`

#### Run Streamlit Workstation (Port 8501)
```powershell
# Windows PowerShell
streamlit run src/app/streamlit_app.py --server.port 8501

# Linux / Google Colab
streamlit run src/app/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
```

#### Run Comprehensive Test Suite
```powershell
python -m pytest tests/test_hashing.py tests/test_file_validation.py tests/test_audit_db.py tests/test_quality_gate.py tests/test_utils.py tests/test_cctv.py tests/test_wound.py tests/test_toolmark.py tests/test_api_and_reports.py -v
```





