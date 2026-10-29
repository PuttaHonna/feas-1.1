"""
Launcher wrapper for CCTV Deep Enhancement Models Training Suite.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEAS_TRAIN = ROOT / "FEAS" / "scripts" / "train_cctv_enhancer.py"

if __name__ == "__main__":
    import runpy
    sys.path.insert(0, str(ROOT / "FEAS"))
    runpy.run_path(str(FEAS_TRAIN), run_name="__main__")
