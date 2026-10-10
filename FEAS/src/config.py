"""
Forensic Evidence Analysis System (FEAS) - Global Configuration
Enforces deterministic behavior, device selection, and system constants.
"""

import os
import random
from pathlib import Path
import numpy as np
import torch

# Deterministic Seed Configuration
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

# Device configuration
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Paths configuration
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
REPORTS_DIR = BASE_DIR / "reports"
TEMP_DIR = BASE_DIR / "temp"
DATA_DIR = BASE_DIR / "data"
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"
DB_PATH = DATA_DIR / "feas_audit.db"

# Create directories if they do not exist
for path in [STORAGE_DIR, REPORTS_DIR, TEMP_DIR, DATA_DIR, FIXTURES_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Ingestion constraints
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".mp4", ".mkv", ".avi", ".wav", ".mp3"}
MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
VIDEO_KEYFRAME_FPS = 1  # 1 frame per second

# Inference & Orchestrator constraints
EXECUTION_TIMEOUT_SECONDS = 12.0
ELA_QUALITY = 95
ELA_SCALE = 10.0
SUPER_RESOLUTION_TARGET_SIZE = (1024, 1024)
EMBEDDING_DIM = 512
COSINE_SIMILARITY_THRESHOLD = 0.60

# Model configurations
WOUND_CLASSES = {
    "type": ["gunshot", "stab", "blunt", "burn"],
    "severity": ["minor", "moderate", "severe"],
    "age": ["fresh", "1-day", "week old"],
    "location": ["head", "torso", "limb"]
}

BALLISTICS_CLASSES = {
    "caliber": [".45ACP", "9mm", "5.56mm"],
    "rifling": ["6R", "5L", "Polygonal"],
    "manufacturer": ["Glock", "Beretta", "Colt", "Smith & Wesson", "SIG Sauer", "Unknown"]
}
