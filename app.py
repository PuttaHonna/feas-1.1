"""
FEAS 2.0 - Hugging Face Spaces Entry Point
Mounts the production FastAPI Forensic Engine inside Gradio for 16GB RAM cloud execution.
"""

import os
import sys
from pathlib import Path

# Add FEAS directory to sys.path so all src.* modules resolve cleanly
ROOT_DIR = Path(__file__).resolve().parent
FEAS_DIR = ROOT_DIR / "FEAS"
if str(FEAS_DIR) not in sys.path:
    sys.path.insert(0, str(FEAS_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure required runtime forensic directories exist
for p in [
    FEAS_DIR / "storage",
    FEAS_DIR / "reports",
    FEAS_DIR / "temp",
    FEAS_DIR / "results" / "cctv" / "originals",
    FEAS_DIR / "results" / "cctv" / "annotated_videos",
    FEAS_DIR / "results" / "cctv" / "keyframes",
    FEAS_DIR / "results" / "cctv" / "evidence_store",
    ROOT_DIR / "data" / "evidence_vault",
    ROOT_DIR / "data" / "working_copies",
]:
    p.mkdir(parents=True, exist_ok=True)

from src.main import app as fastapi_app

try:
    import gradio as gr

    with gr.Blocks(title="FEAS 2.0 Forensics Surveillance Engine") as demo:
        gr.Markdown(
            """
            # 🛡️ FEAS 2.0 - Forensic Evidence Analysis System
            ### High-Performance Deep Learning Surveillance & Forensic Processing Engine (16 GB RAM Cluster)
            
            * **Status**: 🟢 Online & Operational
            * **Backend Node**: Hugging Face Spaces (2 vCPU · 16 GB RAM)
            * **API Documentation**: [Swagger UI (/docs)](/docs) | [ReDoc (/redoc)](/redoc)
            * **System Telemetry**: [/health](/health) | [/api/v1/health](/api/v1/health)
            * **Live Frontend**: [https://feas-forensics.web.app](https://feas-forensics.web.app)
            ---
            *Connected to FEAS Surveillance Suite. Processing YOLOv8 object detection, ByteTrack tracking, and CCTVEnhanceNet super-resolution.*
            """
        )

    # Mount Gradio dashboard at root while preserving all FastAPI routes
    app = gr.mount_gradio_app(fastapi_app, demo, path="/")
except Exception:
    app = fastapi_app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)

