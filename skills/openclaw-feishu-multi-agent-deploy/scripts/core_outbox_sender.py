#!/usr/bin/env python3
"""Outbox sender for visible control-plane messages."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from core_runtime_store import RuntimeStore


def message_dedup_key(
    *,
    team_key: str,
    job_ref: str,
    message_kind: str,
    stage_index: int = -1,
    agent_id: str = "",
) -> str:
    return f"{team_key}:{job_ref}:{message_kind}:{stage_index}:{agent_id}"


def _require_message_contains_job_ref(job_ref: str, message_kind: str, payload: dict[str, Any]) -> None:
    message = str(payload.get("message") or "").strip()
    if not message:
        raise ValueError(f"{message_kind} payload requires non-empty message")
    if job_ref not in message:
        raise ValueError(f"{message_kind} visible message must include job_ref")


def enqueue_visible_message(
    store: RuntimeStore,
    *,
    team_key: str,
    job_ref: str,
    message_kind: str,
    payload: dict[str, Any],
    stage_index: int = -1,
    agent_id: str = "",
) -> dict[str, Any]:
    if not str(team_key or "").strip():
        raise ValueError("team_key is required")
    if not str(job_ref or "").strip():
        raise ValueError("job_ref is required")
    if not str(message_kind or "").strip():
        raise ValueError("message_kind is required")
    delivery = payload.get("delivery")
    if not isinstance(delivery, dict):
        raise ValueError("visible payload requires delivery")
    for field in ("channel", "accountId", "target"):
        if not str(delivery.get(field) or "").strip():
            raise ValueError(f"visible payload delivery requires {field}")
    _require_message_contains_job_ref(job_ref, message_kind, payload)
    return store.enqueue_outbound_message(
        team_key=team_key,
        job_ref=job_ref,
        message_kind=message_kind,
        payload=payload,
        stage_index=stage_index,
        agent_id=agent_id,
    )


def mark_message_sent(
    store: RuntimeStore,
    *,
    team_key: str,
    job_ref: str,
    message_kind: str,
    stage_index: int = -1,
    agent_id: str = "",
    delivery_message_id: str,
) -> dict[str, Any]:
    if not str(delivery_message_id or "").strip():
        raise ValueError("delivery_message_id is required")
    return store.mark_outbound_message_sent(
        team_key=team_key,
        job_ref=job_ref,
        message_kind=message_kind,
        stage_index=stage_index,
        agent_id=agent_id,
        delivery_message_id=delivery_message_id,
    )


def _extract_message_id(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("messageId", "message_id", "id"):
            candidate = str(value.get(key) or "").strip()
            if candidate:
                return candidate
        for nested_key in ("result", "payload", "data"):
            nested = value.get(nested_key)
            candidate = _extract_message_id(nested)
            if candidate:
                return candidate
    if isinstance(value, list):
        for item in value:
            candidate = _extract_message_id(item)
            if candidate:
                return candidate
    return ""


def _coerce_delivery_message_id(result: Any) -> str:
    return _extract_message_id(result)


def deliver_pending_messages(
    store: RuntimeStore,
    *,
    delivery_func: Callable[[dict[str, Any]], Any],
    team_key: str | None = None,
    limit: int | None = None,
    on_delivered: Callable[[dict[str, Any], str], None] | None = None,
) -> dict[str, Any]:
    messages = store.list_pending_outbound_messages(team_key=team_key, limit=limit)
    results: list[dict[str, Any]] = []
    delivered = 0
    for row in messages:
        delivery_message_id = _coerce_delivery_message_id(delivery_func(row))
        if not delivery_message_id:
            raise RuntimeError(
                f"delivery_func did not return message id for {message_dedup_key(team_key=row['teamKey'], job_ref=row['jobRef'], message_kind=row['messageKind'], stage_index=row['stageIndex'], agent_id=row['agentId'])}"
            )
        sent_row = mark_message_sent(
            store,
            team_key=row["teamKey"],
            job_ref=row["jobRef"],
            message_kind=row["messageKind"],
            stage_index=row["stageIndex"],
            agent_id=row["agentId"],
            delivery_message_id=delivery_message_id,
        )
        if on_delivered is not None:
            on_delivered(sent_row, delivery_message_id)
        delivered += 1
        results.append(
            {
                "jobRef": row["jobRef"],
                "teamKey": row["teamKey"],
                "messageKind": row["messageKind"],
                "stageIndex": row["stageIndex"],
                "agentId": row["agentId"],
                "deliveryMessageId": delivery_message_id,
            }
        )
    return {"deliveredCount": delivered, "results": results}


def _openclaw_delivery_callable(openclaw_bin: Path) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def _deliver(row: dict[str, Any]) -> dict[str, Any]:
        payload = row["payload"]
        delivery = payload["delivery"]
        proc = subprocess.run(
            [
                str(openclaw_bin),
                "message",
                "send",
                "--channel",
                str(delivery["channel"]),
                "--account",
                str(delivery["accountId"]),
                "--target",
                str(delivery["target"]),
                "--message",
                str(payload["message"]),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        stdout = proc.stdout.strip()
        return json.loads(stdout) if stdout else {}

    return _deliver


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deliver pending visible messages from outbox.")
    sub = parser.add_subparsers(dest="command", required=True)

    deliver = sub.add_parser("deliver-pending")
    deliver.add_argument("--db", required=True)
    deliver.add_argument("--openclaw-bin", required=True)
    deliver.add_argument("--team-key", default="")
    deliver.add_argument("--limit", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "deliver-pending":
        raise RuntimeError(f"unsupported command: {args.command}")
    store = RuntimeStore(args.db)
    try:
        store.initialize()
        result = deliver_pending_messages(
            store,
            delivery_func=_openclaw_delivery_callable(Path(args.openclaw_bin)),
            team_key=str(args.team_key or "").strip() or None,
            limit=args.limit,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
