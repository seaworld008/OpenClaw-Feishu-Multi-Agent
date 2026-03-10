#!/usr/bin/env python3
"""Public runtime entrypoint for V5.1 team orchestrator production."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from core_job_registry import main as registry_main
from core_outbox_sender import main as outbox_main
from core_worker_callback_sink import main as callback_sink_main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "deliver-outbox":
        return outbox_main(["deliver-pending", *args[1:]])
    if args and args[0] == "ingest-callback":
        return callback_sink_main(["ingest", *args[1:]])
    return registry_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
