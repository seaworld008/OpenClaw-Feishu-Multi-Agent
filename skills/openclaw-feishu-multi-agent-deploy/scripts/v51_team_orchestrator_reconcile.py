#!/usr/bin/env python3
"""Deterministic control-plane reconciler for V5.1 team orchestrator."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from core_job_registry import connect, get_active_job, get_job, init_db, workflow_repair_status
from core_session_hygiene import remove_session_keys

INLINE_WORKER_NO_REPLY_RETRY_LIMIT = 5


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def parse_last_json_blob(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        raise ValueError("command produced no output")
    starts = [idx for idx, ch in enumerate(stripped) if ch in "[{"]
    for start in reversed(starts):
        candidate = stripped[start:]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"unable to parse json output: {text}")


def run_command(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
    )


def parse_command_json(command: list[str], *, cwd: Path | None = None) -> tuple[subprocess.CompletedProcess[str], Any]:
    result = run_command(command, cwd=cwd)
    payload = parse_last_json_blob(result.stdout)
    return result, payload


def expand_path(raw: str, *, base: Path | None = None) -> Path:
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    if base is not None:
        return (base / path).resolve()
    return path.resolve()


def resolve_executable(raw: str) -> str:
    if "/" not in raw and not raw.startswith(".") and not raw.startswith("~"):
        if shutil.which(raw):
            return raw
        npm_global = Path.home() / ".npm-global" / "bin" / raw
        if npm_global.exists():
            return str(npm_global)
        return raw
    return str(expand_path(raw))


@dataclass
class PendingInbound:
    source_message_id: str
    requested_by: str
    request_text: str


@dataclass
class SessionTurn:
    user_text: str
    assistant_text: str | None


@dataclass
class HiddenMainPacket:
    packet: dict[str, str]
    valid: bool
    error: str | None = None


def resolve_session_transcript_path(sessions_dir: Path, session_key: str) -> Path | None:
    sessions_path = sessions_dir / "sessions.json"
    if not sessions_path.exists():
        return None
    try:
        sessions_map = json.loads(sessions_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    session_entry = sessions_map.get(session_key)
    if not isinstance(session_entry, dict):
        return None

    transcript_file = session_entry.get("sessionFile")
    session_id = str(session_entry.get("sessionId") or "").strip()
    if transcript_file:
        transcript_path = expand_path(str(transcript_file), base=sessions_dir)
    elif session_id:
        transcript_path = sessions_dir / f"{session_id}.jsonl"
    else:
        return None
    if not transcript_path.exists():
        return None
    return transcript_path


def load_session_entries(sessions_dir: Path, session_key: str) -> list[dict[str, Any]]:
    transcript_path = resolve_session_transcript_path(sessions_dir, session_key)
    if transcript_path is None:
        return []

    entries: list[dict[str, Any]] = []
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def extract_text_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            chunks.append(str(item.get("text") or ""))
    return "\n".join(chunk for chunk in chunks if chunk)


def iter_content_items(message: dict[str, Any]) -> list[dict[str, Any]]:
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [item for item in content if isinstance(item, dict)]


def load_session_turn(sessions_dir: Path, session_key: str) -> SessionTurn | None:
    turns = load_session_turns(sessions_dir, session_key)
    if not turns:
        return None
    return turns[-1]


def load_session_turns(sessions_dir: Path, session_key: str) -> list[SessionTurn]:
    entries = load_session_entries(sessions_dir, session_key)
    if not entries:
        return []
    last_user_text = ""
    last_assistant_text = None
    turns: list[SessionTurn] = []
    for entry in entries:
        if entry.get("type") != "message":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role == "user":
            if last_user_text:
                turns.append(SessionTurn(user_text=last_user_text, assistant_text=last_assistant_text))
            last_user_text = extract_text_content(message)
            last_assistant_text = None
        elif role == "assistant" and last_user_text:
            last_assistant_text = extract_text_content(message).strip()
    if last_user_text:
        turns.append(SessionTurn(user_text=last_user_text, assistant_text=last_assistant_text))
    return turns


def parse_pending_inbound(raw_text: str) -> PendingInbound | None:
    lines = raw_text.splitlines()
    body_start = None
    source_message_id = ""
    for idx, line in enumerate(lines):
        line = line.rstrip()
        if line.startswith("[message_id: ") and line.endswith("]"):
            source_message_id = line[len("[message_id: ") : -1].strip()
            body_start = idx + 1
            break
    if body_start is None or body_start >= len(lines):
        return None
    first_body_line = lines[body_start]
    if ": " not in first_body_line:
        return None
    requested_by, first_line = first_body_line.split(": ", 1)
    body_lines = [first_line, *lines[body_start + 1 :]]
    request_text = "\n".join(body_lines).strip()
    if not source_message_id or not request_text:
        return None
    return PendingInbound(
        source_message_id=source_message_id,
        requested_by=requested_by.strip() or "unknown",
        request_text=request_text,
    )


def parse_pipe_packet(raw_text: str, prefix: str) -> dict[str, str] | None:
    marker = f"{prefix}|"
    start = raw_text.find(marker)
    if start < 0:
        return None
    payload = raw_text[start:]
    packet: dict[str, str] = {"kind": prefix}
    for part in payload.split("|")[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        packet[key] = value.strip()
    return packet


def is_non_actionable_request(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return True
    upper = normalized.upper()
    return upper in {"WARMUP", "HEARTBEAT", "HEARTBEAT_OK", "PING", "PONG"}


def load_manifest_team(manifest_path: Path, team_key: str) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    teams = manifest.get("teams")
    if not isinstance(teams, list):
        raise ValueError("manifest.teams must be a list")
    for team in teams:
        if isinstance(team, dict) and str(team.get("teamKey")) == team_key:
            return team
    raise ValueError(f"team not found in manifest: {team_key}")


def resolve_registry_script(team: dict[str, Any], manifest_path: Path) -> Path:
    raw = str(team["runtime"]["controlPlane"]["registryScript"])
    return expand_path(raw, base=manifest_path.parent)


def registry_command(
    team: dict[str, Any],
    manifest_path: Path,
    *args: str,
) -> tuple[subprocess.CompletedProcess[str], Any]:
    registry_script = resolve_registry_script(team, manifest_path)
    db_path = expand_path(str(team["runtime"]["dbPath"]), base=manifest_path.parent)
    return parse_command_json(["python3", str(registry_script), "--db", str(db_path), *args])


def openclaw_command(
    openclaw_bin: Path,
    *args: str,
) -> tuple[subprocess.CompletedProcess[str], Any]:
    return parse_command_json([str(openclaw_bin), *args])


def extract_message_id(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("messageId", "message_id"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        for value in payload.values():
            found = extract_message_id(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = extract_message_id(item)
            if found:
                return found
    return ""


def extract_message_id_from_tool_result(message: dict[str, Any]) -> str:
    found = extract_message_id(message.get("details"))
    if found:
        return found
    found = extract_message_id(message)
    if found:
        return found

    content = message.get("content")
    if not isinstance(content, list):
        return ""
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "text":
            continue
        raw_text = str(item.get("text") or "").strip()
        if not raw_text:
            continue
        try:
            parsed = parse_last_json_blob(raw_text)
        except ValueError:
            continue
        found = extract_message_id(parsed)
        if found:
            return found
    return ""


def summarize_worker_output(text: str) -> str:
    summary = text.strip()
    if not summary or summary == "NO_REPLY":
        return ""
    if summary.startswith("[[reply_to_current]]"):
        summary = summary[len("[[reply_to_current]]") :].strip()
    if len(summary) > 120:
        summary = summary[:120].rstrip() + "..."
    return summary


def job_exists_for_source_message(conn: sqlite3.Connection, source_message_id: str) -> bool:
    row = conn.execute(
        "SELECT job_ref FROM jobs WHERE source_message_id = ? LIMIT 1",
        (source_message_id,),
    ).fetchone()
    return row is not None


def latest_pending_inbound(team: dict[str, Any], openclaw_home: Path, conn: sqlite3.Connection) -> PendingInbound | None:
    supervisor_agent_id = str(team["supervisor"]["agentId"])
    supervisor_session_key = str(team["runtime"]["sessionKeys"]["supervisorGroup"])
    sessions_dir = openclaw_home / "agents" / supervisor_agent_id / "sessions"
    turn = load_session_turn(sessions_dir, supervisor_session_key)
    if turn is None or turn.assistant_text != "NO_REPLY":
        return None
    pending = parse_pending_inbound(turn.user_text)
    if pending is None:
        return None
    if is_non_actionable_request(pending.request_text):
        return None
    if job_exists_for_source_message(conn, pending.source_message_id):
        return None
    return pending


def current_worker_main_no_reply(team: dict[str, Any], openclaw_home: Path, row: sqlite3.Row) -> bool:
    agent_id = str(row["waiting_for_agent_id"] or "").strip()
    if not agent_id or str(row["next_action"] or "").strip() != "wait_worker":
        return False

    sessions_dir = openclaw_home / "agents" / agent_id / "sessions"
    turn = load_session_turn(sessions_dir, f"agent:{agent_id}:main")
    if turn is None:
        return False
    return bool(turn.user_text) and f"TASK_DISPATCH|jobRef={row['job_ref']}|" in turn.user_text and turn.assistant_text == "NO_REPLY"


def placeholder_message_id(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"", "pending", "placeholder_progress_id", "placeholder_final_id", "placeholder", "processing", "none", "null", "sent"}:
        return True
    if "pending" in normalized or "placeholder" in normalized:
        return True
    if normalized.startswith("<") and normalized.endswith(">"):
        return True
    return False


def hidden_main_completion_packet(
    team: dict[str, Any],
    openclaw_home: Path,
    row: sqlite3.Row,
    conn: sqlite3.Connection,
) -> HiddenMainPacket | None:
    if str(row["next_action"] or "").strip() != "wait_worker":
        return None

    supervisor_agent_id = str(team["supervisor"]["agentId"])
    main_session_key = str(team["runtime"]["sessionKeys"].get("supervisorMain") or team["runtime"]["hiddenMainSessionKey"])
    turns = load_session_turns(openclaw_home / "agents" / supervisor_agent_id / "sessions", main_session_key)
    if not turns:
        return None

    latest_invalid: HiddenMainPacket | None = None
    for turn in reversed(turns):
        packet = parse_pipe_packet(turn.user_text, "COMPLETE_PACKET")
        if not packet or packet.get("jobRef") != str(row["job_ref"]):
            continue

        agent_id = str(packet.get("from") or packet.get("agent") or "").strip()
        if not agent_id:
            if latest_invalid is None:
                latest_invalid = HiddenMainPacket(packet=packet, valid=False, error="missing_agent_id")
            continue
        if agent_id != str(row["waiting_for_agent_id"] or "").strip():
            continue

        participant = conn.execute(
            "SELECT agent_id FROM job_participants WHERE job_ref = ? AND agent_id = ? LIMIT 1",
            (row["job_ref"], agent_id),
        ).fetchone()
        if participant is None:
            if latest_invalid is None:
                latest_invalid = HiddenMainPacket(packet=packet, valid=False, error="participant_missing")
            continue

        status = str(packet.get("status") or "").strip().lower()
        if status and status not in {"completed", "done", "ok", "success"}:
            if latest_invalid is None:
                latest_invalid = HiddenMainPacket(packet=packet, valid=False, error="invalid_status")
            continue

        progress_message_id = str(packet.get("progressMessageId") or "").strip()
        final_message_id = str(packet.get("finalMessageId") or "").strip()
        if placeholder_message_id(progress_message_id):
            if latest_invalid is None:
                latest_invalid = HiddenMainPacket(packet=packet, valid=False, error="invalid_progress_message_id")
            continue
        if placeholder_message_id(final_message_id):
            if latest_invalid is None:
                latest_invalid = HiddenMainPacket(packet=packet, valid=False, error="invalid_final_message_id")
            continue

        summary = str(packet.get("summary") or "").strip()
        if not summary or summary.lower() == "processing":
            if latest_invalid is None:
                latest_invalid = HiddenMainPacket(packet=packet, valid=False, error="invalid_summary")
            continue

        return HiddenMainPacket(packet=packet, valid=True)

    return latest_invalid


def recover_hidden_main_packet_from_worker_transcript(
    openclaw_home: Path,
    row: sqlite3.Row,
    packet: HiddenMainPacket,
) -> HiddenMainPacket | None:
    if packet.valid or packet.error not in {
        "invalid_progress_message_id",
        "invalid_final_message_id",
        "invalid_summary",
    }:
        return None

    agent_id = str(row["waiting_for_agent_id"] or "").strip()
    if not agent_id:
        return None

    sessions_dir = openclaw_home / "agents" / agent_id / "sessions"
    entries = load_session_entries(sessions_dir, f"agent:{agent_id}:main")
    if not entries:
        return None

    dispatch_marker = f"TASK_DISPATCH|jobRef={row['job_ref']}|"
    in_current_dispatch = False
    message_ids: list[str] = []
    last_assistant_text = ""
    visible_messages = extract_worker_visible_messages(entries, dispatch_marker)
    for entry in entries:
        if entry.get("type") != "message":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "")
        if role == "user":
            text = extract_text_content(message)
            if dispatch_marker in text:
                in_current_dispatch = True
                message_ids = []
                last_assistant_text = ""
                continue
            if in_current_dispatch:
                break
            continue
        if not in_current_dispatch:
            continue

        if role == "toolResult" and str(message.get("toolName") or "") == "message":
            message_id = extract_message_id_from_tool_result(message)
            if message_id and not placeholder_message_id(message_id) and message_id not in message_ids:
                message_ids.append(message_id)
            continue

        if role == "assistant":
            assistant_text = extract_text_content(message).strip()
            if assistant_text:
                last_assistant_text = assistant_text

    if len(message_ids) < 2:
        return None

    recovered_packet = dict(packet.packet)
    recovered_packet["progressMessageId"] = message_ids[0]
    recovered_packet["finalMessageId"] = message_ids[1]
    summary = str(recovered_packet.get("summary") or "").strip()
    if not summary or summary.lower() == "processing":
        summary = summarize_worker_output(last_assistant_text)
    if not summary:
        summary = "已通过 worker transcript 恢复真实消息回调并继续团队流程。"
    recovered_packet["summary"] = summary
    if len(visible_messages) >= 2:
        recovered_packet["finalVisibleText"] = visible_messages[1]
    recovered_packet.setdefault("from", agent_id)
    recovered_packet.setdefault("status", "completed")
    return HiddenMainPacket(packet=recovered_packet, valid=True)


def extract_completion_packet_from_worker_toolcall(
    message: dict[str, Any],
    job_ref: str,
    agent_id: str,
) -> dict[str, str] | None:
    for item in iter_content_items(message):
        if item.get("type") != "toolCall" or str(item.get("name") or "") != "sessions_send":
            continue
        arguments = item.get("arguments")
        if not isinstance(arguments, dict):
            continue
        raw_message = str(arguments.get("message") or "").strip()
        packet = parse_pipe_packet(raw_message, "COMPLETE_PACKET")
        if not packet or packet.get("jobRef") != job_ref:
            continue
        packet_agent_id = str(packet.get("from") or packet.get("agent") or "").strip()
        if packet_agent_id and packet_agent_id != agent_id:
            continue
        return packet
    return None


def extract_worker_visible_messages(entries: list[dict[str, Any]], dispatch_marker: str) -> list[str]:
    in_current_dispatch = False
    visible_messages: list[str] = []
    for entry in entries:
        if entry.get("type") != "message":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "")
        if role == "user":
            text = extract_text_content(message)
            if dispatch_marker in text:
                in_current_dispatch = True
                visible_messages = []
                continue
            if in_current_dispatch:
                break
            continue
        if not in_current_dispatch or role != "assistant":
            continue
        for item in iter_content_items(message):
            if item.get("type") != "toolCall" or str(item.get("name") or "") != "message":
                continue
            arguments = item.get("arguments")
            if not isinstance(arguments, dict):
                continue
            raw_message = str(arguments.get("message") or "").strip()
            if raw_message:
                visible_messages.append(raw_message)
    return visible_messages


def latest_worker_final_visible_text(openclaw_home: Path, agent_id: str, job_ref: str) -> str:
    sessions_dir = openclaw_home / "agents" / agent_id / "sessions"
    entries = load_session_entries(sessions_dir, f"agent:{agent_id}:main")
    if not entries:
        return ""
    visible_messages = extract_worker_visible_messages(entries, f"TASK_DISPATCH|jobRef={job_ref}|")
    if len(visible_messages) < 2:
        return ""
    return visible_messages[1]


def worker_transcript_completion_packet(
    openclaw_home: Path,
    row: sqlite3.Row,
) -> HiddenMainPacket | None:
    agent_id = str(row["waiting_for_agent_id"] or "").strip()
    if not agent_id:
        return None

    sessions_dir = openclaw_home / "agents" / agent_id / "sessions"
    entries = load_session_entries(sessions_dir, f"agent:{agent_id}:main")
    if not entries:
        return None

    dispatch_marker = f"TASK_DISPATCH|jobRef={row['job_ref']}|"
    in_current_dispatch = False
    message_ids: list[str] = []
    latest_packet: dict[str, str] | None = None
    last_assistant_text = ""
    visible_messages = extract_worker_visible_messages(entries, dispatch_marker)

    for entry in entries:
        if entry.get("type") != "message":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "")
        if role == "user":
            text = extract_text_content(message)
            if dispatch_marker in text:
                in_current_dispatch = True
                message_ids = []
                latest_packet = None
                last_assistant_text = ""
                continue
            if in_current_dispatch:
                break
            continue
        if not in_current_dispatch:
            continue

        if role == "toolResult" and str(message.get("toolName") or "") == "message":
            message_id = extract_message_id_from_tool_result(message)
            if message_id and not placeholder_message_id(message_id) and message_id not in message_ids:
                message_ids.append(message_id)
            continue

        if role != "assistant":
            continue

        packet = extract_completion_packet_from_worker_toolcall(message, str(row["job_ref"]), agent_id)
        if packet is not None:
            latest_packet = packet

        assistant_text = extract_text_content(message).strip()
        if assistant_text:
            last_assistant_text = assistant_text

    if latest_packet is None:
        return None

    recovered_packet = dict(latest_packet)
    progress_message_id = str(recovered_packet.get("progressMessageId") or "").strip()
    final_message_id = str(recovered_packet.get("finalMessageId") or "").strip()

    if placeholder_message_id(progress_message_id):
        if len(message_ids) < 1:
            return None
        recovered_packet["progressMessageId"] = message_ids[0]

    if placeholder_message_id(final_message_id):
        if len(message_ids) < 2:
            return None
        recovered_packet["finalMessageId"] = message_ids[1]

    summary = str(recovered_packet.get("summary") or "").strip()
    if not summary or summary.lower() == "processing":
        summary = summarize_worker_output(last_assistant_text)
    if not summary:
        summary = "已通过 worker transcript 合成有效回调并继续团队流程。"
    recovered_packet["summary"] = summary
    if len(visible_messages) >= 2:
        recovered_packet["finalVisibleText"] = visible_messages[1]
    recovered_packet.setdefault("from", agent_id)
    recovered_packet.setdefault("status", "completed")
    return HiddenMainPacket(packet=recovered_packet, valid=True)


def derive_job_title(request_text: str) -> str:
    first_line = request_text.splitlines()[0].strip()
    first_line = first_line.lstrip("@")
    if len(first_line) > 48:
        return first_line[:48].rstrip() + "..."
    return first_line or "团队协作任务"


def participants_payload(team: dict[str, Any]) -> list[dict[str, str]]:
    participants: list[dict[str, str]] = []
    for worker in team.get("workers", []):
        participants.append(
            {
                "agentId": str(worker["agentId"]),
                "accountId": str(worker["accountId"]),
                "role": str(worker.get("role") or worker.get("responsibility") or worker["agentId"]),
                "visibleLabel": str(worker.get("visibleLabel") or ""),
            }
        )
    return participants


def start_job_from_inbound(team: dict[str, Any], manifest_path: Path, inbound: PendingInbound) -> Any:
    runtime = team["runtime"]
    _result, payload = registry_command(
        team,
        manifest_path,
        "start-job-with-workflow",
        "--group-peer-id",
        str(team["group"]["peerId"]),
        "--requested-by",
        inbound.requested_by,
        "--source-message-id",
        inbound.source_message_id,
        "--title",
        derive_job_title(inbound.request_text),
        "--request-text",
        inbound.request_text,
        "--supervisor-visible-label",
        str(team.get("supervisor", {}).get("visibleLabel") or ""),
        "--entry-account-id",
        str(runtime["entryAccountId"]),
        "--entry-channel",
        str(runtime["entryChannel"]),
        "--entry-target",
        str(runtime["entryTarget"]),
        "--hidden-main-session-key",
        str(runtime["hiddenMainSessionKey"]),
        "--workflow-json",
        json.dumps(team["workflow"], ensure_ascii=False),
        "--participants-json",
        json.dumps(participants_payload(team), ensure_ascii=False),
    )
    return payload


def db_and_active_job(team: dict[str, Any], manifest_path: Path) -> tuple[sqlite3.Connection, sqlite3.Row | None]:
    db_path = expand_path(str(team["runtime"]["dbPath"]), base=manifest_path.parent)
    conn = connect(db_path)
    init_db(conn)
    return conn, get_active_job(conn, str(team["group"]["peerId"]))


def append_delivery_fields(packet: str, payload: dict[str, Any]) -> str:
    suffixes = {
        "channel": payload.get("delivery", {}).get("channel") or "feishu",
        "accountId": payload.get("delivery", {}).get("accountId") or payload.get("accountId"),
        "target": payload.get("delivery", {}).get("target") or f"chat:{payload.get('groupPeerId')}",
        "groupPeerId": payload.get("groupPeerId"),
    }
    output = packet
    for key, value in suffixes.items():
        if value and f"{key}=" not in output:
            output += f"|{key}={value}"
    return output


def reset_agent_main_session(openclaw_home: Path, agent_id: str) -> list[dict]:
    return remove_session_keys(
        openclaw_home,
        [(agent_id, f"agent:{agent_id}:main")],
        delete_transcripts=True,
        dry_run=False,
    )


def consume_hidden_main_completion_packet(
    team: dict[str, Any],
    manifest_path: Path,
    openclaw_home: Path,
    openclaw_bin: Path,
    row: sqlite3.Row,
    conn: sqlite3.Connection,
    packet: HiddenMainPacket,
) -> int:
    agent_id = str(packet.packet.get("from") or packet.packet.get("agent") or "").strip()
    participant = conn.execute(
        """
        SELECT account_id, role
        FROM job_participants
        WHERE job_ref = ? AND agent_id = ?
        LIMIT 1
        """,
        (row["job_ref"], agent_id),
    ).fetchone()
    if participant is None:
        emit({"status": "callback_participant_missing", "jobRef": row["job_ref"], "agentId": agent_id})
        return 2
    final_visible_text = str(packet.packet.get("finalVisibleText") or packet.packet.get("final_visible_text") or "").strip()
    if not final_visible_text:
        final_visible_text = latest_worker_final_visible_text(openclaw_home, agent_id, str(row["job_ref"]))

    registry_command(
        team,
        manifest_path,
        "mark-worker-complete",
        "--job-ref",
        row["job_ref"],
        "--agent-id",
        agent_id,
        "--account-id",
        str(participant["account_id"]),
        "--role",
        str(participant["role"]),
        "--progress-message-id",
        str(packet.packet["progressMessageId"]),
        "--final-message-id",
        str(packet.packet["finalMessageId"]),
        "--summary",
        str(packet.packet.get("summary") or ""),
        "--details",
        str(packet.packet.get("details") or ""),
        "--final-visible-text",
        final_visible_text,
        "--risks",
        str(packet.packet.get("risks") or ""),
        "--action-items",
        str(packet.packet.get("actionItems") or packet.packet.get("action_items") or ""),
        "--dependencies",
        str(packet.packet.get("dependencies") or ""),
        "--conflicts",
        str(packet.packet.get("conflicts") or ""),
    )

    refreshed = get_job(conn, str(row["job_ref"]))
    if refreshed is None:
        emit({"status": "job_missing_after_callback", "jobRef": row["job_ref"]})
        return 2
    repair_status = workflow_repair_status(conn, refreshed)
    if repair_status and repair_status["status"] == "needs_dispatch_reconcile":
        return reconcile_dispatch(team, manifest_path, openclaw_home, openclaw_bin, str(refreshed["job_ref"]))
    if repair_status and repair_status["status"] == "needs_rollup_reconcile":
        return reconcile_rollup(team, manifest_path, openclaw_bin, str(refreshed["job_ref"]))

    emit(
        {
            "status": "callback_consumed",
            "jobRef": refreshed["job_ref"],
            "agentId": agent_id,
            "nextAction": str(refreshed["next_action"] or ""),
        }
    )
    return 0


def reconcile_dispatch(
    team: dict[str, Any],
    manifest_path: Path,
    openclaw_home: Path,
    openclaw_bin: Path,
    job_ref: str | None,
    *,
    force: bool = False,
) -> int:
    conn, active = db_and_active_job(team, manifest_path)
    try:
        row = get_job(conn, job_ref) if job_ref else active
        if row is None:
            emit({"status": "job_missing", "jobRef": job_ref})
            return 2
        repair_status = workflow_repair_status(conn, row)
        if not force and (not repair_status or repair_status["status"] != "needs_dispatch_reconcile"):
            emit({"status": "dispatch_not_needed", "jobRef": row["job_ref"]})
            return 0

        ack_sent = bool(repair_status.get("ackVisibleSent")) if repair_status else bool(row["ack_visible_sent"])
        ack_message_id = ""
        if not ack_sent:
            _ack_result, ack_payload = registry_command(team, manifest_path, "build-visible-ack", "--job-ref", row["job_ref"])
            delivery = ack_payload["delivery"]
            _send_result, send_payload = openclaw_command(
                openclaw_bin,
                "message",
                "send",
                "--channel",
                str(delivery["channel"]),
                "--account",
                str(delivery["accountId"]),
                "--target",
                str(delivery["target"]),
                "--message",
                str(ack_payload["message"]),
                "--json",
            )
            ack_message_id = extract_message_id(send_payload)
            if not ack_message_id:
                emit({"status": "ack_message_id_missing", "jobRef": row["job_ref"], "sendResult": send_payload})
                return 2
            registry_command(
                team,
                manifest_path,
                "record-visible-message",
                "--job-ref",
                row["job_ref"],
                "--kind",
                "ack",
                "--message-id",
                ack_message_id,
            )

        _dispatch_result, dispatch_payload = registry_command(team, manifest_path, "build-dispatch-payload", "--job-ref", row["job_ref"])
        dispatch_packet = append_delivery_fields(str(dispatch_payload["packet"]), dispatch_payload)
        worker_session_reset = reset_agent_main_session(openclaw_home, str(dispatch_payload["agentId"]))
        _agent_result, agent_payload = openclaw_command(
            openclaw_bin,
            "agent",
            "--agent",
            str(dispatch_payload["agentId"]),
            "--message",
            dispatch_packet,
            "--json",
        )
        if str(agent_payload.get("status")) != "ok":
            emit({"status": "dispatch_agent_failed", "jobRef": row["job_ref"], "agentResult": agent_payload})
            return 2

        dispatch_run_id = str(agent_payload.get("runId") or f"run-{dispatch_payload['agentId']}")
        registry_command(
            team,
            manifest_path,
            "mark-dispatch",
            "--job-ref",
            row["job_ref"],
            "--agent-id",
            str(dispatch_payload["agentId"]),
            "--account-id",
            str(dispatch_payload["accountId"]),
            "--role",
            str(dispatch_payload["role"]),
            "--dispatch-run-id",
            dispatch_run_id,
            "--dispatch-status",
            "accepted",
        )

        _details_result, details_payload = registry_command(team, manifest_path, "get-job", "--job-ref", row["job_ref"])
        emit(
            {
                "status": "dispatch_reconciled",
                "jobRef": row["job_ref"],
                "agentId": dispatch_payload["agentId"],
                "ackVisibleSent": details_payload["job"]["ackVisibleSent"],
                "jobStarted": False,
                "workerMainSessionReset": worker_session_reset,
            }
        )
        return 0
    finally:
        conn.close()


def reconcile_rollup(team: dict[str, Any], manifest_path: Path, openclaw_bin: Path, job_ref: str | None) -> int:
    conn, active = db_and_active_job(team, manifest_path)
    try:
        row = get_job(conn, job_ref) if job_ref else active
        if row is None:
            emit({"status": "job_missing", "jobRef": job_ref})
            return 2
        if bool(row["rollup_visible_sent"]):
            if str(row["status"] or "") != "done":
                registry_command(
                    team,
                    manifest_path,
                    "close-job",
                    "--job-ref",
                    row["job_ref"],
                    "--status",
                    "done",
                )
            emit(
                {
                    "status": "rollup_already_recorded",
                    "jobRef": row["job_ref"],
                    "rollupVisibleSent": True,
                    "messageId": row["rollup_visible_message_id"],
                }
            )
            return 0
        if str(row["status"] or "") != "active":
            emit({"status": "rollup_not_needed", "jobRef": row["job_ref"], "currentStatus": row["status"]})
            return 0

        _rollup_result, rollup_payload = registry_command(
            team,
            manifest_path,
            "build-rollup-visible-message",
            "--job-ref",
            row["job_ref"],
        )
        delivery = rollup_payload["delivery"]
        _send_result, send_payload = openclaw_command(
            openclaw_bin,
            "message",
            "send",
            "--channel",
            str(delivery["channel"]),
            "--account",
            str(delivery["accountId"]),
            "--target",
            str(delivery["target"]),
            "--message",
            str(rollup_payload["message"]),
            "--json",
        )
        rollup_message_id = extract_message_id(send_payload)
        if not rollup_message_id:
            emit({"status": "rollup_message_id_missing", "jobRef": row["job_ref"], "sendResult": send_payload})
            return 2

        registry_command(
            team,
            manifest_path,
            "record-visible-message",
            "--job-ref",
            row["job_ref"],
            "--kind",
            "rollup",
            "--message-id",
            rollup_message_id,
        )
        registry_command(
            team,
            manifest_path,
            "close-job",
            "--job-ref",
            row["job_ref"],
            "--status",
            "done",
        )
        emit(
            {
                "status": "rollup_reconciled",
                "jobRef": row["job_ref"],
                "rollupVisibleSent": True,
                "messageId": rollup_message_id,
            }
        )
        return 0
    finally:
        conn.close()


def resume_job(team: dict[str, Any], manifest_path: Path, openclaw_home: Path, openclaw_bin: Path, stale_seconds: int) -> int:
    _watchdog_result, watchdog_payload = registry_command(
        team,
        manifest_path,
        "watchdog-tick",
        "--group-peer-id",
        str(team["group"]["peerId"]),
        "--stale-seconds",
        str(stale_seconds),
    )
    status = str(watchdog_payload.get("status") or "")

    if status == "needs_dispatch_reconcile":
        return reconcile_dispatch(team, manifest_path, openclaw_home, openclaw_bin, str(watchdog_payload["jobRef"]))
    if status == "needs_rollup_reconcile":
        return reconcile_rollup(team, manifest_path, openclaw_bin, str(watchdog_payload["jobRef"]))
    if status not in {"no_active_job", "stale_recovered", "active_ok"}:
        emit(watchdog_payload if isinstance(watchdog_payload, dict) else {"status": status or "noop"})
        return 0

    conn, active = db_and_active_job(team, manifest_path)
    try:
        bare_no_reply_retries = 0
        handled_invalid_hidden_packets: set[str] = set()
        while active is not None:
            repair_status = workflow_repair_status(conn, active)
            if repair_status and repair_status["status"] == "needs_dispatch_reconcile":
                job_ref = str(active["job_ref"])
                conn.close()
                dispatch_exit = reconcile_dispatch(team, manifest_path, openclaw_home, openclaw_bin, job_ref)
                if dispatch_exit != 0:
                    return dispatch_exit
                conn, active = db_and_active_job(team, manifest_path)
                continue
            if repair_status and repair_status["status"] == "needs_rollup_reconcile":
                return reconcile_rollup(team, manifest_path, openclaw_bin, str(active["job_ref"]))

            packet = hidden_main_completion_packet(team, openclaw_home, active, conn)
            if packet is not None:
                recovered_packet = recover_hidden_main_packet_from_worker_transcript(openclaw_home, active, packet)
                if recovered_packet is not None:
                    emit(
                        {
                            "status": "worker_transcript_callback_recovered",
                            "jobRef": active["job_ref"],
                            "agentId": active["waiting_for_agent_id"],
                            "progressMessageId": recovered_packet.packet["progressMessageId"],
                            "finalMessageId": recovered_packet.packet["finalMessageId"],
                        }
                    )
                    packet = recovered_packet
                elif not packet.valid:
                    promoted_packet = worker_transcript_completion_packet(openclaw_home, active)
                    if promoted_packet is not None:
                        emit(
                            {
                                "status": "worker_transcript_callback_promoted",
                                "jobRef": active["job_ref"],
                                "agentId": active["waiting_for_agent_id"],
                                "progressMessageId": promoted_packet.packet["progressMessageId"],
                                "finalMessageId": promoted_packet.packet["finalMessageId"],
                            }
                        )
                        packet = promoted_packet
            else:
                promoted_packet = worker_transcript_completion_packet(openclaw_home, active)
                if promoted_packet is not None:
                    emit(
                        {
                            "status": "worker_transcript_callback_promoted",
                            "jobRef": active["job_ref"],
                            "agentId": active["waiting_for_agent_id"],
                            "progressMessageId": promoted_packet.packet["progressMessageId"],
                            "finalMessageId": promoted_packet.packet["finalMessageId"],
                        }
                    )
                    packet = promoted_packet
            if packet is None:
                if current_worker_main_no_reply(team, openclaw_home, active):
                    if bare_no_reply_retries >= INLINE_WORKER_NO_REPLY_RETRY_LIMIT:
                        emit(
                            {
                                "status": "worker_no_reply_retry_exhausted",
                                "jobRef": active["job_ref"],
                                "agentId": active["waiting_for_agent_id"],
                                "reason": "worker_main_bare_no_reply",
                            }
                        )
                        return 2
                    bare_no_reply_retries += 1
                    job_ref = str(active["job_ref"])
                    agent_id = str(active["waiting_for_agent_id"] or "")
                    conn.close()
                    dispatch_exit = reconcile_dispatch(team, manifest_path, openclaw_home, openclaw_bin, job_ref, force=True)
                    if dispatch_exit != 0:
                        return dispatch_exit
                    conn, active = db_and_active_job(team, manifest_path)
                    emit(
                        {
                            "status": "worker_no_reply_retry_scheduled",
                            "jobRef": job_ref,
                            "agentId": agent_id,
                            "attempt": bare_no_reply_retries,
                            "limit": INLINE_WORKER_NO_REPLY_RETRY_LIMIT,
                        }
                    )
                    continue
                break
            if packet.valid:
                consume_exit = consume_hidden_main_completion_packet(
                    team,
                    manifest_path,
                    openclaw_home,
                    openclaw_bin,
                    active,
                    conn,
                    packet,
                )
                if consume_exit != 0:
                    return consume_exit
                conn.close()
                conn, active = db_and_active_job(team, manifest_path)
                continue
            packet_signature = json.dumps(packet.packet, ensure_ascii=False, sort_keys=True)
            if packet_signature in handled_invalid_hidden_packets:
                break
            handled_invalid_hidden_packets.add(packet_signature)
            if bare_no_reply_retries >= INLINE_WORKER_NO_REPLY_RETRY_LIMIT:
                emit(
                    {
                        "status": "worker_no_reply_retry_exhausted",
                        "jobRef": active["job_ref"],
                        "agentId": active["waiting_for_agent_id"],
                        "reason": packet.error or "invalid_hidden_main_packet",
                    }
                )
                return 2
            bare_no_reply_retries += 1
            job_ref = str(active["job_ref"])
            agent_id = str(active["waiting_for_agent_id"] or "")
            conn.close()
            dispatch_exit = reconcile_dispatch(team, manifest_path, openclaw_home, openclaw_bin, job_ref, force=True)
            if dispatch_exit != 0:
                return dispatch_exit
            conn, active = db_and_active_job(team, manifest_path)
            emit(
                {
                    "status": "worker_no_reply_retry_scheduled",
                    "jobRef": job_ref,
                    "agentId": agent_id,
                    "attempt": bare_no_reply_retries,
                    "limit": INLINE_WORKER_NO_REPLY_RETRY_LIMIT,
                }
            )
            continue

            if current_worker_main_no_reply(team, openclaw_home, active):
                if bare_no_reply_retries >= INLINE_WORKER_NO_REPLY_RETRY_LIMIT:
                    emit(
                        {
                            "status": "worker_no_reply_retry_exhausted",
                            "jobRef": active["job_ref"],
                            "agentId": active["waiting_for_agent_id"],
                            "reason": "worker_main_bare_no_reply",
                        }
                    )
                    return 2
                bare_no_reply_retries += 1
                job_ref = str(active["job_ref"])
                agent_id = str(active["waiting_for_agent_id"] or "")
                conn.close()
                dispatch_exit = reconcile_dispatch(team, manifest_path, openclaw_home, openclaw_bin, job_ref, force=True)
                if dispatch_exit != 0:
                    return dispatch_exit
                conn, active = db_and_active_job(team, manifest_path)
                emit(
                    {
                        "status": "worker_no_reply_retry_scheduled",
                        "jobRef": job_ref,
                        "agentId": agent_id,
                        "attempt": bare_no_reply_retries,
                        "limit": INLINE_WORKER_NO_REPLY_RETRY_LIMIT,
                    }
                )
                continue
            break
    finally:
        conn.close()

    conn, _active = db_and_active_job(team, manifest_path)
    try:
        pending = latest_pending_inbound(team, openclaw_home, conn)
    finally:
        conn.close()

    if pending is None:
        emit({"status": "no_pending_inbound_message", "teamKey": team["teamKey"]})
        return 0

    started_payload = start_job_from_inbound(team, manifest_path, pending)
    dispatch_exit = reconcile_dispatch(team, manifest_path, openclaw_home, openclaw_bin, str(started_payload["jobRef"]))
    if dispatch_exit != 0:
        return dispatch_exit
    emit(
        {
            "status": "dispatch_reconciled",
            "jobRef": started_payload["jobRef"],
            "jobStarted": True,
            "ackVisibleSent": True,
            "agentId": started_payload["waitingForAgentId"],
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--team-key", required=True)
    parser.add_argument("--openclaw-home", default="~/.openclaw")
    parser.add_argument("--openclaw-bin", default="openclaw")

    sub = parser.add_subparsers(dest="command", required=True)

    resume = sub.add_parser("resume-job")
    resume.add_argument("--stale-seconds", type=int, default=180)

    dispatch = sub.add_parser("reconcile-dispatch")
    dispatch.add_argument("--job-ref", default="")

    rollup = sub.add_parser("reconcile-rollup")
    rollup.add_argument("--job-ref", default="")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    manifest_path = expand_path(args.manifest)
    openclaw_home = expand_path(args.openclaw_home)
    openclaw_bin = resolve_executable(args.openclaw_bin)
    try:
        team = load_manifest_team(manifest_path, args.team_key)
    except (ValueError, FileNotFoundError) as exc:
        emit({"status": "invalid_manifest", "error": str(exc)})
        return 2

    try:
        if args.command == "resume-job":
            return resume_job(team, manifest_path, openclaw_home, openclaw_bin, args.stale_seconds)
        if args.command == "reconcile-dispatch":
            return reconcile_dispatch(team, manifest_path, openclaw_home, openclaw_bin, args.job_ref or None)
        if args.command == "reconcile-rollup":
            return reconcile_rollup(team, manifest_path, openclaw_bin, args.job_ref or None)
        emit({"status": "unsupported_command", "command": args.command})
        return 2
    except Exception as exc:  # pragma: no cover - surfaced via CLI output
        emit({"status": "reconcile_error", "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
