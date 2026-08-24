import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("RISK_DISABLE_EMBEDDINGS", "1")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "")
