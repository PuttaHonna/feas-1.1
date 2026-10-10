# Deep Learning Forensic Investigator

A Streamlit starter dashboard inspired by the supplied architecture diagram. It includes:
- Dark navy dashboard and module navigation
- Forgery localization upload flow and visualization panel
- Face comparison upload flow
- Wound image classification upload flow
- Session results, SHA-256 image digest, and PDF/JSON report export
- A model adapter layer that explicitly separates demo placeholders from actual inference

## Important: demo vs real model

The app starts in **Demo mode**. It does not claim to detect actual forgery, verify identity, or classify wounds. The forgery overlay is a visual placeholder only. Face and wound demo outputs intentionally do not fabricate scores or labels.

Selecting **Real model adapters** will not create predictions by itself. Until your trained models and preprocessing/postprocessing are connected in `forensic_models.py`, the app returns “not configured” instead of inventing results.

## 1. Requirements

- Python 3.10 or newer
- pip
- Optional: your trained model weights and the relevant framework/runtime

## 2. Install and run

### Windows PowerShell

```powershell
cd deep_learning_forensic_investigator
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, you can use the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS / Linux

```bash
cd deep_learning_forensic_investigator
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will print a local URL, usually `http://localhost:8501`.

## 3. Project structure

```text
deep_learning_forensic_investigator/
├── app.py
├── forensic_models.py
├── requirements.txt
├── README.md
├── .env.example
└── .streamlit/
    └── config.toml
```

## 4. Connect actual trained models

Edit the adapter functions in `forensic_models.py`:

- `detect_forgery(image, real=True)`: preprocess image, run your trained detector/segmenter, map detections to image coordinates, and return a visualization plus structured results.
- `authenticate_faces(image_a, image_b, real=True)`: detect/align faces, obtain embeddings from a validated face model, calculate cosine similarity, and apply a threshold calibrated on your evaluation data.
- `classify_wound(image, real=True)`: apply the training-time resize/normalization, run the classifier, map logits to labels, and return calibrated probabilities.

Use the same preprocessing, label mapping, and model versions as training. Add model version, weight hash, threshold, and inference timestamp to report metadata. Do not set any `*_MODEL_READY` flag until the relevant adapter really runs end-to-end. In this starter, setting the flag does not enable inference; each adapter intentionally remains unconfigured until implementation is added.

## 5. Suggested integration notes

### Forgery localization (e.g., YOLOv8 or segmentation model)
Keep the model's actual output boxes/masks and confidence values. Do not treat ordinary object detections as proof of tampering. Evaluate on an appropriate tampering dataset and report false-positive limitations.

### Face authentication
Face comparison is probabilistic and sensitive to image quality, pose, lighting, and demographic performance differences. Calibrate thresholds on a suitable validation set; a similarity score is not absolute identity proof. Only process images with appropriate authorization.

### Wound classification
Use an appropriate, consented dataset and expert-reviewed labels. Do not infer wound age, severity, intent, or cause unless the model has been specifically trained and validated for that target. The dashboard is not a substitute for clinical assessment.

## 6. Evidence handling and report caveats

- Preserve original evidence separately and read-only when possible.
- Record provenance, acquisition time, source, operator, hashes, model/version details, and every transformation.
- The current SHA-256 is calculated from a normalized PNG encoding of the uploaded image, not necessarily the exact original file bytes. For evidentiary use, hash the original uploaded byte stream before decoding.
- PDF report entries are generated from the current Streamlit session only; this is not persistent case management.
- Demo output must not be presented as a forensic finding.

## 7. Troubleshooting

- If installation fails, confirm Python 3.10+ and retry in a fresh virtual environment.
- If Streamlit is not found, activate the virtual environment and run `python -m streamlit run app.py`.
- If PDF export fails, confirm `reportlab` installed successfully with `pip show reportlab`.

---

## 8. CCTV Video Analysis Module

### Feature Overview
The CCTV Video Analysis module provides an objective, automated pipeline for video triage, deterministic enhancement, object detection, multi-object tracking, and spatio-temporal event extraction. All processing operates strictly on a derived working copy while preserving original evidence unaltered in immutable storage.

### Supported Files
- Formats: `.mp4`, `.avi`, `.mkv`, `.mov`
- Maximum file size: 500 MB (configurable)
- Frame integrity: Verified via OpenCV stream decoding

### Workflow
1. **Intake & Preservation**: Uploaded file is stored untouched in `evidence_store/originals/`.
2. **Cryptographic Integrity**: SHA-256 hash is computed on original bytes and recorded in an SQLite audit database.
3. **Derived Working Copy**: A byte-for-byte duplicate is created in `evidence_store/working_copies/` and verified against the original hash.
4. **Frame Extraction**: Decodes working frames under Fast Review (1 FPS) or Full Analysis (configurable frame step) with millisecond timestamps (`frame_index / FPS`).
5. **Deterministic Enhancement**: Applies conventional, reproducible OpenCV algorithms (`basic`, `low_light`, or `none`) including CLAHE, gamma correction, and mild edge sharpening.
6. **YOLO Detection & Tracking**: Runs cached YOLOv8 restricted to 10 COCO classes (`person`, `car`, `motorcycle`, `bicycle`, `bus`, `truck`, `backpack`, `handbag`, `suitcase`, `cell phone`). ByteTrack assigns readable IDs (e.g., `person_01`, `car_01`).
7. **Event Extraction**: Extracts objective, non-judgmental spatio-temporal events (camera view enter/exit, prolonged presence, ROI zone transitions, person/vehicle co-presence).
8. **Export & Visualization**: Generates annotated video, CSV logs (`detections.csv`, `tracks.csv`), JSON events, and keyframe galleries.

### Outputs
```
evidence_store/
├── originals/
└── working_copies/

results/cctv/
├── metadata/
│   └── video_metadata.json
├── enhanced_frames/
├── keyframes/
│   ├── overview/
│   ├── entries/
│   ├── exits/
│   └── best_detections/
├── annotated_videos/
│   └── {evidence_id}_annotated.mp4
├── detection_logs/
│   ├── detections.csv
│   ├── tracks.csv
│   ├── events.json
│   └── audit_log.json
└── reports/
    └── {evidence_id}_cctv_summary.json
```

### Setup & Run Commands

#### Windows PowerShell:
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements
python -m pip install -r requirements.txt

# Run the Streamlit application
streamlit run app.py
```

#### Google Colab / Linux:
```bash
# Install dependencies
pip install -r requirements.txt

# Run Streamlit with public tunnel (e.g., localtunnel)
streamlit run app.py & npx localtunnel --port 8501
```

### Privacy & Limitations
- **No Biometric Identification**: Does not perform facial recognition, re-identification, or identity matching.
- **No Crime or Intent Prediction**: Does not predict suspicious behavior, theft, violence, weapons, or legal culpability.
- **Advisory Prototype**: Results are algorithmic estimates intended solely for research and human investigative review.
- **Immutable Evidence**: Original footage is never overwritten or altered.

### Disclaimer
*This is an experimental computer-vision analysis. Detections and tracking results are automated estimates and require human review. The application does not identify people or establish legal conclusions.*

