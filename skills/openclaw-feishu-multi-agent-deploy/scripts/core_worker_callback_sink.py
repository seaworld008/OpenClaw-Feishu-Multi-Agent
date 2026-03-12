#!/usr/bin/env python3
"""Structured worker callback sink for the redesigned V5.1 control plane."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import core_job_registry as registry
from core_runtime_store import RuntimeStore
from core_team_controller import TeamController


@dataclass(frozen=True)
class StructuredWorkerCallback:
    job_ref: str
    team_key: str
    stage_index: int
    agent_id: str
    progress_draft: str
    final_draft: str
    summary: str
    details: str
    risks: str
    action_items: str
    progress_message_id: str = ""
    final_message_id: str = ""
    final_visible_text: str = ""


def _placeholder_message_id(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return False
    if normalized in {"pending", "sent", "placeholder", "placeholder_progress_id", "placeholder_final_id"}:
        return True
    if "pending" in normalized or "placeholder" in normalized:
        return True
    if normalized.startswith("<") and normalized.endswith(">"):
        return True
    return False


def _require_text(name: str, value: str, *, allow_empty: bool = False) -> str:
    normalized = str(value or "").strip()
    if not allow_empty and not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def validate_callback_payload(callback: StructuredWorkerCallback) -> StructuredWorkerCallback:
    stage_index = int(callback.stage_index)
    if stage_index < 0:
        raise ValueError("stage_index must be >= 0")
    progress_draft = _require_text("progress_draft", callback.progress_draft, allow_empty=True)
    raw_final_text = str(callback.final_draft or "").strip()
    raw_final_visible_text = str(callback.final_visible_text or "").strip()
    raw_final_message_id = str(callback.final_message_id or "").strip()
    final_required = bool(raw_final_text or raw_final_visible_text or raw_final_message_id)
    if final_required:
        final_draft = _require_text("final_draft", callback.final_draft)
        summary = _require_text("summary", callback.summary)
        details = _require_text("details", callback.details)
        risks = _require_text("risks", callback.risks)
        action_items = _require_text("action_items", callback.action_items)
    else:
        final_draft = ""
        summary = _require_text("summary", callback.summary, allow_empty=True)
        details = _require_text("details", callback.details, allow_empty=True)
        risks = _require_text("risks", callback.risks, allow_empty=True)
        action_items = _require_text("action_items", callback.action_items, allow_empty=True)
        if not progress_draft:
            raise ValueError("progress_draft is required when final_draft is omitted")
    normalized = StructuredWorkerCallback(
        job_ref=_require_text("job_ref", callback.job_ref),
        team_key=_require_text("team_key", callback.team_key),
        stage_index=stage_index,
        agent_id=_require_text("agent_id", callback.agent_id),
        progress_draft=progress_draft,
        final_draft=final_draft,
        summary=summary,
        details=details,
        risks=risks,
        action_items=action_items,
        progress_message_id=_require_text("progress_message_id", callback.progress_message_id, allow_empty=True),
        final_message_id=_require_text("final_message_id", callback.final_message_id, allow_empty=True),
        final_visible_text=_require_text("final_visible_text", callback.final_visible_text or final_draft, allow_empty=not final_required),
    )
    if normalized.progress_message_id and _placeholder_message_id(normalized.progress_message_id):
        raise ValueError("progress_message_id must be a real delivery message id")
    if normalized.final_message_id and _placeholder_message_id(normalized.final_message_id):
        raise ValueError("final_message_id must be a real delivery message id")
    return normalized


def callback_payload_dict(callback: StructuredWorkerCallback) -> dict[str, Any]:
    return {
        "jobRef": callback.job_ref,
        "teamKey": callback.team_key,
        "stageIndex": callback.stage_index,
        "agentId": callback.agent_id,
        "progressDraft": callback.progress_draft,
        "finalDraft": callback.final_draft,
        "progressMessageId": callback.progress_message_id,
        "finalMessageId": callback.final_message_id,
        "finalVisibleText": callback.final_visible_text,
        "summary": callback.summary,
        "details": callback.details,
        "risks": callback.risks,
        "actionItems": callback.action_items,
    }


def _row_team_key(row: sqlite3.Row) -> str:
    if "team_key" in row.keys():
        value = str(row["team_key"] or "").strip()
        if value:
            return value
    return str(row["group_peer_id"] or "").strip()


def _payload_matches(existing: dict[str, Any], callback: StructuredWorkerCallback) -> bool:
    payload = existing.get("payload")
    if not isinstance(payload, dict):
        return False
    candidate = callback_payload_dict(callback)
    for key, value in payload.items():
        if candidate.get(key) != value:
            return False
    return True


def ingest_callback(
    *,
    store: RuntimeStore,
    callback: StructuredWorkerCallback,
    subagent_sessions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized = validate_callback_payload(callback)
    if subagent_sessions:
        raise ValueError("worker callback rejected because job-scoped subagent sessions still exist")

    conn = store.connection
    registry.init_db(conn)
    row = registry.get_job(conn, normalized.job_ref)
    if row is None:
        raise RuntimeError(f"job missing: {normalized.job_ref}")
    if _row_team_key(row) != normalized.team_key:
        raise ValueError("callback team_key does not match job team_key")

    is_progress_only = not bool(str(normalized.final_draft or "").strip())

    if is_progress_only:
        controller = TeamController(store=store)
        result = controller.record_progress_update(
            job_ref=normalized.job_ref,
            agent_id=normalized.agent_id,
            progress_text=normalized.progress_draft,
            progress_message_id=normalized.progress_message_id,
        )
        return {
            "status": result["status"],
            "jobRef": normalized.job_ref,
            "teamKey": normalized.team_key,
            "stageIndex": normalized.stage_index,
            "agentId": normalized.agent_id,
            "nextAction": result["nextAction"],
            "waitingForAgentId": result["waitingForAgentId"],
        }

    existing = store.get_stage_callback(
        job_ref=normalized.job_ref,
        stage_index=normalized.stage_index,
        agent_id=normalized.agent_id,
    )
    if existing is not None:
        if _payload_matches(existing, normalized):
            return {
                "status": "duplicate",
                "jobRef": normalized.job_ref,
                "teamKey": normalized.team_key,
                "stageIndex": normalized.stage_index,
                "agentId": normalized.agent_id,
            }
        raise RuntimeError("callback already claimed for this stage")
    current_stage_index = int(row["current_stage_index"] or 0) if "current_stage_index" in row.keys() else 0
    if normalized.stage_index != current_stage_index:
        raise ValueError(
            f"callback stage_index mismatch: expected={current_stage_index}, actual={normalized.stage_index}"
        )

    controller = TeamController(store=store)
    result = controller.accept_worker_callback(
        job_ref=normalized.job_ref,
        agent_id=normalized.agent_id,
        progress_text=normalized.progress_draft,
        final_text=normalized.final_draft,
        summary=normalized.summary,
        details=normalized.details,
        risks=normalized.risks,
        action_items=normalized.action_items,
        progress_message_id=normalized.progress_message_id,
        final_message_id=normalized.final_message_id,
        final_visible_text=normalized.final_visible_text,
    )
    return {
        "status": "accepted",
        "jobRef": normalized.job_ref,
        "teamKey": normalized.team_key,
        "stageIndex": normalized.stage_index,
        "agentId": normalized.agent_id,
        "nextAction": result["nextAction"],
        "waitingForAgentId": result["waitingForAgentId"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Structured worker callback sink.")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest")
    ingest.add_argument("--db", required=True)
    ingest.add_argument("--job-ref", required=True)
    ingest.add_argument("--team-key", required=True)
    ingest.add_argument("--stage-index", type=int, required=True)
    ingest.add_argument("--agent-id", required=True)
    ingest.add_argument("--payload", default="")
    ingest.add_argument("--progress-text", default="")
    ingest.add_argument("--final-text", default="")
    ingest.add_argument("--summary", default="")
    ingest.add_argument("--details", default="")
    ingest.add_argument("--risks", default="")
    ingest.add_argument("--action-items", default="")
    ingest.add_argument("--progress-message-id", default="")
    ingest.add_argument("--final-message-id", default="")
    ingest.add_argument("--final-visible-text", default="")
    ingest.add_argument("--subagent-sessions-json", default="[]")
    return parser


def _parse_payload_argument(raw_payload: str) -> dict[str, Any]:
    text = str(raw_payload or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid --payload: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("invalid --payload: expected JSON object")
    return payload


def _normalize_payload_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _payload_get(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if key in payload and payload[key] is not None:
            return _normalize_payload_value(payload[key])
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "ingest":
        raise RuntimeError(f"unsupported command: {args.command}")
    try:
        subagent_sessions = json.loads(args.subagent_sessions_json)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid --subagent-sessions-json: {exc}") from exc
    payload = _parse_payload_argument(args.payload)

    store = RuntimeStore(args.db)
    try:
        store.initialize()
        result = ingest_callback(
            store=store,
            callback=StructuredWorkerCallback(
                job_ref=args.job_ref,
                team_key=args.team_key,
                stage_index=args.stage_index,
                agent_id=args.agent_id,
                progress_draft=_payload_get(payload, "progressDraft", "progressText", "progress_draft", "progress_text") or args.progress_text,
                final_draft=_payload_get(payload, "finalDraft", "finalText", "final_draft", "final_text") or args.final_text,
                summary=_payload_get(payload, "summary") or args.summary,
                details=_payload_get(payload, "details") or args.details,
                risks=_payload_get(payload, "risks") or args.risks,
                action_items=_payload_get(payload, "actionItems", "action_items") or args.action_items,
                progress_message_id=_payload_get(payload, "progressMessageId", "progress_message_id")
                or args.progress_message_id,
                final_message_id=_payload_get(payload, "finalMessageId", "final_message_id")
                or args.final_message_id,
                final_visible_text=_payload_get(payload, "finalVisibleText", "final_visible_text")
                or args.final_visible_text,
            ),
            subagent_sessions=subagent_sessions if isinstance(subagent_sessions, list) else [],
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
