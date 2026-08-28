"""Build the React frontend before Vercel packages the FastAPI app."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"


def main() -> None:
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    subprocess.check_call([npm, "install"], cwd=FRONTEND)
    subprocess.check_call([npm, "run", "build"], cwd=FRONTEND)


if __name__ == "__main__":
    main()
