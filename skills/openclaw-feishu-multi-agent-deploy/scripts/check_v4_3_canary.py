#!/usr/bin/env python3
"""Validate V4.3/V4.3.1/V5 team production runs using SQLite state and session logs."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path


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


def normalize_agents(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def find_protocol_leaks(root: Path, job_ref: str, supervisor_agent: str, required_agents: list[str]) -> list[str]:
    leaks: list[str] = []
    for agent_id in (supervisor_agent, *required_agents):
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


def find_supervisor_rollup_message(root: Path, supervisor_agent: str, job_ref: str, group_peer_id: str) -> str | None:
    session_dir = root / supervisor_agent / "sessions"
    if not session_dir.exists():
        return None
    message_id_re = re.compile(r'messageId[=": ]+([A-Za-z0-9_\\-]+)')
    target_token = f"chat:{group_peer_id}"
    for path in session_dir.glob("*.jsonl"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if job_ref not in text or target_token not in text:
            continue
        match = message_id_re.search(text)
        if match:
            return match.group(1)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--job-ref", required=True)
    parser.add_argument("--session-root")
    parser.add_argument("--require-visible-messages", action="store_true")
    parser.add_argument("--worker-agents", default="ops_agent,finance_agent")
    parser.add_argument("--supervisor-agent", default="supervisor_agent")
    parser.add_argument("--team-key")
    parser.add_argument("--success-token", default="V4_3_CANARY_OK")
    parser.add_argument("--require-supervisor-target-chat", action="store_true")
    args = parser.parse_args()
    required_agents = normalize_agents(args.worker_agents)
    if not required_agents:
        emit("WORKER_AGENTS_EMPTY")
        return 2

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

    missing_agents = [agent for agent in required_agents if agent not in participants]
    if missing_agents:
        emit(f"PARTICIPANTS_MISSING: {','.join(missing_agents)}")
        return 2

    incomplete = []
    for agent_id in required_agents:
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
        for agent_id in required_agents:
            row = participants[agent_id]
            if not session_contains(root, agent_id, row["progress_message_id"]):
                missing_visibility.append(f"{agent_id}:progress")
            if not session_contains(root, agent_id, row["final_message_id"]):
                missing_visibility.append(f"{agent_id}:final")
        if missing_visibility:
            emit("VISIBLE_MESSAGE_MISSING: " + ", ".join(missing_visibility))
            return 3
        leaks = find_protocol_leaks(root, args.job_ref, args.supervisor_agent, required_agents)
        if leaks:
            emit("VISIBLE_PROTOCOL_LEAK: " + " | ".join(leaks[:5]))
            return 3
        supervisor_rollup_message_id = None
        if args.require_supervisor_target_chat:
            supervisor_rollup_message_id = find_supervisor_rollup_message(
                root,
                args.supervisor_agent,
                args.job_ref,
                str(job["group_peer_id"]),
            )
            if supervisor_rollup_message_id is None:
                emit(
                    "SUPERVISOR_ROLLUP_TARGET_MISSING: "
                    f"agent={args.supervisor_agent} group={job['group_peer_id']} job={args.job_ref}"
                )
                return 3
    else:
        if args.require_supervisor_target_chat:
            emit("SUPERVISOR_TARGET_CHECK_REQUIRES_VISIBLE_MESSAGES")
            return 2

    result_fields = [
        args.success_token + ":",
        f"jobRef={job['job_ref']}",
        f"title={job['title']}",
        f"status={job['status']}",
    ]
    if args.team_key:
        result_fields.append(f"teamKey={args.team_key}")
    for agent_id in required_agents:
        result_fields.append(f"{agent_id}_progress={participants[agent_id]['progress_message_id']}")
        result_fields.append(f"{agent_id}_final={participants[agent_id]['final_message_id']}")
    if args.require_supervisor_target_chat:
        supervisor_rollup_message_id = find_supervisor_rollup_message(
            Path(args.session_root),
            args.supervisor_agent,
            args.job_ref,
            str(job["group_peer_id"]),
        )
        if supervisor_rollup_message_id:
            result_fields.append(f"{args.supervisor_agent}_final={supervisor_rollup_message_id}")
    emit(" ".join(result_fields))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
