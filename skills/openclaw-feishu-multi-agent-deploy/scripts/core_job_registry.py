#!/usr/bin/env python3
"""Shared SQLite-backed job registry for OpenClaw Feishu team workflows."""

from __future__ import annotations

import argparse
import json
import re
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
  workflow_json TEXT,
  orchestrator_version TEXT,
  request_text TEXT,
  supervisor_visible_label TEXT,
  entry_account_id TEXT,
  entry_channel TEXT,
  entry_target TEXT,
  entry_delivery_json TEXT,
  hidden_main_session_key TEXT,
  current_stage_index INTEGER,
  waiting_for_agent_id TEXT,
  next_action TEXT,
  ack_visible_sent INTEGER NOT NULL DEFAULT 0,
  ack_visible_message_id TEXT,
  rollup_visible_sent INTEGER NOT NULL DEFAULT 0,
  rollup_visible_message_id TEXT,
  dispatch_attempt_count INTEGER NOT NULL DEFAULT 0,
  last_control_error TEXT,
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
  visible_label TEXT,
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

JOB_EXTRA_COLUMNS = {
    "workflow_json": "TEXT",
    "orchestrator_version": "TEXT",
    "request_text": "TEXT",
    "supervisor_visible_label": "TEXT",
    "entry_account_id": "TEXT",
    "entry_channel": "TEXT",
    "entry_target": "TEXT",
    "entry_delivery_json": "TEXT",
    "hidden_main_session_key": "TEXT",
    "current_stage_index": "INTEGER",
    "waiting_for_agent_id": "TEXT",
    "next_action": "TEXT",
    "ack_visible_sent": "INTEGER NOT NULL DEFAULT 0",
    "ack_visible_message_id": "TEXT",
    "rollup_visible_sent": "INTEGER NOT NULL DEFAULT 0",
    "rollup_visible_message_id": "TEXT",
    "dispatch_attempt_count": "INTEGER NOT NULL DEFAULT 0",
    "last_control_error": "TEXT",
}

PARTICIPANT_EXTRA_COLUMNS = {
    "visible_label": "TEXT",
}

V5_1_HARDENING = "V5.1 Hardening"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    existing_jobs_columns = {
        row["name"] if isinstance(row, sqlite3.Row) else row[1]
        for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
    }
    for column, definition in JOB_EXTRA_COLUMNS.items():
        if column not in existing_jobs_columns:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {column} {definition}")
    existing_participant_columns = {
        row["name"] if isinstance(row, sqlite3.Row) else row[1]
        for row in conn.execute("PRAGMA table_info(job_participants)").fetchall()
    }
    for column, definition in PARTICIPANT_EXTRA_COLUMNS.items():
        if column not in existing_participant_columns:
            conn.execute(f"ALTER TABLE job_participants ADD COLUMN {column} {definition}")
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


def flag_value(value) -> bool:
    return bool(int(value or 0))


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
          job_ref, agent_id, account_id, role, visible_label, status, dispatch_run_id, dispatch_status,
          progress_message_id, final_message_id, summary, completed_at
        FROM job_participants
        WHERE job_ref = ?
        ORDER BY agent_id ASC
        """,
        (job_ref,),
    ).fetchall()


def participant_map(conn: sqlite3.Connection, job_ref: str) -> dict[str, sqlite3.Row]:
    return {row["agent_id"]: row for row in participant_rows(conn, job_ref)}


def validate_participants_payload(raw: str | None, workflow: dict) -> list[dict]:
    if not raw:
        raise ValueError("participants_json is required in V5.1 Hardening")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"participants_json must be valid JSON: {exc}") from exc
    if not isinstance(decoded, list) or not decoded:
        raise ValueError("participants_json must be a non-empty array")

    normalized: list[dict] = []
    stage_agent_ids = set(workflow_stage_agent_ids(workflow))
    seen_agent_ids: set[str] = set()
    for idx, item in enumerate(decoded):
        if not isinstance(item, dict):
            raise ValueError(f"participants_json[{idx}] must be an object")
        agent_id = str(item.get("agentId") or "").strip()
        account_id = str(item.get("accountId") or "").strip()
        role = str(item.get("role") or "").strip()
        visible_label = str(item.get("visibleLabel") or "").strip()
        if not agent_id or not account_id or not role:
            raise ValueError(f"participants_json[{idx}] requires agentId, accountId and role")
        if not visible_label:
            raise ValueError(f"participants_json[{idx}].visibleLabel is required")
        if agent_id not in stage_agent_ids:
            raise ValueError(f"participants_json[{idx}].agentId must exist in workflow.stages: {agent_id}")
        if agent_id in seen_agent_ids:
            raise ValueError(f"participants_json contains duplicate agentId: {agent_id}")
        seen_agent_ids.add(agent_id)
        normalized.append(
            {
                "agentId": agent_id,
                "accountId": account_id,
                "role": role,
                "visibleLabel": visible_label,
            }
        )

    missing = sorted(stage_agent_ids - seen_agent_ids)
    if missing:
        raise ValueError(
            "participants_json must include every workflow stage agent exactly once; "
            f"missing: {', '.join(missing)}"
        )
    return normalized


def validate_workflow_payload(workflow: dict) -> dict:
    if not isinstance(workflow, dict):
        raise ValueError("workflow must be an object")
    mode = str(workflow.get("mode") or "serial").strip()
    if mode != "serial":
        raise ValueError("only serial workflow is supported in V5.1 Hardening")
    stages = workflow.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("workflow.stages must be a non-empty array")

    normalized_stages = []
    seen_agent_ids: set[str] = set()
    for idx, stage in enumerate(stages):
        if not isinstance(stage, dict):
            raise ValueError(f"workflow.stages[{idx}] must be an object")
        agent_id = str(stage.get("agentId") or "").strip()
        if not agent_id:
            raise ValueError(f"workflow.stages[{idx}].agentId is required")
        if agent_id in seen_agent_ids:
            raise ValueError(f"workflow.stages contains duplicate agentId: {agent_id}")
        seen_agent_ids.add(agent_id)
        normalized_stages.append({"agentId": agent_id})

    return {
        "mode": mode,
        "stages": normalized_stages,
    }


def parse_workflow_json(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    try:
        return validate_workflow_payload(decoded)
    except ValueError:
        return None


def workflow_stage_agent_ids(workflow: dict | None) -> list[str]:
    if not workflow:
        return []
    return [str(stage["agentId"]) for stage in workflow.get("stages", [])]


def workflow_initial_state(workflow: dict) -> tuple[int, str, str]:
    first_agent_id = workflow_stage_agent_ids(workflow)[0]
    return 0, first_agent_id, "dispatch"


def activate_promoted_job(conn: sqlite3.Connection, row: sqlite3.Row, promoted_at: str) -> None:
    workflow = parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
    if workflow:
        current_stage_index, waiting_for_agent_id, next_action = workflow_initial_state(workflow)
        conn.execute(
            """
            UPDATE jobs
            SET status = 'active',
                queue_position = NULL,
                updated_at = ?,
                current_stage_index = ?,
                waiting_for_agent_id = ?,
                next_action = ?
            WHERE job_ref = ?
            """,
            (
                promoted_at,
                current_stage_index,
                waiting_for_agent_id,
                next_action,
                row["job_ref"],
            ),
        )
        return

    conn.execute(
        "UPDATE jobs SET status = 'active', queue_position = NULL, updated_at = ? WHERE job_ref = ?",
        (promoted_at, row["job_ref"]),
    )


def next_action_payload_for_row(row: sqlite3.Row) -> dict | None:
    workflow = parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
    if not workflow:
        return None

    action = str(row["next_action"] or "").strip() or ("queued" if row["status"] == "queued" else "dispatch")
    payload = {
        "type": action,
        "mode": workflow["mode"],
        "totalStages": len(workflow["stages"]),
    }
    if row["current_stage_index"] is not None:
        payload["stageIndex"] = int(row["current_stage_index"])
    if row["waiting_for_agent_id"]:
        payload["agentId"] = row["waiting_for_agent_id"]
    return payload


def build_stage_packets(conn: sqlite3.Connection, job_ref: str, workflow: dict | None) -> list[dict]:
    if not workflow:
        return []

    by_agent = participant_map(conn, job_ref)
    completion_packets = latest_completion_packets(conn, job_ref)
    packets: list[dict] = []
    for idx, agent_id in enumerate(workflow_stage_agent_ids(workflow)):
        participant = by_agent.get(agent_id)
        packets.append(
            {
                "stageIndex": idx,
                "agentId": agent_id,
                "visibleLabel": str(participant["visible_label"] or "").strip() if participant else "",
                "status": participant["status"] if participant else None,
                "progressMessageId": participant["progress_message_id"] if participant else None,
                "finalMessageId": participant["final_message_id"] if participant else None,
                "summary": participant["summary"] if participant else None,
                "completionPacket": completion_packets.get(agent_id),
            }
        )
    return packets


def job_age_seconds(row: sqlite3.Row, reference: datetime | None = None) -> int:
    if reference is None:
        reference = datetime.now(timezone.utc)
    updated_at = datetime.fromisoformat(row["updated_at"])
    return max(0, int((reference - updated_at).total_seconds()))


def job_ready_to_rollup(conn: sqlite3.Connection, job_ref: str) -> tuple[bool, dict]:
    job = get_job(conn, job_ref)
    workflow = parse_workflow_json(job["workflow_json"]) if job and "workflow_json" in job.keys() else None
    by_agent = participant_map(conn, job_ref)
    required_rows = list(by_agent.values())
    active_job = bool(job) and str(job["status"] or "") == "active"
    if workflow and job:
        ready = active_job and str(job["next_action"] or "") == "rollup"
    else:
        ready = active_job and bool(required_rows) and all(
            row["status"] == "done"
            and row["progress_message_id"]
            and row["final_message_id"]
            for row in required_rows
        )
    payload = {
        agent: {
            "status": by_agent[agent]["status"],
            "visibleLabel": (
                str(by_agent[agent]["visible_label"] or "").strip()
                if workflow
                else participant_visible_label(by_agent[agent], agent)
            ),
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
        SELECT * FROM jobs
        WHERE group_peer_id = ? AND status = 'queued'
        ORDER BY queue_position ASC, created_at ASC
        LIMIT 1
        """,
        (group_peer_id,),
    ).fetchone()
    if not next_row:
        return None
    activate_promoted_job(conn, next_row, promoted_at)
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


def emit_workflow_out_of_order(job_ref: str, expected_agent_id: str | None, actual_agent_id: str) -> int:
    emit(
        {
            "status": "workflow_out_of_order",
            "jobRef": job_ref,
            "expectedAgentId": expected_agent_id,
            "actualAgentId": actual_agent_id,
        }
    )
    return 2


def hidden_main_agent_id(hidden_main_session_key: str | None) -> str:
    raw = str(hidden_main_session_key or "").strip()
    if raw.startswith("agent:") and raw.endswith(":main"):
        return raw[len("agent:") : -len(":main")]
    return ""


def visible_delivery_for_row(row: sqlite3.Row) -> dict | None:
    channel = str(row["entry_channel"] or "").strip() if "entry_channel" in row.keys() else ""
    account_id = str(row["entry_account_id"] or "").strip() if "entry_account_id" in row.keys() else ""
    target = str(row["entry_target"] or "").strip() if "entry_target" in row.keys() else ""
    if channel and account_id and target:
        return {
            "channel": channel,
            "accountId": account_id,
            "target": target,
        }
    raw = str(row["entry_delivery_json"] or "").strip() if "entry_delivery_json" in row.keys() else ""
    if not raw:
        return None
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    if decoded.get("channel") and decoded.get("accountId") and decoded.get("target"):
        return {
            "channel": decoded["channel"],
            "accountId": decoded["accountId"],
            "target": decoded["target"],
        }
    return None


def current_stage_participant(conn: sqlite3.Connection, row: sqlite3.Row) -> sqlite3.Row | None:
    if not row["waiting_for_agent_id"]:
        return None
    return participant_map(conn, row["job_ref"]).get(str(row["waiting_for_agent_id"]))


def workflow_visible_snapshot_error(conn: sqlite3.Connection, row: sqlite3.Row) -> str | None:
    workflow = parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
    if not workflow:
        return None
    if not str(row["supervisor_visible_label"] or "").strip():
        return "workflow supervisor visibleLabel snapshot is required"
    participants = participant_map(conn, row["job_ref"])
    for agent_id in workflow_stage_agent_ids(workflow):
        participant = participants.get(agent_id)
        if participant is None:
            return f"workflow participant snapshot missing: {agent_id}"
        if not str(participant["visible_label"] or "").strip():
            return f"workflow participant visibleLabel snapshot is required: {agent_id}"
    return None


def dispatch_record_exists(participant: sqlite3.Row | None) -> bool:
    if not participant:
        return False
    if participant["dispatch_run_id"]:
        return True
    return str(participant["status"] or "") in {"accepted", "running", "done", "failed"}


def clean_role_label(role: str) -> str:
    cleaned = str(role or "").strip()
    for needle in ("机器人", "专家", "执行", "Agent", "agent", "顾问", "负责人", "Leader", "leader"):
        cleaned = cleaned.replace(needle, "")
    return cleaned.strip(" -_/")


def participant_role_label(agent_id: str, role: str) -> str:
    hints = (
        (("运营", "ops", "operation"), "运营"),
        (("财务", "finance", "fin"), "财务"),
        (("销售", "sales", "biz"), "销售"),
        (("客服", "service", "support", "success"), "客服"),
        (("数据", "data", "analyst"), "数据"),
        (("人力", "hr", "people"), "人力"),
        (("法务", "legal", "compliance"), "法务"),
        (("产品", "product", "pm"), "产品"),
    )
    for candidate in (str(role or "").strip(), str(agent_id or "").strip()):
        lowered = candidate.lower()
        for markers, label in hints:
            if any(marker in lowered or marker in candidate for marker in markers):
                return label
    cleaned = clean_role_label(role)
    return cleaned or (str(agent_id or "阶段").strip() or "阶段")


def resolved_visible_label(
    *,
    explicit_label: str | None,
    agent_id: str,
    role: str,
    kind: str,
) -> str:
    label = str(explicit_label or "").strip()
    if label:
        return label
    if kind == "supervisor":
        inferred = participant_role_label(agent_id or "supervisor", role or "主管")
        return inferred if inferred and inferred != "阶段" else "主管"
    return participant_role_label(agent_id, role)


def participant_visible_label(participant: sqlite3.Row | dict | None, agent_id: str = "", role: str = "") -> str:
    if participant:
        explicit = participant["visible_label"] if "visible_label" in participant.keys() else participant.get("visible_label")
        agent_id = agent_id or (
            participant["agent_id"] if "agent_id" in participant.keys() else participant.get("agent_id", "")
        )
        role = role or (participant["role"] if "role" in participant.keys() else participant.get("role", ""))
    else:
        explicit = ""
    return resolved_visible_label(
        explicit_label=str(explicit or ""),
        agent_id=str(agent_id or ""),
        role=str(role or ""),
        kind="worker",
    )


def supervisor_visible_label_for_row(row: sqlite3.Row) -> str:
    explicit = str(row["supervisor_visible_label"] or "").strip() if "supervisor_visible_label" in row.keys() else ""
    return resolved_visible_label(
        explicit_label=explicit,
        agent_id=hidden_main_agent_id(row["hidden_main_session_key"]) if "hidden_main_session_key" in row.keys() else "supervisor",
        role="主管",
        kind="supervisor",
    )


def worker_visible_contract(
    job_ref: str,
    agent_id: str,
    role: str,
    visible_label: str | None = None,
) -> dict[str, str]:
    label = resolved_visible_label(
        explicit_label=str(visible_label or ""),
        agent_id=agent_id,
        role=role,
        kind="worker",
    )
    return {
        "roleLabel": label,
        "progressTitle": f"【{label}进度｜{job_ref}】",
        "finalTitle": f"【{label}结论｜{job_ref}】",
        "callbackMustInclude": "summary,details,risks,actionItems",
    }


def normalize_lines(raw: str) -> list[str]:
    text = str(raw or "").strip()
    if not text:
        return []
    chunks = [line.strip(" -•\t") for line in text.replace("\r", "\n").splitlines() if line.strip()]
    if len(chunks) == 1 and re.search(r"[；;]", chunks[0]):
        split_chunks = [part.strip(" -•\t") for part in re.split(r"[；;]", chunks[0]) if part.strip()]
        if len(split_chunks) > 1:
            return split_chunks
    return chunks


def normalize_visible_plan_lines(raw: str) -> list[str]:
    text = str(raw or "").replace("\r", "\n")
    if not text.strip():
        return []
    raw_lines = text.splitlines()
    cleaned: list[str] = []
    skipped_header = False
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if not skipped_header and stripped.startswith("【") and "】" in stripped:
            skipped_header = True
            continue
        skipped_header = True
        cleaned.append(stripped)
    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return cleaned


def chinese_section(index: int) -> str:
    mapping = {
        1: "一",
        2: "二",
        3: "三",
        4: "四",
        5: "五",
        6: "六",
        7: "七",
        8: "八",
        9: "九",
        10: "十",
    }
    return mapping.get(index, str(index))


def format_chinese_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]}和{items[1]}"
    return f"{'、'.join(items[:-1])}和{items[-1]}"


def ack_worker_role_summary(row: sqlite3.Row, conn: sqlite3.Connection | None = None) -> str:
    if conn is None or "workflow_json" not in row.keys():
        return ""
    workflow = parse_workflow_json(row["workflow_json"])
    stage_agent_ids = workflow_stage_agent_ids(workflow)
    if not stage_agent_ids:
        return ""
    participants = participant_map(conn, row["job_ref"])
    ordered_roles: list[str] = []
    seen_roles: set[str] = set()
    for agent_id in stage_agent_ids:
        participant = participants.get(agent_id)
        if participant is None:
            return ""
        visible_label = str(participant["visible_label"] or "").strip()
        if not visible_label:
            return ""
        if visible_label not in seen_roles:
            seen_roles.add(visible_label)
            ordered_roles.append(visible_label)
    return format_chinese_join(ordered_roles)


def visible_message_text(kind: str, row: sqlite3.Row, conn: sqlite3.Connection | None = None) -> str:
    job_ref = row["job_ref"]
    supervisor_label = supervisor_visible_label_for_row(row)
    if kind == "ack":
        role_summary = ack_worker_role_summary(row, conn)
        if role_summary:
            return f"【{supervisor_label}已接单｜{job_ref}】任务已受理，正分配给{role_summary}处理，请稍候查看进度。"
        return f"【{supervisor_label}已接单｜{job_ref}】任务已受理，按固定顺序推进，请稍候查看进度。"
    if kind == "rollup":
        workflow = parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
        participants = participant_map(conn, job_ref) if conn is not None else {}
        completion_packets = latest_completion_packets(conn, job_ref) if conn is not None else {}
        stage_agent_ids = workflow_stage_agent_ids(workflow) if workflow else list(participants.keys())
        lines = [
            f"【{supervisor_label}最终统一收口｜{job_ref}】",
            f"任务主题：{row['title']}",
            "",
            f"一、{supervisor_label}统一终案",
            "以下终案已结合各角色完整结论整理，可直接作为执行底稿。",
        ]
        risk_lines: list[str] = []
        action_lines: list[str] = []
        section_index = 2
        for agent_id in stage_agent_ids:
            participant = participants.get(agent_id)
            packet = completion_packets.get(agent_id, {})
            label = participant_visible_label(participant, agent_id)
            final_visible_text = str(packet.get("finalVisibleText") or packet.get("final_visible_text") or "").strip()
            summary = str(packet.get("summary") or (participant["summary"] if participant else "") or "").strip()
            details = str(packet.get("details") or "").strip()
            risks = str(packet.get("risks") or "").strip()
            action_items = str(packet.get("actionItems") or packet.get("action_items") or "").strip()
            section_lines = normalize_visible_plan_lines(final_visible_text)
            if section_lines:
                lines.extend(
                    [
                        "",
                        f"{chinese_section(section_index)}、{label}终案方案",
                        *section_lines,
                    ]
                )
            else:
                fallback_lines = normalize_lines(summary)
                for line in normalize_lines(details):
                    if line not in fallback_lines:
                        fallback_lines.append(line)
                if not fallback_lines:
                    fallback_lines.append(f"{label}已完成当前阶段方案输出，详见对应角色结论消息。")
                lines.extend(
                    [
                        "",
                        f"{chinese_section(section_index)}、{label}结论",
                        *[f"- {line}" for line in fallback_lines],
                    ]
                )
            section_index += 1
            if risks:
                risk_lines.extend(f"{label}：{line}" for line in normalize_lines(risks))
            if action_items:
                action_lines.extend(f"{label}：{line}" for line in normalize_lines(action_items))
        lines.extend(
            [
                "",
                f"{chinese_section(section_index)}、联合风险与红线",
                *([f"- {line}" for line in risk_lines] if risk_lines else ["- 当前未上报新增风险，请继续按各角色结论中的红线执行。"]),
                "",
                f"{chinese_section(section_index + 1)}、明日三件事",
                *([f"- {line}" for line in action_lines] if action_lines else ["- 先按上述统一方案推进，并在首轮执行后回收数据复盘。"]),
            ]
        )
        return "\n".join(lines)
    raise ValueError(f"unsupported visible message kind: {kind}")


def workflow_repair_status(conn: sqlite3.Connection, row: sqlite3.Row) -> dict | None:
    workflow = parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
    if not workflow:
        return None

    current_action = str(row["next_action"] or "").strip()
    participant = current_stage_participant(conn, row)
    if current_action == "dispatch":
        return {
            "status": "needs_dispatch_reconcile",
            "jobRef": row["job_ref"],
            "stageAgentId": row["waiting_for_agent_id"],
            "ackVisibleSent": flag_value(row["ack_visible_sent"]) if "ack_visible_sent" in row.keys() else False,
        }

    if current_action == "wait_worker":
        if not dispatch_record_exists(participant):
            return {
                "status": "needs_dispatch_reconcile",
                "jobRef": row["job_ref"],
                "stageAgentId": row["waiting_for_agent_id"],
                "ackVisibleSent": flag_value(row["ack_visible_sent"]) if "ack_visible_sent" in row.keys() else False,
            }
        return None

    if current_action == "rollup" and not flag_value(row["rollup_visible_sent"] if "rollup_visible_sent" in row.keys() else 0):
        return {
            "status": "needs_rollup_reconcile",
            "jobRef": row["job_ref"],
            "stageAgentId": row["waiting_for_agent_id"],
            "rollupVisibleSent": False,
        }
    return None


def visible_snapshot_status_payload(snapshot_error: str | None) -> dict:
    if not snapshot_error:
        return {}
    return {
        "snapshotStatus": "invalid_visible_label",
        "snapshotError": snapshot_error,
    }


def build_job_control_state(row: sqlite3.Row) -> dict:
    workflow = parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
    payload = {
        "orchestratorVersion": row["orchestrator_version"] or (V5_1_HARDENING if workflow else None),
        "workflow": workflow,
        "currentStageIndex": int(row["current_stage_index"]) if row["current_stage_index"] is not None else None,
        "waitingForAgentId": row["waiting_for_agent_id"],
        "nextAction": next_action_payload_for_row(row),
    }
    if "ack_visible_sent" in row.keys():
        payload["ackVisibleSent"] = flag_value(row["ack_visible_sent"])
    if "rollup_visible_sent" in row.keys():
        payload["rollupVisibleSent"] = flag_value(row["rollup_visible_sent"])
    if "entry_account_id" in row.keys() and row["entry_account_id"]:
        payload["entryAccountId"] = row["entry_account_id"]
    if "entry_channel" in row.keys() and row["entry_channel"]:
        payload["entryChannel"] = row["entry_channel"]
    if "entry_target" in row.keys() and row["entry_target"]:
        payload["entryTarget"] = row["entry_target"]
    if "hidden_main_session_key" in row.keys() and row["hidden_main_session_key"]:
        payload["hiddenMainSessionKey"] = row["hidden_main_session_key"]
    if "supervisor_visible_label" in row.keys():
        payload["supervisorVisibleLabel"] = (
            str(row["supervisor_visible_label"] or "").strip()
            if workflow
            else supervisor_visible_label_for_row(row)
        )
    return payload


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


def cmd_start_job_with_workflow(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    try:
        workflow = validate_workflow_payload(json.loads(args.workflow_json))
        participants = validate_participants_payload(args.participants_json, workflow)
    except (json.JSONDecodeError, ValueError) as exc:
        emit({"status": "invalid_workflow", "error": str(exc)})
        return 2
    supervisor_visible_label = str(args.supervisor_visible_label or "").strip()
    if not supervisor_visible_label:
        emit({"status": "invalid_workflow", "error": "supervisor_visible_label is required in V5.1 Hardening"})
        return 2
    active = get_active_job(conn, args.group_peer_id)
    job_ref = next_job_ref(conn)
    created_at = now_iso()

    if active:
        status = "queued"
        queue_position = next_queue_position(conn, args.group_peer_id)
        current_stage_index = 0
        waiting_for_agent_id = workflow_stage_agent_ids(workflow)[0]
        next_action = "queued"
    else:
        status = "active"
        queue_position = None
        current_stage_index, waiting_for_agent_id, next_action = workflow_initial_state(workflow)
    entry_delivery = {
        "channel": args.entry_channel,
        "accountId": args.entry_account_id,
        "target": args.entry_target,
    }
    entry_delivery_json = (
        json.dumps(entry_delivery, ensure_ascii=False)
        if entry_delivery["channel"] and entry_delivery["accountId"] and entry_delivery["target"]
        else args.entry_delivery_json
    )
    conn.execute(
        """
        INSERT INTO jobs (
          job_ref, group_peer_id, requested_by, source_message_id, title, status, queue_position,
          workflow_json, orchestrator_version, request_text, supervisor_visible_label, entry_account_id, entry_channel,
          entry_target, entry_delivery_json, hidden_main_session_key,
          current_stage_index, waiting_for_agent_id, next_action,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_ref,
            args.group_peer_id,
            args.requested_by,
            args.source_message_id,
            args.title,
            status,
            queue_position,
            json.dumps(workflow, ensure_ascii=False),
            args.orchestrator_version or V5_1_HARDENING,
            args.request_text,
            supervisor_visible_label,
            args.entry_account_id,
            args.entry_channel,
            args.entry_target,
            entry_delivery_json,
            args.hidden_main_session_key,
            current_stage_index,
            waiting_for_agent_id,
            next_action,
            created_at,
            created_at,
        ),
    )
    insert_event(
        conn,
        job_ref,
        "job_started",
        args.requested_by or "system",
        {
            "title": args.title,
            "status": status,
            "queuePosition": queue_position,
            "workflow": workflow,
            "orchestratorVersion": args.orchestrator_version or V5_1_HARDENING,
            "requestText": args.request_text,
            "entryDelivery": entry_delivery if entry_delivery_json else None,
        },
    )
    for participant in participants:
        conn.execute(
            """
            INSERT INTO job_participants (
              job_ref, agent_id, account_id, role, visible_label, status, dispatch_run_id, dispatch_status,
              progress_message_id, final_message_id, summary, completed_at
            ) VALUES (?, ?, ?, ?, ?, 'pending', '', '', '', '', '', NULL)
            ON CONFLICT(job_ref, agent_id) DO UPDATE SET
              account_id=excluded.account_id,
              role=excluded.role,
              visible_label=excluded.visible_label,
              status='pending',
              dispatch_run_id='',
              dispatch_status=''
            """,
            (
                job_ref,
                participant["agentId"],
                participant["accountId"],
                participant["role"],
                str(participant.get("visibleLabel") or "").strip(),
            ),
        )
    conn.commit()

    row = get_job(conn, job_ref)
    emit(
        {
            "jobRef": job_ref,
            "status": status,
            "queuePosition": queue_position,
            "title": args.title,
            "groupPeerId": args.group_peer_id,
            **build_job_control_state(row),
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
    job = get_job(conn, args.job_ref)
    if not job:
        emit({"status": "job_missing", "jobRef": args.job_ref})
        return 2
    workflow = parse_workflow_json(job["workflow_json"]) if "workflow_json" in job.keys() else None
    if workflow and job["status"] != "active":
        emit({"status": "job_not_active", "jobRef": args.job_ref, "currentStatus": job["status"]})
        return 2
    expected_agent_id = job["waiting_for_agent_id"] if workflow else None
    if workflow and expected_agent_id and args.agent_id != expected_agent_id:
        return emit_workflow_out_of_order(args.job_ref, expected_agent_id, args.agent_id)

    completed_at = now_iso()
    existing = conn.execute(
        "SELECT account_id, role, visible_label, dispatch_run_id, dispatch_status FROM job_participants WHERE job_ref = ? AND agent_id = ?",
        (args.job_ref, args.agent_id),
    ).fetchone()
    account_id = args.account_id or (existing["account_id"] if existing and existing["account_id"] else "")
    role = args.role or (existing["role"] if existing and existing["role"] else "")
    explicit_visible_label = str(args.visible_label or (existing["visible_label"] if existing and existing["visible_label"] else "")).strip()
    if not account_id or not role:
        emit(
            {
                "status": "participant_identity_missing",
                "jobRef": args.job_ref,
                "agentId": args.agent_id,
                "error": "participant accountId and role are required",
            }
        )
        return 2
    if not explicit_visible_label:
        emit(
            {
                "status": "invalid_visible_label",
                "jobRef": args.job_ref,
                "agentId": args.agent_id,
                "error": "workflow participant visibleLabel snapshot is required"
                if workflow
                else "participant visibleLabel snapshot is required",
            }
        )
        return 2
    visible_label = explicit_visible_label
    dispatch_run_id = args.dispatch_run_id or (existing["dispatch_run_id"] if existing and existing["dispatch_run_id"] else "")
    dispatch_status = args.dispatch_status or (existing["dispatch_status"] if existing and existing["dispatch_status"] else "accepted")
    conn.execute(
        """
        INSERT INTO job_participants (
          job_ref, agent_id, account_id, role, visible_label, status, dispatch_run_id, dispatch_status,
          progress_message_id, final_message_id, summary, completed_at
        ) VALUES (?, ?, ?, ?, ?, 'done', ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_ref, agent_id) DO UPDATE SET
          account_id=excluded.account_id,
          role=excluded.role,
          visible_label=excluded.visible_label,
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
            visible_label,
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
    next_action_payload = None
    if workflow:
        stages = workflow_stage_agent_ids(workflow)
        current_stage_index = stages.index(args.agent_id)
        if current_stage_index == len(stages) - 1:
            conn.execute(
                """
                UPDATE jobs
                SET current_stage_index = ?, waiting_for_agent_id = NULL, next_action = ?, updated_at = ?
                WHERE job_ref = ?
                """,
                (current_stage_index, "rollup", completed_at, args.job_ref),
            )
        else:
            next_agent_id = stages[current_stage_index + 1]
            conn.execute(
                """
                UPDATE jobs
                SET current_stage_index = ?, waiting_for_agent_id = ?, next_action = ?, updated_at = ?
                WHERE job_ref = ?
                """,
                (current_stage_index + 1, next_agent_id, "dispatch", completed_at, args.job_ref),
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
            "finalVisibleText": args.final_visible_text,
            "risks": args.risks,
            "actionItems": args.action_items,
            "dependencies": args.dependencies,
            "conflicts": args.conflicts,
        },
    )
    conn.commit()
    row = get_job(conn, args.job_ref)
    next_action_payload = next_action_payload_for_row(row) if row else None
    emit(
        {
            "jobRef": args.job_ref,
            "agentId": args.agent_id,
            "status": "done",
            "nextAction": next_action_payload,
        }
    )
    return 0


def cmd_mark_dispatch(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    job = get_job(conn, args.job_ref)
    if not job:
        emit({"status": "job_missing", "jobRef": args.job_ref})
        return 2
    workflow = parse_workflow_json(job["workflow_json"]) if "workflow_json" in job.keys() else None
    if workflow:
        if job["status"] != "active":
            emit({"status": "job_not_active", "jobRef": args.job_ref, "currentStatus": job["status"]})
            return 2
        expected_agent_id = job["waiting_for_agent_id"]
        if expected_agent_id and args.agent_id != expected_agent_id:
            return emit_workflow_out_of_order(args.job_ref, expected_agent_id, args.agent_id)
    existing = conn.execute(
        "SELECT visible_label FROM job_participants WHERE job_ref = ? AND agent_id = ?",
        (args.job_ref, args.agent_id),
    ).fetchone()
    explicit_visible_label = str(
        args.visible_label or (existing["visible_label"] if existing and existing["visible_label"] else "")
    ).strip()
    if not explicit_visible_label:
        emit(
            {
                "status": "invalid_visible_label",
                "jobRef": args.job_ref,
                "agentId": args.agent_id,
                "error": "workflow participant visibleLabel snapshot is required"
                if workflow
                else "participant visibleLabel snapshot is required",
            }
        )
        return 2

    dispatched_at = now_iso()
    conn.execute(
        """
        INSERT INTO job_participants (
          job_ref, agent_id, account_id, role, visible_label, status, dispatch_run_id, dispatch_status,
          progress_message_id, final_message_id, summary, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', '', '', NULL)
        ON CONFLICT(job_ref, agent_id) DO UPDATE SET
          account_id=excluded.account_id,
          role=excluded.role,
          visible_label=excluded.visible_label,
          status=excluded.status,
          dispatch_run_id=excluded.dispatch_run_id,
          dispatch_status=excluded.dispatch_status
        """,
        (
            args.job_ref,
            args.agent_id,
            args.account_id,
            args.role,
            explicit_visible_label,
            args.status,
            args.dispatch_run_id,
            args.dispatch_status,
        ),
    )
    conn.execute(
        "UPDATE jobs SET updated_at = ? WHERE job_ref = ?",
        (dispatched_at, args.job_ref),
    )
    if workflow:
        conn.execute(
            """
            UPDATE jobs
            SET next_action = ?, updated_at = ?, dispatch_attempt_count = dispatch_attempt_count + 1,
                last_control_error = ?
            WHERE job_ref = ?
            """,
            (
                "wait_worker",
                dispatched_at,
                args.dispatch_status if args.dispatch_status in {"timeout", "failed", "error"} else None,
                args.job_ref,
            ),
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
    row = get_job(conn, args.job_ref)
    emit(
        {
            "jobRef": args.job_ref,
            "agentId": args.agent_id,
            "status": args.status,
            "dispatchStatus": args.dispatch_status,
            "nextAction": next_action_payload_for_row(row) if row else None,
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
    snapshot_error = workflow_visible_snapshot_error(conn, active)
    payload = {
        "active": {
            "jobRef": active["job_ref"],
            "title": active["title"],
            "status": active["status"],
            "createdAt": active["created_at"],
            "updatedAt": active["updated_at"],
            "ageSeconds": job_age_seconds(active),
            "readyToRollup": ready,
            "participants": participants,
            **build_job_control_state(active),
            **visible_snapshot_status_payload(snapshot_error),
            **stats,
        }
    }
    if snapshot_error:
        payload["status"] = "invalid_visible_label"
        payload["error"] = snapshot_error
    emit(payload)
    return 0


def cmd_get_job(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    row = get_job(conn, args.job_ref)
    if not row:
        emit({"job": None, "jobRef": args.job_ref})
        return 2
    ready, participants = job_ready_to_rollup(conn, args.job_ref)
    snapshot_error = workflow_visible_snapshot_error(conn, row)
    payload = {
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
            "stagePackets": build_stage_packets(
                conn,
                args.job_ref,
                parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None,
            ),
            **build_job_control_state(row),
            **visible_snapshot_status_payload(snapshot_error),
            **participant_stats(conn, args.job_ref),
        }
    }
    if snapshot_error:
        payload["status"] = "invalid_visible_label"
        payload["error"] = snapshot_error
    emit(payload)
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
    row = get_job(conn, args.job_ref)
    emit(
        {
            "jobRef": args.job_ref,
            "ready": ready,
            "participants": participants,
            "nextAction": next_action_payload_for_row(row) if row else None,
        }
    )
    return 0


def cmd_get_next_action(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    row = get_job(conn, args.job_ref)
    if not row:
        emit({"job": None, "jobRef": args.job_ref})
        return 2
    emit(
        {
            "jobRef": args.job_ref,
            "status": row["status"],
            "nextAction": next_action_payload_for_row(row),
            "currentStageIndex": int(row["current_stage_index"]) if row["current_stage_index"] is not None else None,
            "waitingForAgentId": row["waiting_for_agent_id"],
            "orchestratorVersion": row["orchestrator_version"] or None,
        }
    )
    return 0


def cmd_build_dispatch_payload(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    row = get_job(conn, args.job_ref)
    if not row:
        emit({"status": "job_missing", "jobRef": args.job_ref})
        return 2
    workflow = parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
    if not workflow:
        emit({"status": "workflow_missing", "jobRef": args.job_ref})
        return 2
    agent_id = str(args.agent_id or row["waiting_for_agent_id"] or "").strip()
    if not agent_id:
        emit({"status": "dispatch_agent_missing", "jobRef": args.job_ref})
        return 2
    participant = participant_map(conn, args.job_ref).get(agent_id)
    if participant is None:
        emit({"status": "dispatch_participant_missing", "jobRef": args.job_ref, "agentId": agent_id})
        return 2
    explicit_visible_label = str(participant["visible_label"] or "").strip()
    if not explicit_visible_label:
        emit(
            {
                "status": "invalid_visible_label",
                "jobRef": args.job_ref,
                "agentId": agent_id,
                "error": "workflow participant visibleLabel snapshot is required",
            }
        )
        return 2
    callback_session_key = str(row["hidden_main_session_key"] or "").strip() if "hidden_main_session_key" in row.keys() else ""
    if not callback_session_key:
        emit({"status": "callback_session_missing", "jobRef": args.job_ref, "agentId": agent_id})
        return 2
    visible_contract = worker_visible_contract(
        args.job_ref,
        agent_id,
        participant["role"],
        explicit_visible_label,
    )
    payload = {
        "jobRef": args.job_ref,
        "groupPeerId": row["group_peer_id"],
        "agentId": agent_id,
        "accountId": participant["account_id"],
        "role": participant["role"],
        "callbackSessionKey": callback_session_key,
        "mustSend": "progress,final,callback",
        **visible_contract,
        "title": row["title"],
        "requestText": row["request_text"] or row["title"],
        "packet": (
            "TASK_DISPATCH|"
            f"jobRef={args.job_ref}|"
            f"from={hidden_main_agent_id(callback_session_key)}|"
            f"to={agent_id}|"
            f"title={row['title']}|"
            f"request={row['request_text'] or row['title']}|"
            f"callbackSessionKey={callback_session_key}|"
            "mustSend=progress,final,callback|"
            f"progressTitle={visible_contract['progressTitle']}|"
            f"finalTitle={visible_contract['finalTitle']}|"
            f"callbackMustInclude={visible_contract['callbackMustInclude']}"
        ),
    }
    emit(payload)
    return 0


def cmd_build_visible_ack(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    row = get_job(conn, args.job_ref)
    if not row:
        emit({"status": "job_missing", "jobRef": args.job_ref})
        return 2
    delivery = visible_delivery_for_row(row)
    if not delivery:
        emit({"status": "entry_delivery_missing", "jobRef": args.job_ref})
        return 2
    snapshot_error = workflow_visible_snapshot_error(conn, row)
    if snapshot_error:
        emit({"status": "invalid_visible_label", "jobRef": args.job_ref, "error": snapshot_error})
        return 2
    emit(
        {
            "jobRef": args.job_ref,
            "kind": "ack",
            "delivery": delivery,
            "message": visible_message_text("ack", row, conn),
        }
    )
    return 0


def cmd_build_rollup_context(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    row = get_job(conn, args.job_ref)
    if not row:
        emit({"job": None, "jobRef": args.job_ref})
        return 2
    snapshot_error = workflow_visible_snapshot_error(conn, row)
    if snapshot_error:
        emit({"status": "invalid_visible_label", "jobRef": args.job_ref, "error": snapshot_error})
        return 2
    workflow = parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
    emit(
        {
            "jobRef": args.job_ref,
            "groupPeerId": row["group_peer_id"],
            "workflow": workflow,
            "stagePackets": build_stage_packets(conn, args.job_ref, workflow),
            "completionPackets": latest_completion_packets(conn, args.job_ref),
            "participants": {
                agent_id: {
                    "status": participant["status"],
                    "visibleLabel": participant_visible_label(participant, agent_id),
                    "summary": participant["summary"],
                    "progressMessageId": participant["progress_message_id"],
                    "finalMessageId": participant["final_message_id"],
                }
                for agent_id, participant in participant_map(conn, args.job_ref).items()
            },
        }
    )
    return 0


def cmd_build_rollup_visible_message(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    row = get_job(conn, args.job_ref)
    if not row:
        emit({"status": "job_missing", "jobRef": args.job_ref})
        return 2
    if flag_value(row["rollup_visible_sent"] if "rollup_visible_sent" in row.keys() else 0):
        emit({"status": "rollup_already_sent", "jobRef": args.job_ref, "messageId": row["rollup_visible_message_id"]})
        return 2
    if str(row["status"] or "") != "active":
        emit({"status": "job_not_active", "jobRef": args.job_ref, "currentStatus": row["status"]})
        return 2
    snapshot_error = workflow_visible_snapshot_error(conn, row)
    if snapshot_error:
        emit({"status": "invalid_visible_label", "jobRef": args.job_ref, "error": snapshot_error})
        return 2
    ready, _participants = job_ready_to_rollup(conn, args.job_ref)
    if not ready:
        emit({"status": "rollup_not_ready", "jobRef": args.job_ref})
        return 2
    workflow = parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
    completion_packets = latest_completion_packets(conn, args.job_ref)
    if workflow:
        missing_packets = [agent_id for agent_id in workflow_stage_agent_ids(workflow) if agent_id not in completion_packets]
        if missing_packets:
            emit(
                {
                    "status": "completion_packets_missing",
                    "jobRef": args.job_ref,
                    "missingAgentIds": missing_packets,
                }
            )
            return 2
    delivery = visible_delivery_for_row(row)
    if not delivery:
        emit({"status": "entry_delivery_missing", "jobRef": args.job_ref})
        return 2
    emit(
        {
            "jobRef": args.job_ref,
            "kind": "rollup",
            "delivery": delivery,
            "message": visible_message_text("rollup", row, conn),
            "completionPackets": completion_packets,
        }
    )
    return 0


def cmd_record_visible_message(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    row = get_job(conn, args.job_ref)
    if not row:
        emit({"status": "job_missing", "jobRef": args.job_ref})
        return 2
    recorded_at = now_iso()
    if args.kind == "ack":
        conn.execute(
            """
            UPDATE jobs
            SET ack_visible_sent = 1, ack_visible_message_id = ?, updated_at = ?
            WHERE job_ref = ?
            """,
            (args.message_id, recorded_at, args.job_ref),
        )
    else:
        conn.execute(
            """
            UPDATE jobs
            SET rollup_visible_sent = 1, rollup_visible_message_id = ?, updated_at = ?
            WHERE job_ref = ?
            """,
            (args.message_id, recorded_at, args.job_ref),
        )
    insert_event(
        conn,
        args.job_ref,
        "visible_message_recorded",
        "system",
        {
            "kind": args.kind,
            "messageId": args.message_id,
        },
    )
    conn.commit()
    row = get_job(conn, args.job_ref)
    emit(
        {
            "jobRef": args.job_ref,
            "kind": args.kind,
            "messageId": args.message_id,
            **build_job_control_state(row),
        }
    )
    return 0


def cmd_close_job(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    row = get_job(conn, args.job_ref)
    if not row:
        emit({"status": "job_missing", "jobRef": args.job_ref})
        return 2
    workflow = parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
    if args.status == "done" and workflow and not flag_value(row["rollup_visible_sent"] if "rollup_visible_sent" in row.keys() else 0):
        emit(
            {
                "status": "rollup_visible_message_required",
                "jobRef": args.job_ref,
            }
        )
        return 2
    closed_at = now_iso()
    conn.execute(
        """
        UPDATE jobs
        SET status = ?, updated_at = ?, closed_at = ?, next_action = NULL, waiting_for_agent_id = NULL
        WHERE job_ref = ?
        """,
        (args.status, closed_at, closed_at, args.job_ref),
    )
    insert_event(conn, args.job_ref, "job_closed", "system", {"status": args.status})
    latest = conn.execute("SELECT * FROM jobs WHERE job_ref = ?", (args.job_ref,)).fetchone()
    if latest and latest["group_peer_id"]:
        promote_next_queued_job(conn, latest["group_peer_id"], closed_at)
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
    snapshot_error = workflow_visible_snapshot_error(conn, active)
    repair_status = workflow_repair_status(conn, active)

    if snapshot_error:
        emit(
            {
                "status": "invalid_visible_label",
                "jobRef": active["job_ref"],
                "ageSeconds": age_seconds,
                "participants": participants,
                "error": snapshot_error,
                **stats,
            }
        )
        return 0

    if repair_status:
        emit(
            {
                "ageSeconds": age_seconds,
                "participants": participants,
                **stats,
                **repair_status,
            }
        )
        return 0

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
        snapshot_error = workflow_visible_snapshot_error(conn, active)
        if not ready and not snapshot_error and age_seconds >= args.stale_seconds:
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
    snapshot_error = workflow_visible_snapshot_error(conn, active)
    repair_status = workflow_repair_status(conn, active)
    recover_payload = recovered
    if snapshot_error and recover_payload is None:
        recover_payload = {
            "status": "invalid_visible_label",
            "jobRef": active["job_ref"],
            "ageSeconds": job_age_seconds(active),
            "readyToRollup": ready,
            "participants": participants,
            "error": snapshot_error,
            **stats,
        }
    elif repair_status and recover_payload is None:
        recover_payload = {
            "ageSeconds": job_age_seconds(active),
            "readyToRollup": ready,
            "participants": participants,
            **stats,
            **repair_status,
        }
    emit(
        {
            "recover": recover_payload
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
                **visible_snapshot_status_payload(snapshot_error),
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
    snapshot_error = workflow_visible_snapshot_error(conn, active)
    repair_status = workflow_repair_status(conn, active)

    if snapshot_error:
        emit(
            {
                "status": "invalid_visible_label",
                "jobRef": active["job_ref"],
                "ageSeconds": age_seconds,
                "participants": participants,
                "error": snapshot_error,
                **stats,
            }
        )
        return 0

    if repair_status:
        emit(
            {
                "ageSeconds": age_seconds,
                "participants": participants,
                **stats,
                **repair_status,
            }
        )
        return 0

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

    start_workflow = sub.add_parser("start-job-with-workflow")
    start_workflow.add_argument("--group-peer-id", required=True)
    start_workflow.add_argument("--requested-by", default="")
    start_workflow.add_argument("--source-message-id", default="")
    start_workflow.add_argument("--title", required=True)
    start_workflow.add_argument("--request-text", default="")
    start_workflow.add_argument("--supervisor-visible-label", default="")
    start_workflow.add_argument("--entry-account-id", default="")
    start_workflow.add_argument("--entry-channel", default="")
    start_workflow.add_argument("--entry-target", default="")
    start_workflow.add_argument("--entry-delivery-json", default="")
    start_workflow.add_argument("--hidden-main-session-key", default="")
    start_workflow.add_argument("--participants-json", default="")
    start_workflow.add_argument("--workflow-json", required=True)
    start_workflow.add_argument("--orchestrator-version", default=V5_1_HARDENING)

    append = sub.add_parser("append-note")
    append.add_argument("--group-peer-id", required=True)
    append.add_argument("--sender-id", default="")
    append.add_argument("--text", required=True)

    dispatch = sub.add_parser("mark-dispatch")
    dispatch.add_argument("--job-ref", required=True)
    dispatch.add_argument("--agent-id", required=True)
    dispatch.add_argument("--account-id", required=True)
    dispatch.add_argument("--role", required=True)
    dispatch.add_argument("--visible-label", default="")
    dispatch.add_argument("--status", default="accepted", choices=["pending", "accepted", "running", "failed"])
    dispatch.add_argument("--dispatch-run-id", default="")
    dispatch.add_argument("--dispatch-status", default="")

    complete = sub.add_parser("mark-worker-complete")
    complete.add_argument("--job-ref", required=True)
    complete.add_argument("--agent-id", required=True)
    complete.add_argument("--account-id", default="")
    complete.add_argument("--role", default="")
    complete.add_argument("--visible-label", default="")
    complete.add_argument("--dispatch-run-id", default="")
    complete.add_argument("--dispatch-status", default="")
    complete.add_argument("--progress-message-id", required=True)
    complete.add_argument("--final-message-id", required=True)
    complete.add_argument("--summary", default="")
    complete.add_argument("--details", default="")
    complete.add_argument("--final-visible-text", default="")
    complete.add_argument("--risks", default="")
    complete.add_argument("--action-items", default="")
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

    next_action = sub.add_parser("get-next-action")
    next_action.add_argument("--job-ref", required=True)

    build_dispatch = sub.add_parser("build-dispatch-payload")
    build_dispatch.add_argument("--job-ref", required=True)
    build_dispatch.add_argument("--agent-id", default="")

    build_ack = sub.add_parser("build-visible-ack")
    build_ack.add_argument("--job-ref", required=True)

    rollup_context = sub.add_parser("build-rollup-context")
    rollup_context.add_argument("--job-ref", required=True)

    build_rollup = sub.add_parser("build-rollup-visible-message")
    build_rollup.add_argument("--job-ref", required=True)

    record_visible = sub.add_parser("record-visible-message")
    record_visible.add_argument("--job-ref", required=True)
    record_visible.add_argument("--kind", required=True, choices=["ack", "rollup"])
    record_visible.add_argument("--message-id", required=True)

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
        "start-job-with-workflow": cmd_start_job_with_workflow,
        "append-note": cmd_append_note,
        "mark-dispatch": cmd_mark_dispatch,
        "mark-worker-complete": cmd_mark_worker_complete,
        "get-active": cmd_get_active,
        "get-job": cmd_get_job,
        "list-queue": cmd_list_queue,
        "ready-to-rollup": cmd_ready_to_rollup,
        "get-next-action": cmd_get_next_action,
        "build-dispatch-payload": cmd_build_dispatch_payload,
        "build-visible-ack": cmd_build_visible_ack,
        "build-rollup-context": cmd_build_rollup_context,
        "build-rollup-visible-message": cmd_build_rollup_visible_message,
        "record-visible-message": cmd_record_visible_message,
        "close-job": cmd_close_job,
        "recover-stale": cmd_recover_stale,
        "begin-turn": cmd_begin_turn,
        "watchdog-tick": cmd_watchdog_tick,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
