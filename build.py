"""Build the React frontend, then copy it to public/ for the Vercel CDN."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
PUBLIC = ROOT / "public"


def main() -> None:
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    subprocess.check_call([npm, "install"], cwd=FRONTEND)
    subprocess.check_call([npm, "run", "build"], cwd=FRONTEND)
    dist = FRONTEND / "dist"
    if not dist.is_dir():
        raise SystemExit("frontend/dist was not created")
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    shutil.copytree(dist, PUBLIC)


if __name__ == "__main__":
    main()
