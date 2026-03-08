#!/usr/bin/env python3
"""Public deployment artifact entrypoint for V5.1 team orchestrator."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from core_feishu_config_builder import main as core_main


def main() -> int:
    argv = sys.argv[1:]
    if "--mode" not in argv:
        argv = ["--mode", "plugin", *argv]
    return core_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
