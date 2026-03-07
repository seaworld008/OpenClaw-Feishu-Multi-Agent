#!/usr/bin/env python3
"""Validate V4.3/V4.3.1 single-group production runs using SQLite state and session logs."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


REQUIRED_AGENTS = ("ops_agent", "finance_agent")
LEAK_TOKENS = ("ACK_READY", "REPLY_SKIP", "COMPLETE_PACKET", "WORKFLOW_INCOMPLETE")


def emit(text: str) -> None:
    print(text)


def load_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def session_contains(root: Path, agent_id: str, token: str) -> bool:
    session_dir = root / agent_id / "sessions"
    if not session_dir.exists():
        return False
    for path in session_dir.glob("*.jsonl"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if token in text:
            return True
    return False


def find_protocol_leaks(root: Path, job_ref: str) -> list[str]:
    leaks: list[str] = []
    for agent_id in ("supervisor_agent", *REQUIRED_AGENTS):
        session_dir = root / agent_id / "sessions"
        if not session_dir.exists():
            continue
        for path in session_dir.glob("*.jsonl"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if job_ref not in text:
                continue
            for line in text.splitlines():
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = payload.get("message", {})
                if message.get("role") != "assistant":
                    continue
                for item in message.get("content", []):
                    if item.get("type") != "text":
                        continue
                    value = item.get("text", "")
                    if value == "NO_REPLY":
                        continue
                    if any(token in value for token in LEAK_TOKENS):
                        leaks.append(f"{agent_id}:{path.name}:{value}")
    return leaks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--job-ref", required=True)
    parser.add_argument("--session-root")
    parser.add_argument("--require-visible-messages", action="store_true")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        emit(f"DB_MISSING: {db_path}")
        return 2

    conn = load_db(db_path)
    job = conn.execute(
        "SELECT job_ref, status, title, group_peer_id, updated_at, closed_at FROM jobs WHERE job_ref = ?",
        (args.job_ref,),
    ).fetchone()
    if not job:
        emit(f"JOB_NOT_FOUND: {args.job_ref}")
        return 2

    participants = {
        row["agent_id"]: row
        for row in conn.execute(
            """
            SELECT job_ref, agent_id, status, progress_message_id, final_message_id, summary, completed_at
            FROM job_participants
            WHERE job_ref = ?
            """,
            (args.job_ref,),
        ).fetchall()
    }

    missing_agents = [agent for agent in REQUIRED_AGENTS if agent not in participants]
    if missing_agents:
        emit(f"PARTICIPANTS_MISSING: {','.join(missing_agents)}")
        return 2

    incomplete = []
    for agent_id in REQUIRED_AGENTS:
        row = participants[agent_id]
        if row["status"] != "done":
            incomplete.append(f"{agent_id}:status={row['status']}")
        if not row["progress_message_id"]:
            incomplete.append(f"{agent_id}:progress_message_id")
        if not row["final_message_id"]:
            incomplete.append(f"{agent_id}:final_message_id")
    if incomplete:
        emit("PARTICIPANTS_INCOMPLETE: " + ", ".join(incomplete))
        return 2

    if job["status"] != "done":
        emit(f"ROLLUP_PENDING: job={args.job_ref} status={job['status']}")
        return 3

    if args.require_visible_messages:
        if not args.session_root:
            emit("VISIBLE_MESSAGE_CHECK_REQUIRES_SESSION_ROOT")
            return 2
        root = Path(args.session_root)
        missing_visibility = []
        for agent_id in REQUIRED_AGENTS:
            row = participants[agent_id]
            if not session_contains(root, agent_id, row["progress_message_id"]):
                missing_visibility.append(f"{agent_id}:progress")
            if not session_contains(root, agent_id, row["final_message_id"]):
                missing_visibility.append(f"{agent_id}:final")
        if missing_visibility:
            emit("VISIBLE_MESSAGE_MISSING: " + ", ".join(missing_visibility))
            return 3
        leaks = find_protocol_leaks(root, args.job_ref)
        if leaks:
            emit("VISIBLE_PROTOCOL_LEAK: " + " | ".join(leaks[:5]))
            return 3

    emit(
        "V4_3_CANARY_OK: "
        f"jobRef={job['job_ref']} title={job['title']} status={job['status']} "
        f"ops_progress={participants['ops_agent']['progress_message_id']} "
        f"ops_final={participants['ops_agent']['final_message_id']} "
        f"finance_progress={participants['finance_agent']['progress_message_id']} "
        f"finance_final={participants['finance_agent']['final_message_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
