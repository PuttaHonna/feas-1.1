"""
Launcher wrapper for CCTV Surveillance Person Detector Training Orchestrator.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEAS_TRAIN = ROOT / "FEAS" / "scripts" / "train_cctv_detector.py"

if __name__ == "__main__":
    import runpy
    sys.path.insert(0, str(ROOT / "FEAS"))
    runpy.run_path(str(FEAS_TRAIN), run_name="__main__")
