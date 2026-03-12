#!/usr/bin/env python3
"""Deterministic control-plane reconciler for V5.1 team orchestrator."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
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

from core_ingress_adapter import (
    claim_inbound_event,
    extract_inbound_event,
    find_unclaimed_inbound_event_for_team,
    persist_inbound_event,
)
from core_openclaw_adapter import OpenClawAdapter, SessionTarget
from core_outbox_sender import deliver_pending_messages, enqueue_visible_message
from core_job_registry import (
    connect,
    current_stage_participants,
    get_active_job,
    get_job,
    init_db,
    visible_delivery_for_row as registry_visible_delivery_for_row,
    visible_message_text as registry_visible_message_text,
    workflow_repair_status,
)
from core_runtime_store import RuntimeStore
from core_team_controller import TeamController
from core_worker_callback_sink import StructuredWorkerCallback, ingest_callback

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
    supervisor_spawned_session_keys: tuple[str, ...] = ()


@dataclass
class ReconcileLoopResult:
    exit_code: int
    status: str = "idle"


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


def team_lock_path(team: dict[str, Any], manifest_path: Path) -> Path:
    db_path = expand_path(str(team["runtime"]["dbPath"]), base=manifest_path.parent)
    return db_path.parent / "reconcile.lock"


def acquire_team_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def registry_command(
    team: dict[str, Any],
    manifest_path: Path,
    *args: str,
) -> tuple[subprocess.CompletedProcess[str], Any]:
    registry_script = resolve_registry_script(team, manifest_path)
    db_path = expand_path(str(team["runtime"]["dbPath"]), base=manifest_path.parent)
    return parse_command_json(["python3", str(registry_script), "--db", str(db_path), *args])


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


def latest_pending_inbound(team: dict[str, Any], adapter: OpenClawAdapter, conn: sqlite3.Connection) -> PendingInbound | None:
    supervisor_agent_id = str(team["supervisor"]["agentId"])
    supervisor_session_key = str(team["runtime"]["sessionKeys"]["supervisorGroup"])
    inbound_events = adapter.capture_inbound_events(
        agent_id=supervisor_agent_id,
        session_key=supervisor_session_key,
    )
    if not inbound_events:
        return None

    store = RuntimeStore(conn)
    candidates: dict[str, PendingInbound] = {}
    for captured_event in inbound_events:
        if is_non_actionable_request(captured_event.request_text):
            continue
        if job_exists_for_source_message(conn, captured_event.source_message_id):
            continue
        ingress_event = extract_inbound_event(
            team_key=str(team["teamKey"]),
            source_message_id=captured_event.source_message_id,
            canonical_target_id=str(team["group"]["peerId"]),
            request_text=captured_event.request_text,
            requested_by=captured_event.requested_by,
            mentioned_agent_id=supervisor_agent_id,
        )
        persist_inbound_event(store, ingress_event)
        candidates[ingress_event.source_message_id] = PendingInbound(
            source_message_id=ingress_event.source_message_id,
            requested_by=ingress_event.requested_by,
            request_text=ingress_event.request_text,
            supervisor_spawned_session_keys=captured_event.supervisor_spawned_session_keys,
        )

    pending_event = find_unclaimed_inbound_event_for_team(store, str(team["teamKey"]))
    if pending_event is None:
        return None
    if pending_event.source_message_id in candidates:
        return candidates[pending_event.source_message_id]
    return PendingInbound(
        source_message_id=pending_event.source_message_id,
        requested_by=pending_event.requested_by or "unknown",
        request_text=pending_event.request_text,
    )


def current_worker_main_no_reply(team: dict[str, Any], adapter: OpenClawAdapter, row: sqlite3.Row) -> bool:
    agent_id = str(row["waiting_for_agent_id"] or "").strip()
    if not agent_id or str(row["next_action"] or "").strip() != "wait_worker":
        return False

    entries = adapter.load_session_entries(agent_id=agent_id, session_key=f"agent:{agent_id}:main")
    if not entries:
        return False
    dispatch_entries = current_worker_dispatch_entries(entries, f"TASK_DISPATCH|jobRef={row['job_ref']}|")
    if not dispatch_entries:
        return False
    last_assistant_text = ""
    for entry in dispatch_entries:
        if entry.get("type") != "message":
            continue
        message = entry.get("message")
        if not isinstance(message, dict) or str(message.get("role") or "") != "assistant":
            continue
        assistant_text = extract_text_content(message).strip()
        if assistant_text:
            last_assistant_text = assistant_text
    return last_assistant_text == "NO_REPLY"


def current_stage_terminal_worker_retry_agents(
    team: dict[str, Any],
    adapter: OpenClawAdapter,
    conn: sqlite3.Connection,
    row: sqlite3.Row,
) -> list[str]:
    if str(row["next_action"] or "").strip() != "wait_worker":
        return []
    stage_index = int(row["current_stage_index"] or 0)
    participants = current_stage_participants(conn, row)
    if not participants:
        return []
    store = RuntimeStore(conn)
    retry_agents: list[str] = []
    for participant in participants:
        agent_id = str(participant["agent_id"] or "").strip()
        if not agent_id:
            continue
        if store.get_stage_callback(job_ref=str(row["job_ref"]), stage_index=stage_index, agent_id=agent_id) is not None:
            continue
        entries = adapter.load_session_entries(agent_id=agent_id, session_key=f"agent:{agent_id}:main")
        if not entries:
            continue
        dispatch_entries = current_worker_dispatch_entries(entries, f"TASK_DISPATCH|jobRef={row['job_ref']}|")
        if not dispatch_entries:
            continue
        last_assistant_text = ""
        for entry in dispatch_entries:
            if entry.get("type") != "message":
                continue
            message = entry.get("message")
            if not isinstance(message, dict) or str(message.get("role") or "") != "assistant":
                continue
            assistant_text = extract_text_content(message).strip()
            if assistant_text:
                last_assistant_text = assistant_text
        if last_assistant_text in {"NO_REPLY", "CALLBACK_OK"}:
            retry_agents.append(agent_id)
    return retry_agents


def structured_callback_from_worker_main(
    adapter: OpenClawAdapter,
    row: sqlite3.Row,
    *,
    team_key: str,
    stage_index: int,
    agent_id: str,
) -> StructuredWorkerCallback | None:
    entries = adapter.load_session_entries(agent_id=agent_id, session_key=f"agent:{agent_id}:main")
    if not entries:
        return None
    dispatch_entries = current_worker_dispatch_entries(entries, f"TASK_DISPATCH|jobRef={row['job_ref']}|")
    if not dispatch_entries:
        return None
    last_assistant_text = ""
    for entry in dispatch_entries:
        if entry.get("type") != "message":
            continue
        message = entry.get("message")
        if not isinstance(message, dict) or str(message.get("role") or "") != "assistant":
            continue
        assistant_text = extract_text_content(message).strip()
        if assistant_text:
            last_assistant_text = assistant_text
    if not last_assistant_text or last_assistant_text in {"NO_REPLY", "CALLBACK_OK"}:
        return None
    try:
        payload = parse_last_json_blob(last_assistant_text)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    if not any(key in payload for key in ("progressDraft", "finalDraft", "summary", "details", "risks", "actionItems")):
        return None
    return StructuredWorkerCallback(
        job_ref=str(row["job_ref"]),
        team_key=team_key,
        stage_index=stage_index,
        agent_id=agent_id,
        progress_draft=str(payload.get("progressDraft") or payload.get("progressText") or ""),
        final_draft=str(payload.get("finalDraft") or payload.get("finalText") or ""),
        summary=str(payload.get("summary") or ""),
        details=str(payload.get("details") or ""),
        risks=str(payload.get("risks") or ""),
        action_items=str(payload.get("actionItems") or payload.get("action_items") or ""),
        progress_message_id=str(payload.get("progressMessageId") or ""),
        final_message_id=str(payload.get("finalMessageId") or ""),
        final_visible_text=str(payload.get("finalVisibleText") or payload.get("finalDraft") or payload.get("finalText") or ""),
    )


def current_worker_dispatch_entries(entries: list[dict[str, Any]], dispatch_marker: str) -> list[dict[str, Any]]:
    dispatch_entries: list[dict[str, Any]] = []
    in_current_dispatch = False
    for entry in entries:
        if entry.get("type") != "message":
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "") == "user":
            text = extract_text_content(message)
            if dispatch_marker in text:
                in_current_dispatch = True
                dispatch_entries = [entry]
                continue
            if in_current_dispatch and "TASK_DISPATCH|" in text:
                break
        if in_current_dispatch:
            dispatch_entries.append(entry)
    return dispatch_entries


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
    db_path = expand_path(str(runtime["dbPath"]), base=manifest_path.parent)
    conn = connect(db_path)
    try:
        init_db(conn)
        store = RuntimeStore(conn)
        store.initialize()
        controller = TeamController(store=store)
        event = extract_inbound_event(
            team_key=str(team["teamKey"]),
            source_message_id=inbound.source_message_id,
            canonical_target_id=str(team["group"]["peerId"]),
            request_text=inbound.request_text,
            requested_by=inbound.requested_by,
            channel=str(runtime["entryChannel"]),
            account_id=str(runtime["entryAccountId"]),
            mentioned_agent_id=str(team["supervisor"]["agentId"]),
        )
        return controller.start_job(
            event=event,
            title=derive_job_title(inbound.request_text),
            workflow=team.get("workflow"),
            workflow_agents=participants_payload(team),
            supervisor_visible_label=str(team.get("supervisor", {}).get("visibleLabel") or "主管"),
            entry_delivery={
                "channel": str(runtime["entryChannel"]),
                "accountId": str(runtime["entryAccountId"]),
                "target": str(runtime["entryTarget"]),
            },
            hidden_main_session_key=str(runtime["hiddenMainSessionKey"]),
        )
    finally:
        conn.close()


def db_and_active_job(team: dict[str, Any], manifest_path: Path) -> tuple[sqlite3.Connection, sqlite3.Row | None]:
    db_path = expand_path(str(team["runtime"]["dbPath"]), base=manifest_path.parent)
    conn = connect(db_path)
    init_db(conn)
    return conn, get_active_job(conn, str(team["group"]["peerId"]))


def ensure_visible_message_enqueued(
    *,
    team: dict[str, Any],
    conn: sqlite3.Connection,
    store: RuntimeStore,
    row: sqlite3.Row,
    kind: str,
) -> dict[str, Any]:
    existing = store.get_outbound_message(
        team_key=str(team["teamKey"]),
        job_ref=row["job_ref"],
        message_kind=kind,
    )
    if existing is not None:
        return existing

    controller = TeamController(store=store)
    action = str(row["next_action"] or "").strip()
    if kind == "ack" and action == "ack_pending":
        controller.enqueue_ack(job_ref=row["job_ref"])
    elif kind == "rollup" and action == "rollup_pending":
        controller.enqueue_rollup(job_ref=row["job_ref"])
    else:
        payload = {
            "jobRef": row["job_ref"],
            "teamKey": str(team["teamKey"]),
            "kind": kind,
            "message": registry_visible_message_text(kind, row, conn),
            "delivery": registry_visible_delivery_for_row(row),
        }
        enqueue_visible_message(
            store,
            team_key=str(team["teamKey"]),
            job_ref=row["job_ref"],
            message_kind=kind,
            payload=payload,
        )

    created = store.get_outbound_message(
        team_key=str(team["teamKey"]),
        job_ref=row["job_ref"],
        message_kind=kind,
    )
    if created is None:
        raise RuntimeError(f"failed to enqueue {kind} visible message")
    return created


def deliver_team_visible_outbox(
    *,
    team: dict[str, Any],
    store: RuntimeStore,
    adapter: OpenClawAdapter,
    on_delivered,
    limit: int = 10,
) -> dict[str, Any]:
    return deliver_pending_messages(
        store,
        delivery_func=adapter_delivery_func(adapter),
        team_key=str(team["teamKey"]),
        limit=limit,
        on_delivered=on_delivered,
    )


def deliver_worker_publish_outbox(
    *,
    team: dict[str, Any],
    store: RuntimeStore,
    controller: TeamController,
    adapter: OpenClawAdapter,
    job_ref: str,
    stage_key: str,
    limit: int = 10,
) -> dict[str, Any]:
    def _on_delivered(sent_row: dict[str, Any], message_id: str) -> None:
        message_kind = str(sent_row["messageKind"])
        agent_id = str(sent_row["agentId"])
        if message_kind not in {"worker_progress", "worker_final"}:
            return
        controller.record_outbound_delivery(
            job_ref=job_ref,
            agent_id=agent_id,
            message_kind=message_kind,
            delivery_message_id=message_id,
        )
        payload = sent_row.get("payload") if isinstance(sent_row, dict) else None
        finalize_after_send = bool(isinstance(payload, dict) and payload.get("finalizeAfterSend"))
        if message_kind == "worker_final" or finalize_after_send:
            controller.mark_callback_published(
                job_ref=job_ref,
                stage_key=stage_key,
                agent_id=agent_id,
            )

    return deliver_pending_messages(
        store,
        delivery_func=adapter_delivery_func(adapter),
        team_key=str(team["teamKey"]),
        limit=limit,
        on_delivered=_on_delivered,
    )


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


def adapter_delivery_func(adapter: OpenClawAdapter):
    def _deliver(row: dict[str, Any]) -> Any:
        payload = row["payload"]
        delivery = payload["delivery"]
        return adapter.send_message(
            channel=str(delivery["channel"]),
            account_id=str(delivery["accountId"]),
            target=str(delivery["target"]),
            message=str(payload["message"]),
        )

    return _deliver


def reset_session_targets(adapter: OpenClawAdapter, targets: list[SessionTarget]) -> list[dict]:
    return adapter.inspect_or_reset_session(
        targets=targets,
        action="reset",
        delete_transcripts=True,
    )


def reset_supervisor_spawned_subagent_sessions(
    team: dict[str, Any],
    adapter: OpenClawAdapter,
    session_keys: tuple[str, ...],
) -> list[dict]:
    supervisor_agent_id = str(team["supervisor"]["agentId"])
    prefix = f"agent:{supervisor_agent_id}:subagent:"
    unique_keys: list[str] = []
    seen: set[str] = set()
    for session_key in session_keys:
        normalized = str(session_key or "").strip()
        if not normalized.startswith(prefix) or normalized in seen:
            continue
        seen.add(normalized)
        unique_keys.append(normalized)
    if not unique_keys:
        return []
    return reset_session_targets(
        adapter,
        [SessionTarget(agent_id=supervisor_agent_id, session_key=session_key) for session_key in unique_keys],
    )


def reconcile_dispatch(
    team: dict[str, Any],
    manifest_path: Path,
    adapter: OpenClawAdapter,
    job_ref: str | None,
    *,
    force: bool = False,
    agent_ids: list[str] | None = None,
) -> int:
    conn, active = db_and_active_job(team, manifest_path)
    try:
        row = get_job(conn, job_ref) if job_ref else active
        if row is None:
            emit({"status": "job_missing", "jobRef": job_ref})
            return 2
        store = RuntimeStore(conn)
        repair_status = workflow_repair_status(conn, row)
        if not force and (not repair_status or repair_status["status"] != "needs_dispatch_reconcile"):
            emit({"status": "dispatch_not_needed", "jobRef": row["job_ref"]})
            return 0

        ack_sent = bool(repair_status.get("ackVisibleSent")) if repair_status else bool(row["ack_visible_sent"])
        ack_message_id = ""
        if not ack_sent:
            ensure_visible_message_enqueued(
                team=team,
                conn=conn,
                store=store,
                row=row,
                kind="ack",
            )
            outbox_result = deliver_team_visible_outbox(
                team=team,
                store=store,
                adapter=adapter,
                limit=10,
                on_delivered=lambda sent_row, message_id: registry_command(
                    team,
                    manifest_path,
                    "record-visible-message",
                    "--job-ref",
                    sent_row["jobRef"],
                    "--kind",
                    str(sent_row["messageKind"]),
                    "--message-id",
                    message_id,
                ),
            )
            if outbox_result["deliveredCount"] < 1:
                emit({"status": "ack_delivery_missing", "jobRef": row["job_ref"], "outboxResult": outbox_result})
                return 2
            ack_message_id = str(outbox_result["results"][0]["deliveryMessageId"])

        controller = TeamController(store=store)
        current_action = str(row["next_action"] or "").strip()
        if force and current_action == "wait_worker":
            if agent_ids:
                dispatches = list(controller.redispatch_agents(job_ref=row["job_ref"], agent_ids=agent_ids)["dispatches"])
            else:
                dispatch_payload = controller.redispatch_current_stage(job_ref=row["job_ref"])["payload"]
                dispatches = [dispatch_payload]
        else:
            dispatch_plan = controller.dispatch_stage(job_ref=row["job_ref"])
            if dispatch_plan.get("mode") == "parallel":
                dispatches = list(dispatch_plan["dispatches"])
            else:
                dispatches = [dispatch_plan["payload"]]
        dispatch_results: list[dict[str, Any]] = []
        worker_session_reset: list[dict[str, Any]] = []
        for dispatch_payload in dispatches:
            dispatch_packet = append_delivery_fields(str(dispatch_payload["packet"]), dispatch_payload)
            provisional_run_id = f"run-{dispatch_payload['agentId']}"
            worker_session_reset.extend(
                reset_session_targets(
                    adapter,
                    [SessionTarget(agent_id=str(dispatch_payload["agentId"]), session_key=f"agent:{dispatch_payload['agentId']}:main")],
                )
            )
            agent_payload = adapter.invoke_agent(
                agent_id=str(dispatch_payload["agentId"]),
                message=dispatch_packet,
            )
            if str(agent_payload.get("status")) != "ok":
                emit({"status": "dispatch_agent_failed", "jobRef": row["job_ref"], "agentResult": agent_payload})
                return 2
            controller.record_dispatch_acceptance(
                job_ref=row["job_ref"],
                agent_id=str(dispatch_payload["agentId"]),
                dispatch_run_id=str(agent_payload.get("runId") or provisional_run_id),
                dispatch_status="accepted",
            )
            structured_callback = structured_callback_from_worker_main(
                adapter,
                row,
                team_key=str(team["teamKey"]),
                stage_index=int(dispatch_payload["stageIndex"]),
                agent_id=str(dispatch_payload["agentId"]),
            )
            if structured_callback is not None:
                ingest_callback(store=store, callback=structured_callback)
            dispatch_results.append(
                {
                    "agentId": str(dispatch_payload["agentId"]),
                    "dispatchRunId": str(agent_payload.get("runId") or provisional_run_id),
                }
            )

        supervisor_group_session_reset = reset_session_targets(
            adapter,
            [
                SessionTarget(
                    agent_id=str(team["supervisor"]["agentId"]),
                    session_key=str(team["runtime"]["sessionKeys"]["supervisorGroup"]),
                )
            ],
        )

        _details_result, details_payload = registry_command(team, manifest_path, "get-job", "--job-ref", row["job_ref"])
        emit(
            {
                "status": "dispatch_reconciled",
                "jobRef": row["job_ref"],
                "agentId": dispatch_results[0]["agentId"] if len(dispatch_results) == 1 else None,
                "agentIds": [item["agentId"] for item in dispatch_results],
                "dispatchRunId": dispatch_results[0]["dispatchRunId"] if len(dispatch_results) == 1 else None,
                "dispatches": dispatch_results,
                "ackVisibleSent": details_payload["job"]["ackVisibleSent"],
                "jobStarted": False,
                "workerMainSessionReset": worker_session_reset,
                "supervisorGroupSessionReset": supervisor_group_session_reset,
            }
        )
        return 0
    finally:
        conn.close()


def reconcile_rollup(team: dict[str, Any], manifest_path: Path, adapter: OpenClawAdapter, job_ref: str | None) -> int:
    conn, active = db_and_active_job(team, manifest_path)
    try:
        row = get_job(conn, job_ref) if job_ref else active
        if row is None:
            emit({"status": "job_missing", "jobRef": job_ref})
            return 2
        store = RuntimeStore(conn)
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

        ensure_visible_message_enqueued(
            team=team,
            conn=conn,
            store=store,
            row=row,
            kind="rollup",
        )
        outbox_result = deliver_team_visible_outbox(
            team=team,
            store=store,
            adapter=adapter,
            limit=10,
            on_delivered=lambda sent_row, message_id: registry_command(
                team,
                manifest_path,
                "record-visible-message",
                "--job-ref",
                sent_row["jobRef"],
                "--kind",
                str(sent_row["messageKind"]),
                "--message-id",
                message_id,
            ),
        )
        if outbox_result["deliveredCount"] < 1:
            emit({"status": "rollup_delivery_missing", "jobRef": row["job_ref"], "outboxResult": outbox_result})
            return 2
        rollup_message_id = str(outbox_result["results"][0]["deliveryMessageId"])

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


def reconcile_active_job_until_idle(
    team: dict[str, Any],
    manifest_path: Path,
    adapter: OpenClawAdapter,
) -> ReconcileLoopResult:
    conn, active = db_and_active_job(team, manifest_path)
    try:
        bare_no_reply_retries = 0
        retry_scheduled = False
        retry_observed_progress = False
        while active is not None:
            current_action = str(active["next_action"] or "").strip()
            if current_action == "publish":
                store = RuntimeStore(conn)
                controller = TeamController(store=store)
                stage_info = controller.current_stage_info(job_ref=str(active["job_ref"]))
                enqueued = controller.enqueue_publishable_callbacks(job_ref=str(active["job_ref"]))
                if not enqueued:
                    raise RuntimeError(f"publish requested but no callback is publishable for {active['job_ref']}")
                outbox_result = deliver_worker_publish_outbox(
                    team=team,
                    store=store,
                    controller=controller,
                    adapter=adapter,
                    job_ref=str(active["job_ref"]),
                    stage_key=str(stage_info["stageKey"]),
                    limit=max(len(enqueued), 1) * 2,
                )
                if outbox_result["deliveredCount"] < len(enqueued):
                    raise RuntimeError(
                        f"publish delivery incomplete for {active['job_ref']}: expected>={len(enqueued)}, actual={outbox_result['deliveredCount']}"
                    )
                retry_observed_progress = True
                conn.close()
                conn, active = db_and_active_job(team, manifest_path)
                continue
            repair_status = workflow_repair_status(conn, active)
            if repair_status and repair_status["status"] == "needs_dispatch_reconcile":
                retry_observed_progress = True
                job_ref = str(active["job_ref"])
                conn.close()
                dispatch_exit = reconcile_dispatch(team, manifest_path, adapter, job_ref)
                if dispatch_exit != 0:
                    return ReconcileLoopResult(dispatch_exit)
                conn, active = db_and_active_job(team, manifest_path)
                continue
            if repair_status and repair_status["status"] == "needs_rollup_reconcile":
                retry_observed_progress = True
                return ReconcileLoopResult(reconcile_rollup(team, manifest_path, adapter, str(active["job_ref"])))

            retry_agent_ids = current_stage_terminal_worker_retry_agents(team, adapter, conn, active)
            if retry_agent_ids:
                if bare_no_reply_retries >= INLINE_WORKER_NO_REPLY_RETRY_LIMIT:
                    emit(
                        {
                            "status": "worker_callback_retry_exhausted",
                            "jobRef": active["job_ref"],
                            "agentIds": retry_agent_ids,
                            "reason": "worker_main_terminal_without_callback",
                        }
                    )
                    return ReconcileLoopResult(2)
                bare_no_reply_retries += 1
                retry_scheduled = True
                job_ref = str(active["job_ref"])
                conn.close()
                dispatch_exit = reconcile_dispatch(team, manifest_path, adapter, job_ref, force=True, agent_ids=retry_agent_ids)
                if dispatch_exit != 0:
                    return ReconcileLoopResult(dispatch_exit)
                conn, active = db_and_active_job(team, manifest_path)
                emit(
                    {
                        "status": "worker_callback_retry_scheduled",
                        "jobRef": job_ref,
                        "agentIds": retry_agent_ids,
                        "attempt": bare_no_reply_retries,
                        "limit": INLINE_WORKER_NO_REPLY_RETRY_LIMIT,
                    }
                )
                continue
            break
    finally:
        conn.close()
    if retry_scheduled and not retry_observed_progress and active is not None:
        return ReconcileLoopResult(0, status="retry_scheduled")
    return ReconcileLoopResult(0)


def resume_job(team: dict[str, Any], manifest_path: Path, adapter: OpenClawAdapter, stale_seconds: int) -> int:
    preflight = reconcile_active_job_until_idle(team, manifest_path, adapter)
    if preflight.exit_code != 0:
        return preflight.exit_code
    if preflight.status == "retry_scheduled":
        return 0

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
        dispatch_exit = reconcile_dispatch(team, manifest_path, adapter, str(watchdog_payload["jobRef"]))
        if dispatch_exit != 0:
            return dispatch_exit
    elif status == "needs_rollup_reconcile":
        rollup_exit = reconcile_rollup(team, manifest_path, adapter, str(watchdog_payload["jobRef"]))
        if rollup_exit != 0:
            return rollup_exit
    elif status not in {"no_active_job", "stale_recovered", "active_ok"}:
        emit(watchdog_payload if isinstance(watchdog_payload, dict) else {"status": status or "noop"})
        return 0

    post_watchdog = reconcile_active_job_until_idle(team, manifest_path, adapter)
    if post_watchdog.exit_code != 0:
        return post_watchdog.exit_code
    if post_watchdog.status == "retry_scheduled":
        return 0

    conn, _active = db_and_active_job(team, manifest_path)
    try:
        pending = latest_pending_inbound(team, adapter, conn)
    finally:
        conn.close()

    if pending is None:
        emit({"status": "no_pending_inbound_message", "teamKey": team["teamKey"]})
        return 0

    started_payload = start_job_from_inbound(team, manifest_path, pending)
    supervisor_drift_session_reset = reset_supervisor_spawned_subagent_sessions(
        team,
        adapter,
        pending.supervisor_spawned_session_keys,
    )
    dispatch_exit = reconcile_dispatch(team, manifest_path, adapter, str(started_payload["jobRef"]))
    if dispatch_exit != 0:
        return dispatch_exit
    emit(
        {
            "status": "dispatch_reconciled",
            "jobRef": started_payload["jobRef"],
            "jobStarted": True,
            "ackVisibleSent": True,
            "agentId": started_payload["waitingForAgentId"],
            "supervisorSpawnedSessionReset": supervisor_drift_session_reset,
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
    adapter = OpenClawAdapter(openclaw_home=openclaw_home, openclaw_bin=openclaw_bin)
    try:
        team = load_manifest_team(manifest_path, args.team_key)
    except (ValueError, FileNotFoundError) as exc:
        emit({"status": "invalid_manifest", "error": str(exc)})
        return 2

    lock_handle = acquire_team_lock(team_lock_path(team, manifest_path))
    if lock_handle is None:
        emit(
            {
                "status": "reconcile_already_running",
                "teamKey": team["teamKey"],
                "lockPath": str(team_lock_path(team, manifest_path)),
            }
        )
        return 0

    try:
        if args.command == "resume-job":
            return resume_job(team, manifest_path, adapter, args.stale_seconds)
        if args.command == "reconcile-dispatch":
            return reconcile_dispatch(team, manifest_path, adapter, args.job_ref or None)
        if args.command == "reconcile-rollup":
            return reconcile_rollup(team, manifest_path, adapter, args.job_ref or None)
        emit({"status": "unsupported_command", "command": args.command})
        return 2
    except Exception as exc:  # pragma: no cover - surfaced via CLI output
        emit({"status": "reconcile_error", "error": str(exc)})
        return 2
    finally:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        finally:
            lock_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
