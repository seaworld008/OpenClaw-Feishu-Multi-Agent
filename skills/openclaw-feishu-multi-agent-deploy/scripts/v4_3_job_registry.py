#!/usr/bin/env python3
"""Minimal SQLite-backed job registry for V4.3 single-group production mode."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_prefix() -> str:
    return datetime.now(timezone.utc).strftime("TG-%Y%m%d")


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  job_ref TEXT PRIMARY KEY,
  group_peer_id TEXT NOT NULL,
  requested_by TEXT,
  source_message_id TEXT,
  title TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'queued', 'done', 'failed', 'cancelled')),
  queue_position INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  closed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_group_status ON jobs(group_peer_id, status);
CREATE INDEX IF NOT EXISTS idx_jobs_group_created ON jobs(group_peer_id, created_at);

CREATE TABLE IF NOT EXISTS job_participants (
  job_ref TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  role TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'running', 'done', 'failed')),
  dispatch_run_id TEXT,
  dispatch_status TEXT,
  progress_message_id TEXT,
  final_message_id TEXT,
  summary TEXT,
  completed_at TEXT,
  PRIMARY KEY (job_ref, agent_id),
  FOREIGN KEY (job_ref) REFERENCES jobs(job_ref)
);

CREATE TABLE IF NOT EXISTS job_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_ref TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor TEXT NOT NULL,
  payload_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (job_ref) REFERENCES jobs(job_ref)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_group_single_active
ON jobs(group_peer_id)
WHERE status = 'active';
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def next_job_ref(conn: sqlite3.Connection) -> str:
    prefix = today_prefix()
    row = conn.execute(
        "SELECT job_ref FROM jobs WHERE job_ref LIKE ? ORDER BY job_ref DESC LIMIT 1",
        (f"{prefix}-%",),
    ).fetchone()
    if not row:
        return f"{prefix}-001"
    seq = int(row["job_ref"].split("-")[-1]) + 1
    return f"{prefix}-{seq:03d}"


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def get_active_job(conn: sqlite3.Connection, group_peer_id: str):
    return conn.execute(
        "SELECT * FROM jobs WHERE group_peer_id = ? AND status = 'active' LIMIT 1",
        (group_peer_id,),
    ).fetchone()


def get_job(conn: sqlite3.Connection, job_ref: str):
    return conn.execute(
        "SELECT * FROM jobs WHERE job_ref = ?",
        (job_ref,),
    ).fetchone()


def participant_stats(conn: sqlite3.Connection, job_ref: str) -> dict:
    row = conn.execute(
        """
        SELECT
          COUNT(*) AS participant_count,
          SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS completed_count
        FROM job_participants
        WHERE job_ref = ?
        """,
        (job_ref,),
    ).fetchone()
    return {
        "participantCount": int(row["participant_count"] or 0),
        "completedParticipantCount": int(row["completed_count"] or 0),
    }


def participant_rows(conn: sqlite3.Connection, job_ref: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
          job_ref, agent_id, account_id, role, status, dispatch_run_id, dispatch_status,
          progress_message_id, final_message_id, summary, completed_at
        FROM job_participants
        WHERE job_ref = ?
        ORDER BY agent_id ASC
        """,
        (job_ref,),
    ).fetchall()


def participant_map(conn: sqlite3.Connection, job_ref: str) -> dict[str, sqlite3.Row]:
    return {row["agent_id"]: row for row in participant_rows(conn, job_ref)}


def job_age_seconds(row: sqlite3.Row, reference: datetime | None = None) -> int:
    if reference is None:
        reference = datetime.now(timezone.utc)
    updated_at = datetime.fromisoformat(row["updated_at"])
    return max(0, int((reference - updated_at).total_seconds()))


def job_ready_to_rollup(conn: sqlite3.Connection, job_ref: str) -> tuple[bool, dict]:
    by_agent = participant_map(conn, job_ref)
    ready = all(
        agent in by_agent
        and by_agent[agent]["status"] == "done"
        and by_agent[agent]["progress_message_id"]
        and by_agent[agent]["final_message_id"]
        for agent in ("ops_agent", "finance_agent")
    )
    payload = {
        agent: {
            "status": by_agent[agent]["status"],
            "dispatchStatus": by_agent[agent]["dispatch_status"],
            "progressMessageId": by_agent[agent]["progress_message_id"],
            "finalMessageId": by_agent[agent]["final_message_id"],
            "summary": by_agent[agent]["summary"],
        }
        for agent in by_agent
    }
    return ready, payload


def latest_completion_packets(conn: sqlite3.Connection, job_ref: str) -> dict[str, dict]:
    rows = conn.execute(
        """
        SELECT actor, payload_json
        FROM job_events
        WHERE job_ref = ? AND event_type = 'worker_completed'
        ORDER BY id ASC
        """,
        (job_ref,),
    ).fetchall()
    packets: dict[str, dict] = {}
    for row in rows:
        actor = row["actor"]
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        packets[actor] = payload
    return packets


def next_queue_position(conn: sqlite3.Connection, group_peer_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(queue_position), 0) AS max_pos "
        "FROM jobs WHERE group_peer_id = ? AND status = 'queued'",
        (group_peer_id,),
    ).fetchone()
    return int(row["max_pos"]) + 1


def insert_event(conn: sqlite3.Connection, job_ref: str, event_type: str, actor: str, payload: dict) -> None:
    conn.execute(
        "INSERT INTO job_events (job_ref, event_type, actor, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (job_ref, event_type, actor, json.dumps(payload, ensure_ascii=False), now_iso()),
    )


def promote_next_queued_job(conn: sqlite3.Connection, group_peer_id: str, promoted_at: str):
    next_row = conn.execute(
        """
        SELECT job_ref FROM jobs
        WHERE group_peer_id = ? AND status = 'queued'
        ORDER BY queue_position ASC, created_at ASC
        LIMIT 1
        """,
        (group_peer_id,),
    ).fetchone()
    if not next_row:
        return None
    conn.execute(
        "UPDATE jobs SET status = 'active', queue_position = NULL, updated_at = ? WHERE job_ref = ?",
        (promoted_at, next_row["job_ref"]),
    )
    insert_event(conn, next_row["job_ref"], "job_promoted", "system", {"from": "queued"})
    return next_row["job_ref"]


def fail_job_and_promote(
    conn: sqlite3.Connection,
    job_ref: str,
    reason: str,
    actor: str = "system",
) -> dict:
    row = get_job(conn, job_ref)
    if not row:
        return {"status": "job_missing", "jobRef": job_ref}

    closed_at = now_iso()
    conn.execute(
        "UPDATE jobs SET status = 'failed', updated_at = ?, closed_at = ? WHERE job_ref = ?",
        (closed_at, closed_at, job_ref),
    )
    insert_event(
        conn,
        job_ref,
        "job_closed",
        actor,
        {"status": "failed", "reason": reason},
    )
    promoted_job_ref = None
    if row["group_peer_id"]:
        promoted_job_ref = promote_next_queued_job(conn, row["group_peer_id"], closed_at)
    return {
        "status": "failed",
        "jobRef": job_ref,
        "reason": reason,
        "promotedJobRef": promoted_job_ref,
    }


def cmd_init_db(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    emit({"status": "initialized", "db": str(args.db)})
    return 0


def cmd_start_job(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    active = get_active_job(conn, args.group_peer_id)
    job_ref = next_job_ref(conn)
    created_at = now_iso()
    if active:
        status = "queued"
        queue_position = next_queue_position(conn, args.group_peer_id)
    else:
        status = "active"
        queue_position = None
    conn.execute(
        "INSERT INTO jobs (job_ref, group_peer_id, requested_by, source_message_id, title, status, queue_position, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            job_ref,
            args.group_peer_id,
            args.requested_by,
            args.source_message_id,
            args.title,
            status,
            queue_position,
            created_at,
            created_at,
        ),
    )
    insert_event(
        conn,
        job_ref,
        "job_started",
        args.requested_by or "system",
        {"title": args.title, "status": status, "queuePosition": queue_position},
    )
    conn.commit()
    emit(
        {
            "jobRef": job_ref,
            "status": status,
            "queuePosition": queue_position,
            "title": args.title,
            "groupPeerId": args.group_peer_id,
        }
    )
    return 0


def cmd_append_note(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    active = get_active_job(conn, args.group_peer_id)
    if not active:
        emit({"status": "no_active_job", "groupPeerId": args.group_peer_id})
        return 2
    conn.execute(
        "UPDATE jobs SET updated_at = ? WHERE job_ref = ?",
        (now_iso(), active["job_ref"]),
    )
    insert_event(
        conn,
        active["job_ref"],
        "note_appended",
        args.sender_id or "unknown",
        {"text": args.text},
    )
    conn.commit()
    emit(
        {
            "jobRef": active["job_ref"],
            "status": "appended",
            "groupPeerId": args.group_peer_id,
        }
    )
    return 0


def cmd_mark_worker_complete(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    completed_at = now_iso()
    existing = conn.execute(
        "SELECT account_id, role, dispatch_run_id, dispatch_status FROM job_participants WHERE job_ref = ? AND agent_id = ?",
        (args.job_ref, args.agent_id),
    ).fetchone()
    defaults = {
        "ops_agent": {"account_id": "xiaolongxia", "role": "运营执行"},
        "finance_agent": {"account_id": "yiran_yibao", "role": "财务执行"},
        "sales_agent": {"account_id": "aoteman", "role": "销售执行"},
    }
    account_id = args.account_id or (existing["account_id"] if existing and existing["account_id"] else defaults.get(args.agent_id, {}).get("account_id", ""))
    role = args.role or (existing["role"] if existing and existing["role"] else defaults.get(args.agent_id, {}).get("role", ""))
    dispatch_run_id = args.dispatch_run_id or (existing["dispatch_run_id"] if existing and existing["dispatch_run_id"] else "")
    dispatch_status = args.dispatch_status or (existing["dispatch_status"] if existing and existing["dispatch_status"] else "accepted")
    conn.execute(
        """
        INSERT INTO job_participants (
          job_ref, agent_id, account_id, role, status, dispatch_run_id, dispatch_status,
          progress_message_id, final_message_id, summary, completed_at
        ) VALUES (?, ?, ?, ?, 'done', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_ref, agent_id) DO UPDATE SET
          account_id=excluded.account_id,
          role=excluded.role,
          status='done',
          dispatch_run_id=excluded.dispatch_run_id,
          dispatch_status=excluded.dispatch_status,
          progress_message_id=excluded.progress_message_id,
          final_message_id=excluded.final_message_id,
          summary=excluded.summary,
          completed_at=excluded.completed_at
        """,
        (
            args.job_ref,
            args.agent_id,
            account_id,
            role,
            dispatch_run_id,
            dispatch_status,
            args.progress_message_id,
            args.final_message_id,
            args.summary,
            completed_at,
        ),
    )
    conn.execute(
        "UPDATE jobs SET updated_at = ? WHERE job_ref = ?",
        (completed_at, args.job_ref),
    )
    insert_event(
        conn,
        args.job_ref,
        "worker_completed",
        args.agent_id,
        {
            "progressMessageId": args.progress_message_id,
            "finalMessageId": args.final_message_id,
            "summary": args.summary,
            "details": args.details,
            "risks": args.risks,
            "dependencies": args.dependencies,
            "conflicts": args.conflicts,
        },
    )
    conn.commit()
    emit({"jobRef": args.job_ref, "agentId": args.agent_id, "status": "done"})
    return 0


def cmd_mark_dispatch(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    dispatched_at = now_iso()
    conn.execute(
        """
        INSERT INTO job_participants (
          job_ref, agent_id, account_id, role, status, dispatch_run_id, dispatch_status,
          progress_message_id, final_message_id, summary, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, '', '', '', NULL)
        ON CONFLICT(job_ref, agent_id) DO UPDATE SET
          account_id=excluded.account_id,
          role=excluded.role,
          status=excluded.status,
          dispatch_run_id=excluded.dispatch_run_id,
          dispatch_status=excluded.dispatch_status
        """,
        (
            args.job_ref,
            args.agent_id,
            args.account_id,
            args.role,
            args.status,
            args.dispatch_run_id,
            args.dispatch_status,
        ),
    )
    conn.execute(
        "UPDATE jobs SET updated_at = ? WHERE job_ref = ?",
        (dispatched_at, args.job_ref),
    )
    insert_event(
        conn,
        args.job_ref,
        "worker_dispatched",
        args.agent_id,
        {
            "status": args.status,
            "dispatchRunId": args.dispatch_run_id,
            "dispatchStatus": args.dispatch_status,
        },
    )
    conn.commit()
    emit(
        {
            "jobRef": args.job_ref,
            "agentId": args.agent_id,
            "status": args.status,
            "dispatchStatus": args.dispatch_status,
        }
    )
    return 0


def cmd_get_active(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    active = get_active_job(conn, args.group_peer_id)
    if not active:
        emit({"active": None, "groupPeerId": args.group_peer_id})
        return 0
    stats = participant_stats(conn, active["job_ref"])
    ready, participants = job_ready_to_rollup(conn, active["job_ref"])
    emit(
        {
            "active": {
                "jobRef": active["job_ref"],
                "title": active["title"],
                "status": active["status"],
                "createdAt": active["created_at"],
                "updatedAt": active["updated_at"],
                "ageSeconds": job_age_seconds(active),
                "readyToRollup": ready,
                "participants": participants,
                **stats,
            }
        }
    )
    return 0


def cmd_get_job(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    row = get_job(conn, args.job_ref)
    if not row:
        emit({"job": None, "jobRef": args.job_ref})
        return 2
    ready, participants = job_ready_to_rollup(conn, args.job_ref)
    emit(
        {
            "job": {
                "jobRef": row["job_ref"],
                "groupPeerId": row["group_peer_id"],
                "requestedBy": row["requested_by"],
                "sourceMessageId": row["source_message_id"],
                "title": row["title"],
                "status": row["status"],
                "queuePosition": row["queue_position"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
                "closedAt": row["closed_at"],
                "ageSeconds": job_age_seconds(row),
                "readyToRollup": ready,
                "participants": participants,
                "completionPackets": latest_completion_packets(conn, args.job_ref),
                **participant_stats(conn, args.job_ref),
            }
        }
    )
    return 0


def cmd_list_queue(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    rows = conn.execute(
        """
        SELECT job_ref, title, status, queue_position, requested_by, created_at, updated_at
        FROM jobs
        WHERE group_peer_id = ? AND status = 'queued'
        ORDER BY queue_position ASC, created_at ASC
        """,
        (args.group_peer_id,),
    ).fetchall()
    emit(
        {
            "groupPeerId": args.group_peer_id,
            "queuedJobs": [
                {
                    "jobRef": row["job_ref"],
                    "title": row["title"],
                    "status": row["status"],
                    "queuePosition": row["queue_position"],
                    "requestedBy": row["requested_by"],
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                }
                for row in rows
            ],
        }
    )
    return 0


def cmd_ready_to_rollup(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    ready, participants = job_ready_to_rollup(conn, args.job_ref)
    emit(
        {
            "jobRef": args.job_ref,
            "ready": ready,
            "participants": participants,
        }
    )
    return 0


def cmd_close_job(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    closed_at = now_iso()
    conn.execute(
        "UPDATE jobs SET status = ?, updated_at = ?, closed_at = ? WHERE job_ref = ?",
        (args.status, closed_at, closed_at, args.job_ref),
    )
    insert_event(conn, args.job_ref, "job_closed", "system", {"status": args.status})
    row = conn.execute(
        "SELECT * FROM jobs WHERE job_ref = ?",
        (args.job_ref,),
    ).fetchone()
    if row and row["group_peer_id"]:
        promote_next_queued_job(conn, row["group_peer_id"], closed_at)
    conn.commit()
    emit({"jobRef": args.job_ref, "status": args.status})
    return 0


def cmd_recover_stale(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    active = get_active_job(conn, args.group_peer_id)
    if not active:
        emit({"status": "no_active_job", "groupPeerId": args.group_peer_id})
        return 0

    stats = participant_stats(conn, active["job_ref"])
    ready, participants = job_ready_to_rollup(conn, active["job_ref"])
    age_seconds = job_age_seconds(active)

    if ready:
        emit(
            {
                "status": "ready_pending_rollup",
                "jobRef": active["job_ref"],
                "ageSeconds": age_seconds,
                "participants": participants,
                **stats,
            }
        )
        return 0

    if age_seconds < args.stale_seconds:
        emit(
            {
                "status": "active_ok",
                "jobRef": active["job_ref"],
                "ageSeconds": age_seconds,
                "participants": participants,
                **stats,
            }
        )
        return 0

    result = fail_job_and_promote(
        conn,
        active["job_ref"],
        reason=f"stale-after-{args.stale_seconds}s",
        actor="system",
    )
    conn.commit()
    emit(
        {
            "status": "stale_recovered",
            "closedJobRef": active["job_ref"],
            "closedAs": "failed",
            "ageSeconds": age_seconds,
            "participants": participants,
            "promotedJobRef": result["promotedJobRef"],
        }
    )
    return 0


def cmd_begin_turn(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)

    active = get_active_job(conn, args.group_peer_id)
    recovered = None

    if active:
        stats = participant_stats(conn, active["job_ref"])
        ready, participants = job_ready_to_rollup(conn, active["job_ref"])
        age_seconds = job_age_seconds(active)
        if not ready and age_seconds >= args.stale_seconds:
            result = fail_job_and_promote(
                conn,
                active["job_ref"],
                reason=f"stale-after-{args.stale_seconds}s",
                actor="system",
            )
            conn.commit()
            recovered = {
                "status": "stale_recovered",
                "closedJobRef": active["job_ref"],
                "closedAs": "failed",
                "ageSeconds": age_seconds,
                "participants": participants,
                "promotedJobRef": result["promotedJobRef"],
            }

    active = get_active_job(conn, args.group_peer_id)
    if not active:
        emit({"recover": recovered, "active": None, "groupPeerId": args.group_peer_id})
        return 0

    stats = participant_stats(conn, active["job_ref"])
    ready, participants = job_ready_to_rollup(conn, active["job_ref"])
    emit(
        {
            "recover": recovered
            or {
                "status": "active_ok",
                "jobRef": active["job_ref"],
                "ageSeconds": job_age_seconds(active),
                "readyToRollup": ready,
                "participants": participants,
                **stats,
            },
            "active": {
                "jobRef": active["job_ref"],
                "title": active["title"],
                "status": active["status"],
                "createdAt": active["created_at"],
                "updatedAt": active["updated_at"],
                "ageSeconds": job_age_seconds(active),
                "readyToRollup": ready,
                "participants": participants,
                **stats,
            },
            "groupPeerId": args.group_peer_id,
        }
    )
    return 0


def cmd_watchdog_tick(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    active = get_active_job(conn, args.group_peer_id)
    if not active:
        emit({"status": "no_active_job", "groupPeerId": args.group_peer_id})
        return 0

    stats = participant_stats(conn, active["job_ref"])
    ready, participants = job_ready_to_rollup(conn, active["job_ref"])
    age_seconds = job_age_seconds(active)

    if ready:
        emit(
            {
                "status": "ready_pending_rollup",
                "jobRef": active["job_ref"],
                "ageSeconds": age_seconds,
                "participants": participants,
                **stats,
            }
        )
        return 0

    if age_seconds < args.stale_seconds:
        emit(
            {
                "status": "active_ok",
                "jobRef": active["job_ref"],
                "ageSeconds": age_seconds,
                "participants": participants,
                **stats,
            }
        )
        return 0

    result = fail_job_and_promote(
        conn,
        active["job_ref"],
        reason=f"watchdog-stale-after-{args.stale_seconds}s",
        actor="watchdog",
    )
    conn.commit()
    emit(
        {
            "status": "stale_recovered",
            "closedJobRef": active["job_ref"],
            "ageSeconds": age_seconds,
            "participants": participants,
            "promotedJobRef": result["promotedJobRef"],
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db")

    start = sub.add_parser("start-job")
    start.add_argument("--group-peer-id", required=True)
    start.add_argument("--requested-by", default="")
    start.add_argument("--source-message-id", default="")
    start.add_argument("--title", required=True)

    append = sub.add_parser("append-note")
    append.add_argument("--group-peer-id", required=True)
    append.add_argument("--sender-id", default="")
    append.add_argument("--text", required=True)

    dispatch = sub.add_parser("mark-dispatch")
    dispatch.add_argument("--job-ref", required=True)
    dispatch.add_argument("--agent-id", required=True)
    dispatch.add_argument("--account-id", required=True)
    dispatch.add_argument("--role", required=True)
    dispatch.add_argument("--status", default="accepted", choices=["pending", "accepted", "running", "failed"])
    dispatch.add_argument("--dispatch-run-id", default="")
    dispatch.add_argument("--dispatch-status", default="")

    complete = sub.add_parser("mark-worker-complete")
    complete.add_argument("--job-ref", required=True)
    complete.add_argument("--agent-id", required=True)
    complete.add_argument("--account-id", default="")
    complete.add_argument("--role", default="")
    complete.add_argument("--dispatch-run-id", default="")
    complete.add_argument("--dispatch-status", default="")
    complete.add_argument("--progress-message-id", required=True)
    complete.add_argument("--final-message-id", required=True)
    complete.add_argument("--summary", default="")
    complete.add_argument("--details", default="")
    complete.add_argument("--risks", default="")
    complete.add_argument("--dependencies", default="")
    complete.add_argument("--conflicts", default="")

    active = sub.add_parser("get-active")
    active.add_argument("--group-peer-id", required=True)

    get_job = sub.add_parser("get-job")
    get_job.add_argument("--job-ref", required=True)

    list_queue = sub.add_parser("list-queue")
    list_queue.add_argument("--group-peer-id", required=True)

    ready = sub.add_parser("ready-to-rollup")
    ready.add_argument("--job-ref", required=True)

    close = sub.add_parser("close-job")
    close.add_argument("--job-ref", required=True)
    close.add_argument("--status", default="done", choices=["done", "failed", "cancelled"])

    recover = sub.add_parser("recover-stale")
    recover.add_argument("--group-peer-id", required=True)
    recover.add_argument("--stale-seconds", type=int, default=180)

    begin = sub.add_parser("begin-turn")
    begin.add_argument("--group-peer-id", required=True)
    begin.add_argument("--stale-seconds", type=int, default=180)

    watchdog = sub.add_parser("watchdog-tick")
    watchdog.add_argument("--group-peer-id", required=True)
    watchdog.add_argument("--stale-seconds", type=int, default=180)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    handlers = {
        "init-db": cmd_init_db,
        "start-job": cmd_start_job,
        "append-note": cmd_append_note,
        "mark-dispatch": cmd_mark_dispatch,
        "mark-worker-complete": cmd_mark_worker_complete,
        "get-active": cmd_get_active,
        "get-job": cmd_get_job,
        "list-queue": cmd_list_queue,
        "ready-to-rollup": cmd_ready_to_rollup,
        "close-job": cmd_close_job,
        "recover-stale": cmd_recover_stale,
        "begin-turn": cmd_begin_turn,
        "watchdog-tick": cmd_watchdog_tick,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
