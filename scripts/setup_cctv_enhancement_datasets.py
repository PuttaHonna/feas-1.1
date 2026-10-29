"""
Launcher wrapper for CCTV Forensic Enhancement Dataset Setup & Verification.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEAS_SETUP = ROOT / "FEAS" / "scripts" / "setup_cctv_enhancement_datasets.py"

if __name__ == "__main__":
    import runpy
    sys.path.insert(0, str(ROOT / "FEAS"))
    runpy.run_path(str(FEAS_SETUP), run_name="__main__")
