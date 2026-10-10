"""
Root Pytest Configuration and Path Resolver for FEAS.
Ensures that 'src' is always discoverable across all test runners and IDE environments.
"""

import sys
from pathlib import Path

# Insert project root into sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
