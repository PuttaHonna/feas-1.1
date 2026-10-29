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

# Device configuration (Cross-platform: CUDA for NVIDIA, MPS for Apple Silicon, CPU fallback)
if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
else:
    DEVICE = torch.device("cpu")

# Paths configuration
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
REPORTS_DIR = BASE_DIR / "reports"
TEMP_DIR = BASE_DIR / "temp"
DATA_DIR = BASE_DIR / "data"
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"
RESULTS_DIR = BASE_DIR / "results"
DB_PATH = DATA_DIR / "feas_audit.db"

# Create directories if they do not exist
for path in [STORAGE_DIR, REPORTS_DIR, TEMP_DIR, DATA_DIR, FIXTURES_DIR, RESULTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Firebase Configuration
FIREBASE_CREDENTIALS_PATH = Path(os.environ.get("FIREBASE_CREDENTIALS", str(BASE_DIR / "firebase-service-account.json")))
FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET", "")
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "")
FIREBASE_USE_EMULATOR = os.environ.get("FIREBASE_USE_EMULATOR", "").lower() in ("1", "true", "yes")
FIREBASE_AUTH_EMULATOR_HOST = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST", "")
FIRESTORE_EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "")
STORAGE_EMULATOR_HOST = os.environ.get("STORAGE_EMULATOR_HOST", "")


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
