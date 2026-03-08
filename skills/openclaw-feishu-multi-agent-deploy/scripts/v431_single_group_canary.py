#!/usr/bin/env python3
"""Public canary entrypoint for V4.3.1 single-group production."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from core_canary_engine import main_sqlite_canary


if __name__ == "__main__":
    raise SystemExit(main_sqlite_canary())
