import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_BACKEND_ROOT = Path(__file__).resolve().parents[1]

for path in (APP_BACKEND_ROOT, REPO_ROOT):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)
