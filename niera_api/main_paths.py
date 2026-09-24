"""Validated paths for local benchmark artifacts."""

import re
from pathlib import Path

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
RUN_ID_RE = re.compile(r"^[0-9]{8}_[0-9]{6}_[a-f0-9]{6}$")


def run_directory(run_id: str) -> Path:
    if not RUN_ID_RE.fullmatch(run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    path = RESULTS_DIR / run_id
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(RESULTS_DIR.resolve(strict=True))
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Run not found") from None
    if not resolved.is_dir() or not (resolved / "run.json").is_file():
        raise HTTPException(status_code=404, detail="Run not found")
    return resolved
