"""Make workspace packages importable without requiring editable installs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for package in ("shared", "platform", "domain"):
    sys.path.insert(0, str(ROOT / "packages" / package))
