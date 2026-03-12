#!/usr/bin/env python3
"""Single-writer team controller for the redesigned V5.1 control plane."""

from __future__ import annotations

import json
import re
import shlex
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import core_job_registry as registry
from core_ingress_adapter import InboundEvent
from core_outbox_sender import enqueue_visible_message
from core_runtime_store import RuntimeStore


ACTION_DISPATCH = "dispatch"
ACTION_WAIT_WORKER = "wait_worker"
ACTION_PUBLISH = "publish"
ACTION_ROLLUP = "rollup"


class TeamController:
    """Single writer for per-team job lifecycle."""

    def __init__(self, store: RuntimeStore | None):
        self.store = store
        self._conn: sqlite3.Connection | None = store.connection if store is not None else None
        if self._conn is not None:
            registry.init_db(self._conn)

    def start_job(
        self,
        *,
        event: InboundEvent,
        title: str,
        workflow_agents: Iterable[str | dict[str, Any]] | None = None,
        workflow: dict[str, Any] | None = None,
        supervisor_visible_label: str = "主管",
        entry_delivery: dict[str, Any] | None = None,
        hidden_main_session_key: str = "",
    ) -> dict[str, Any]:
        conn = self._require_connection()
        workflow_payload = self._normalize_workflow_definition(workflow=workflow, workflow_agents=workflow_agents)
        normalized_agents = [
            dict(agent)
            for stage in registry.workflow_stage_groups(workflow_payload)
            for agent in stage.get("agents", [])
        ]
        if not normalized_agents:
            raise ValueError("workflow_agents 不能为空")

        existing = registry.find_job_by_source_message(
            conn,
            event.source_message_id,
            group_peer_id=event.canonical_target_id,
        )
        if existing is not None:
            return self._job_snapshot(existing)

        job_ref = registry.next_job_ref(conn)
        created_at = registry.now_iso()
        entry_target = registry.normalize_entry_target(event.canonical_target_id, event.canonical_target_id)

        conn.execute(
            """
            INSERT INTO jobs (
              job_ref, group_peer_id, team_key, requested_by, source_message_id, title, status, queue_position,
              workflow_json, orchestrator_version, request_text, supervisor_visible_label, entry_account_id, entry_channel,
              entry_target, entry_delivery_json, hidden_main_session_key, current_stage_index, waiting_for_agent_id, next_action,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'active', NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            """,
            (
                job_ref,
                event.canonical_target_id,
                event.team_key,
                event.requested_by,
                event.source_message_id,
                title,
                json.dumps(workflow_payload, ensure_ascii=False),
                registry.V5_1_HARDENING,
                event.request_text,
                supervisor_visible_label,
                event.account_id,
                event.channel,
                entry_target,
                json.dumps(entry_delivery or {
                    "channel": event.channel,
                    "accountId": event.account_id,
                    "target": entry_target,
                }, ensure_ascii=False),
                str(hidden_main_session_key or "").strip(),
                normalized_agents[0]["agentId"],
                ACTION_DISPATCH,
                created_at,
                created_at,
            ),
        )

        for agent in normalized_agents:
            conn.execute(
                """
                INSERT INTO job_participants (
                  job_ref, agent_id, account_id, role, visible_label, status, dispatch_run_id,
                  dispatch_status, progress_message_id, final_message_id, summary, completed_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', '', '', '', '', '', NULL)
                """,
                (
                    job_ref,
                    agent["agentId"],
                    agent["accountId"],
                    agent["role"],
                    agent["visibleLabel"],
                ),
            )

        registry.insert_event(
            conn,
            job_ref,
            "job_started",
            event.requested_by or "system",
            {
                "title": title,
                "workflow": workflow_payload,
                "sourceMessageId": event.source_message_id,
                "teamKey": event.team_key,
            },
        )

        for stage in registry.workflow_stage_groups(workflow_payload):
            if str(stage.get("mode") or "serial") == "parallel":
                self.store.create_publish_gate(
                    job_ref=job_ref,
                    stage_key=str(stage["stageKey"]),
                    mode="parallel",
                    publish_order=[str(item) for item in stage["publishOrder"]],
                )

        claim = self.store.claim_inbound_event(
            team_key=event.team_key,
            source_message_id=event.source_message_id,
            job_ref=job_ref,
        )
        if claim is None:
            self.store.record_inbound_event(
                team_key=event.team_key,
                source_message_id=event.source_message_id,
                canonical_target_id=event.canonical_target_id,
                request_text=event.request_text,
                requested_by=event.requested_by,
                raw_event=event.raw_event,
            )
            claim = self.store.claim_inbound_event(
                team_key=event.team_key,
                source_message_id=event.source_message_id,
                job_ref=job_ref,
            )
        if not claim or not claim.get("claimed"):
            raise RuntimeError("inbound event claim failed")

        conn.commit()
        return self._job_snapshot(self._load_job(job_ref))

    def plan_ack(self, *, job_ref: str) -> dict[str, Any]:
        return self.enqueue_ack(job_ref=job_ref)

    def enqueue_ack(self, *, job_ref: str) -> dict[str, Any]:
        conn = self._require_connection()
        row = self._load_job(job_ref)
        current_action = str(row["next_action"] or "").strip()
        if current_action != ACTION_DISPATCH:
            raise RuntimeError(f"ack 只能在待派单阶段执行: expected={ACTION_DISPATCH}, actual={current_action or 'none'}")
        existing = self.store.get_outbound_message(
            team_key=self._team_key_for_row(row),
            job_ref=job_ref,
            message_kind="ack",
        )
        if existing is not None or registry.flag_value(row["ack_visible_sent"] if "ack_visible_sent" in row.keys() else 0):
            raise RuntimeError("ack 已经计划或发送，不能重复执行")

        payload = {
            "jobRef": job_ref,
            "teamKey": self._team_key_for_row(row),
            "kind": "ack",
            "message": registry.visible_message_text("ack", row, conn),
            "delivery": registry.visible_delivery_for_row(row),
        }
        enqueue_visible_message(
            self.store,
            team_key=self._team_key_for_row(row),
            job_ref=job_ref,
            message_kind="ack",
            payload=payload,
        )
        conn.execute("UPDATE jobs SET updated_at = ? WHERE job_ref = ?", (registry.now_iso(), job_ref))
        registry.insert_event(conn, job_ref, "ack_planned", "controller", payload)
        conn.commit()
        return {
            "jobRef": job_ref,
            "teamKey": self._team_key_for_row(row),
            "deliveryMode": "outbox",
            "messageKind": "ack",
            "nextAction": ACTION_DISPATCH,
        }

    def dispatch_next_stage(self, *, job_ref: str) -> dict[str, Any]:
        return self.dispatch_stage(job_ref=job_ref)

    def _build_dispatch_payload(
        self,
        *,
        job_ref: str,
        allow_wait_worker: bool = False,
        agent_id: str | None = None,
    ) -> tuple[sqlite3.Row, sqlite3.Row, int, dict[str, Any]]:
        conn = self._require_connection()
        row = self._load_job(job_ref)
        current_action = str(row["next_action"] or "").strip()
        if allow_wait_worker:
            if current_action not in {ACTION_DISPATCH, ACTION_WAIT_WORKER}:
                raise RuntimeError(f"当前 job 不处于可派单状态: expected=dispatch/wait_worker, actual={current_action or 'none'}")
        else:
            self._require_next_action(row, ACTION_DISPATCH, "当前 job 不处于可派单状态")
        stage_index = self._current_stage_index(row)
        if agent_id:
            participant = self._participant_map(job_ref).get(agent_id)
        else:
            participant = self._current_stage_participant(job_ref, row)
        if participant is None:
            raise RuntimeError("当前 stage 缺少 participant snapshot")

        runtime_script = str((Path(__file__).resolve().parent / "v51_team_orchestrator_runtime.py"))
        callback_sink_args = {
            "db": self._db_path(),
            "jobRef": job_ref,
            "teamKey": self._team_key_for_row(row),
            "stageIndex": stage_index,
            "agentId": participant["agent_id"],
        }
        callback_sink_command = " ".join(
            [
                "python3",
                shlex.quote(runtime_script),
                "ingest-callback",
                "--db",
                shlex.quote(self._db_path()),
                "--job-ref",
                shlex.quote(job_ref),
                "--team-key",
                shlex.quote(self._team_key_for_row(row)),
                "--stage-index",
                shlex.quote(str(stage_index)),
                "--agent-id",
                shlex.quote(participant["agent_id"]),
                "--payload",
            ]
        )
        payload = {
            "jobRef": job_ref,
            "teamKey": self._team_key_for_row(row),
            "stageIndex": stage_index,
            "groupPeerId": registry.canonical_group_peer_id_for_row(row),
            "agentId": participant["agent_id"],
            "accountId": participant["account_id"],
            "role": participant["role"],
            "requestText": row["request_text"] or row["title"],
            "title": row["title"],
            "callbackSinkRuntime": runtime_script,
            "callbackSinkArgs": callback_sink_args,
            "callbackSinkCommand": callback_sink_command,
            "mustSend": "progress,final,structured_callback",
            **registry.worker_visible_contract(
                job_ref,
                participant["agent_id"],
                participant["role"],
                participant["visible_label"],
            ),
        }
        payload["packet"] = (
            "TASK_DISPATCH|"
            f"jobRef={job_ref}|"
            f"from={str(row['hidden_main_session_key'] or '').strip() or 'controller'}|"
            f"to={participant['agent_id']}|"
            f"title={row['title']}|"
            f"request={row['request_text'] or row['title']}|"
            "mustSend=progress,final,structured_callback|"
            f"callbackCommand={callback_sink_command}|"
            f"scopeLabel={payload['scopeLabel']}|"
            f"progressTitle={payload['progressTitle']}|"
            f"finalTitle={payload['finalTitle']}|"
            f"callbackMustInclude={payload['callbackMustInclude']}|"
            f"forbiddenLabels={payload['forbiddenRoleLabels']}|"
            f"forbiddenSections={payload['forbiddenSectionKeywords']}|"
            f"finalScopeRule={payload['finalScopeRule']}"
        )
        return row, participant, stage_index, payload

    def dispatch_stage(self, *, job_ref: str) -> dict[str, Any]:
        conn = self._require_connection()
        row = self._load_job(job_ref)
        stage_group = self._current_stage_group(row)
        if str(stage_group.get("mode") or "serial") == "parallel":
            current_action = str(row["next_action"] or "").strip()
            self._require_next_action(row, ACTION_DISPATCH, "当前 job 不处于可派单状态")
            stage_index = self._current_stage_index(row)
            dispatches = []
            for agent in stage_group["agents"]:
                agent_id = str(agent["agentId"])
                participant = self._participant_map(job_ref).get(agent_id)
                if participant is None:
                    raise RuntimeError("当前 parallel stage 缺少 participant snapshot")
                _row, _participant, _stage_index, payload = self._build_dispatch_payload(
                    job_ref=job_ref,
                    agent_id=agent_id,
                )
                dispatches.append(payload)
                conn.execute(
                    """
                    UPDATE job_participants
                    SET status = 'running', dispatch_status = 'planned'
                    WHERE job_ref = ? AND agent_id = ?
                    """,
                    (job_ref, participant["agent_id"]),
                )
            self.store.update_publish_gate_state(
                job_ref=job_ref,
                stage_key=str(stage_group["stageKey"]),
                stage_status="running",
            )
            conn.execute(
                """
                UPDATE jobs
                SET next_action = ?, waiting_for_agent_id = NULL, updated_at = ?, dispatch_attempt_count = dispatch_attempt_count + 1
                WHERE job_ref = ?
                """,
                (ACTION_WAIT_WORKER, registry.now_iso(), job_ref),
            )
            registry.insert_event(
                conn,
                job_ref,
                "stage_dispatch_planned",
                "controller",
                {"stageKey": stage_group["stageKey"], "mode": "parallel", "dispatchCount": len(dispatches)},
            )
            conn.commit()
            return {
                "jobRef": job_ref,
                "teamKey": self._team_key_for_row(row),
                "stageKey": stage_group["stageKey"],
                "mode": "parallel",
                "dispatches": dispatches,
                "nextAction": ACTION_WAIT_WORKER,
            }

        row, participant, stage_index, payload = self._build_dispatch_payload(job_ref=job_ref)
        conn.execute(
            """
            UPDATE job_participants
            SET status = 'running', dispatch_status = 'planned'
            WHERE job_ref = ? AND agent_id = ?
            """,
            (job_ref, participant["agent_id"]),
        )
        conn.execute(
            """
            UPDATE jobs
            SET next_action = ?, updated_at = ?, dispatch_attempt_count = dispatch_attempt_count + 1
            WHERE job_ref = ?
            """,
            (ACTION_WAIT_WORKER, registry.now_iso(), job_ref),
        )
        registry.insert_event(conn, job_ref, "stage_dispatch_planned", "controller", payload)
        conn.commit()
        return {
            "jobRef": job_ref,
            "teamKey": self._team_key_for_row(row),
            "agentId": participant["agent_id"],
            "stageIndex": stage_index,
            "nextAction": ACTION_WAIT_WORKER,
            "payload": payload,
        }

    def redispatch_current_stage(self, *, job_ref: str) -> dict[str, Any]:
        _row, participant, stage_index, payload = self._build_dispatch_payload(
            job_ref=job_ref,
            allow_wait_worker=True,
        )
        return {
            "jobRef": job_ref,
            "teamKey": payload["teamKey"],
            "agentId": participant["agent_id"],
            "stageIndex": stage_index,
            "nextAction": ACTION_WAIT_WORKER,
            "payload": payload,
        }

    def redispatch_agents(self, *, job_ref: str, agent_ids: Iterable[str]) -> dict[str, Any]:
        row = self._load_job(job_ref)
        stage_group = self._current_stage_group(row)
        allowed_agents = {str(agent["agentId"]) for agent in stage_group.get("agents", [])}
        dispatches: list[dict[str, Any]] = []
        stage_index = self._current_stage_index(row)
        for agent_id in agent_ids:
            normalized_agent_id = str(agent_id or "").strip()
            if not normalized_agent_id:
                continue
            if normalized_agent_id not in allowed_agents:
                raise RuntimeError(f"当前 stage 不接受 {normalized_agent_id}")
            _row, _participant, _stage_index, payload = self._build_dispatch_payload(
                job_ref=job_ref,
                allow_wait_worker=True,
                agent_id=normalized_agent_id,
            )
            stage_index = _stage_index
            dispatches.append(payload)
        if not dispatches:
            raise RuntimeError("当前 stage 没有可重派的 agent")
        return {
            "jobRef": job_ref,
            "teamKey": self._team_key_for_row(row),
            "agentIds": [payload["agentId"] for payload in dispatches],
            "stageIndex": stage_index,
            "nextAction": ACTION_WAIT_WORKER,
            "dispatches": dispatches,
        }

    def record_dispatch_acceptance(
        self,
        *,
        job_ref: str,
        agent_id: str,
        dispatch_run_id: str,
        dispatch_status: str = "accepted",
    ) -> dict[str, Any]:
        conn = self._require_connection()
        row = self._load_job(job_ref)
        participant = self._participant_map(job_ref).get(agent_id)
        if participant is None:
            raise RuntimeError("当前 stage 缺少 participant snapshot")
        conn.execute(
            """
            UPDATE job_participants
            SET dispatch_run_id = ?, dispatch_status = ?, status = CASE WHEN status = 'done' THEN status ELSE 'accepted' END
            WHERE job_ref = ? AND agent_id = ?
            """,
            (
                str(dispatch_run_id or "").strip(),
                str(dispatch_status or "").strip() or "accepted",
                job_ref,
                agent_id,
            ),
        )
        conn.execute("UPDATE jobs SET updated_at = ? WHERE job_ref = ?", (registry.now_iso(), job_ref))
        conn.commit()
        return self._job_snapshot(self._load_job(job_ref))

    def record_progress_update(
        self,
        *,
        job_ref: str,
        agent_id: str,
        progress_text: str,
        progress_message_id: str,
    ) -> dict[str, Any]:
        conn = self._require_connection()
        row = self._load_job(job_ref)
        self._require_next_action(row, ACTION_WAIT_WORKER, "worker progress 只能在当前 stage 运行中写入")
        stage_group = self._current_stage_group(row)
        if str(stage_group.get("mode") or "serial") == "parallel":
            allowed_agents = {str(agent["agentId"]) for agent in stage_group["agents"]}
            if agent_id not in allowed_agents:
                raise RuntimeError(f"当前 parallel stage 不接受 {agent_id}")
            participant = self._participant_map(job_ref).get(agent_id)
        else:
            waiting_agent_id = str(row["waiting_for_agent_id"] or "").strip()
            if waiting_agent_id != agent_id:
                raise RuntimeError(f"当前 stage 等待 {waiting_agent_id or 'N/A'}，不能接收 {agent_id}")
            participant = self._current_stage_participant(job_ref, row)
        if participant is None:
            raise RuntimeError("当前 stage 缺少 participant snapshot")
        self._assert_worker_scope(
            job_ref=job_ref,
            participant=participant,
            progress_text=progress_text,
            final_text="",
        )
        existing_progress_message_id = str(participant["progress_message_id"] or "").strip()
        normalized_progress_message_id = str(progress_message_id or "").strip()
        if existing_progress_message_id and existing_progress_message_id == normalized_progress_message_id:
            return {
                "jobRef": job_ref,
                "agentId": agent_id,
                "stageIndex": self._current_stage_index(row),
                "nextAction": ACTION_WAIT_WORKER,
                "waitingForAgentId": str(row["waiting_for_agent_id"] or "").strip() or None,
                "status": "duplicate_progress",
            }
        conn.execute(
            """
            UPDATE job_participants
            SET progress_message_id = ?, status = CASE WHEN status = 'pending' THEN 'accepted' ELSE status END
            WHERE job_ref = ? AND agent_id = ?
            """,
            (
                normalized_progress_message_id,
                job_ref,
                agent_id,
            ),
        )
        registry.insert_event(
            conn,
            job_ref,
            "worker_progress_recorded",
            agent_id,
            {
                "stageIndex": self._current_stage_index(row),
                "agentId": agent_id,
                "progressText": progress_text,
                "progressMessageId": normalized_progress_message_id,
            },
        )
        conn.commit()
        return {
            "jobRef": job_ref,
            "agentId": agent_id,
            "stageIndex": self._current_stage_index(row),
            "nextAction": ACTION_WAIT_WORKER,
            "waitingForAgentId": str(row["waiting_for_agent_id"] or "").strip() or None,
            "status": "progress_recorded",
        }

    def current_stage_info(self, *, job_ref: str) -> dict[str, Any]:
        row = self._load_job(job_ref)
        stage_group = self._current_stage_group(row)
        return {
            "jobRef": job_ref,
            "stageIndex": self._current_stage_index(row),
            "stageKey": str(stage_group["stageKey"]),
            "mode": str(stage_group.get("mode") or "serial"),
            "nextAction": str(row["next_action"] or "").strip(),
        }

    def record_outbound_delivery(
        self,
        *,
        job_ref: str,
        agent_id: str,
        message_kind: str,
        delivery_message_id: str,
    ) -> dict[str, Any]:
        conn = self._require_connection()
        if message_kind not in {"worker_progress", "worker_final"}:
            raise ValueError(f"unsupported worker outbound message kind: {message_kind}")
        participant = self._participant_map(job_ref).get(agent_id)
        if participant is None:
            raise RuntimeError("当前 stage 缺少 participant snapshot")
        column = "progress_message_id" if message_kind == "worker_progress" else "final_message_id"
        conn.execute(
            f"""
            UPDATE job_participants
            SET {column} = ?
            WHERE job_ref = ? AND agent_id = ?
            """,
            (
                str(delivery_message_id or "").strip(),
                job_ref,
                agent_id,
            ),
        )
        conn.commit()
        return self._job_snapshot(self._load_job(job_ref))

    def accept_worker_callback(
        self,
        *,
        job_ref: str,
        agent_id: str,
        progress_text: str,
        final_text: str,
        summary: str,
        details: str,
        risks: str,
        action_items: str,
        progress_message_id: str = "",
        final_message_id: str = "",
        final_visible_text: str = "",
    ) -> dict[str, Any]:
        return self.accept_callback(
            job_ref=job_ref,
            agent_id=agent_id,
            progress_text=progress_text,
            final_text=final_text,
            summary=summary,
            details=details,
            risks=risks,
            action_items=action_items,
            progress_message_id=progress_message_id,
            final_message_id=final_message_id,
            final_visible_text=final_visible_text,
        )

    def accept_callback(
        self,
        *,
        job_ref: str,
        agent_id: str,
        progress_text: str,
        final_text: str,
        summary: str,
        details: str,
        risks: str,
        action_items: str,
        progress_message_id: str = "",
        final_message_id: str = "",
        final_visible_text: str = "",
    ) -> dict[str, Any]:
        conn = self._require_connection()
        row = self._load_job(job_ref)
        self._require_next_action(row, ACTION_WAIT_WORKER, "worker callback 只能在当前 stage 运行中写入")
        stage_group = self._current_stage_group(row)
        if str(stage_group.get("mode") or "serial") == "parallel":
            allowed_agents = {str(agent["agentId"]) for agent in stage_group["agents"]}
            if agent_id not in allowed_agents:
                raise RuntimeError(f"当前 parallel stage 不接受 {agent_id}")
            participant = self._participant_map(job_ref).get(agent_id)
        else:
            waiting_agent_id = str(row["waiting_for_agent_id"] or "").strip()
            if waiting_agent_id != agent_id:
                raise RuntimeError(f"当前 stage 等待 {waiting_agent_id or 'N/A'}，不能接收 {agent_id}")
            participant = self._current_stage_participant(job_ref, row)
        if participant is None:
            raise RuntimeError("当前 stage 缺少 participant snapshot")

        self._assert_worker_scope(
            job_ref=job_ref,
            participant=participant,
            progress_text=progress_text,
            final_text=final_text,
        )

        stage_index = self._current_stage_index(row)
        callback_payload = {
            "jobRef": job_ref,
            "stageIndex": stage_index,
            "agentId": agent_id,
            "progressDraft": progress_text,
            "finalDraft": final_text,
            "progressMessageId": str(progress_message_id or "").strip(),
            "finalMessageId": str(final_message_id or "").strip(),
            "finalVisibleText": str(final_visible_text or final_text or "").strip(),
            "summary": summary,
            "details": details,
            "risks": risks,
            "actionItems": action_items,
        }
        self.store.record_stage_callback(
            job_ref=job_ref,
            stage_index=stage_index,
            agent_id=agent_id,
            payload=callback_payload,
        )
        conn.execute(
            """
            UPDATE job_participants
            SET status = 'done', summary = ?, completed_at = ?, progress_message_id = ?, final_message_id = ?
            WHERE job_ref = ? AND agent_id = ?
            """,
            (
                summary,
                registry.now_iso(),
                str(progress_message_id or "").strip(),
                str(final_message_id or "").strip(),
                job_ref,
                agent_id,
            ),
        )

        workflow_groups = self._workflow_groups(row)
        if str(stage_group.get("mode") or "serial") == "parallel":
            callbacks = self.store.list_stage_callbacks(job_ref=job_ref)
            stage_callback_agents = {
                item["agentId"] for item in callbacks if int(item["stageIndex"]) == stage_index
            }
            stage_agents = {str(agent["agentId"]) for agent in stage_group["agents"]}
            all_stage_callbacks_received = stage_agents.issubset(stage_callback_agents)
            if all_stage_callbacks_received:
                next_action = ACTION_PUBLISH
                next_stage_index = stage_index
                next_agent_id = None
                self.store.update_publish_gate_state(
                    job_ref=job_ref,
                    stage_key=str(stage_group["stageKey"]),
                    stage_status="ready_to_publish",
                )
            else:
                next_action = ACTION_WAIT_WORKER
                next_stage_index = stage_index
                next_agent_id = None
        else:
            workflow_agents = self._workflow_agents(row)
            if stage_index >= len(workflow_agents) - 1:
                next_action = ACTION_ROLLUP
                next_stage_index = stage_index
                next_agent_id = None
            else:
                next_stage_index = stage_index + 1
                next_agent_id = workflow_agents[next_stage_index]
                next_action = ACTION_DISPATCH

        conn.execute(
            """
            UPDATE jobs
            SET current_stage_index = ?, waiting_for_agent_id = ?, next_action = ?, updated_at = ?
            WHERE job_ref = ?
            """,
            (next_stage_index, next_agent_id, next_action, registry.now_iso(), job_ref),
        )
        registry.insert_event(conn, job_ref, "worker_completed", agent_id, callback_payload)
        conn.commit()
        return {
            "jobRef": job_ref,
            "agentId": agent_id,
            "stageIndex": stage_index,
            "nextAction": next_action,
            "waitingForAgentId": next_agent_id,
        }

    def collect_publishable_callbacks(self, *, job_ref: str) -> list[dict[str, Any]]:
        row = self._load_job(job_ref)
        stage_group = self._current_stage_group(row)
        if str(stage_group.get("mode") or "serial") != "parallel":
            return []
        gate = self.store.get_publish_gate(job_ref=job_ref, stage_key=str(stage_group["stageKey"]))
        if gate is None:
            return []
        callbacks = {
            item["agentId"]: item
            for item in self.store.list_stage_callbacks(job_ref=job_ref)
            if int(item["stageIndex"]) == self._current_stage_index(row)
        }
        next_agent = gate["nextAgentId"]
        if not next_agent:
            return []
        callback = callbacks.get(next_agent)
        if not callback or callback["publishState"] != "pending_publish":
            return []
        return [callback]

    def enqueue_publishable_callbacks(self, *, job_ref: str) -> list[dict[str, Any]]:
        row = self._load_job(job_ref)
        stage_group = self._current_stage_group(row)
        if str(stage_group.get("mode") or "serial") != "parallel":
            return []
        callbacks = self.collect_publishable_callbacks(job_ref=job_ref)
        enqueued: list[dict[str, Any]] = []
        participants = self._participant_map(job_ref)
        for callback in callbacks:
            agent_id = str(callback["agentId"])
            participant = participants.get(agent_id)
            if participant is None:
                raise RuntimeError("publishable callback missing participant snapshot")
            payload = callback["payload"]
            delivery = {
                "channel": row["entry_channel"],
                "accountId": participant["account_id"],
                "target": registry.normalize_entry_target(
                    str(row["group_peer_id"] or ""),
                    str(row["entry_target"] or ""),
                ),
            }
            progress_draft = str(payload.get("progressDraft") or payload.get("progressText") or "").strip()
            final_draft = str(payload.get("finalDraft") or payload.get("finalText") or "").strip()
            existing_progress_message_id = str(participant["progress_message_id"] or "").strip()
            existing_final_message_id = str(participant["final_message_id"] or "").strip()
            progress_finalize_after_send = False
            if progress_draft and not existing_progress_message_id:
                progress_finalize_after_send = bool(existing_final_message_id and not final_draft)
                enqueue_visible_message(
                    self.store,
                    team_key=self._team_key_for_row(row),
                    job_ref=job_ref,
                    message_kind="worker_progress",
                    payload={
                        "jobRef": job_ref,
                        "teamKey": self._team_key_for_row(row),
                        "delivery": delivery,
                        "message": progress_draft,
                        "finalizeAfterSend": progress_finalize_after_send,
                    },
                    stage_index=int(callback["stageIndex"]),
                    agent_id=agent_id,
                )
                enqueued.append(
                    {
                        "jobRef": job_ref,
                        "stageIndex": int(callback["stageIndex"]),
                        "agentId": agent_id,
                        "messageKind": "worker_progress",
                    }
                )
            if final_draft and not existing_final_message_id:
                enqueue_visible_message(
                    self.store,
                    team_key=self._team_key_for_row(row),
                    job_ref=job_ref,
                    message_kind="worker_final",
                    payload={
                        "jobRef": job_ref,
                        "teamKey": self._team_key_for_row(row),
                        "delivery": delivery,
                        "message": final_draft,
                    },
                    stage_index=int(callback["stageIndex"]),
                    agent_id=agent_id,
                )
                enqueued.append(
                    {
                        "jobRef": job_ref,
                        "stageIndex": int(callback["stageIndex"]),
                        "agentId": agent_id,
                        "messageKind": "worker_final",
                    }
                )
            if enqueued:
                self.store.mark_stage_callback_publish_queued(
                    job_ref=job_ref,
                    stage_index=int(callback["stageIndex"]),
                    agent_id=agent_id,
                )
            elif existing_progress_message_id or existing_final_message_id:
                self.mark_callback_published(
                    job_ref=job_ref,
                    stage_key=str(stage_group["stageKey"]),
                    agent_id=agent_id,
                )
        return enqueued

    def mark_callback_published(self, *, job_ref: str, stage_key: str, agent_id: str) -> dict[str, Any]:
        row = self._load_job(job_ref)
        stage_index = self._current_stage_index(row)
        self.store.mark_stage_callback_published(job_ref=job_ref, stage_index=stage_index, agent_id=agent_id)
        gate = self.store.advance_publish_gate(job_ref=job_ref, stage_key=stage_key, published_agent_id=agent_id)
        if gate["stageStatus"] == "completed":
            workflow_groups = self._workflow_groups(row)
            if stage_index >= len(workflow_groups) - 1:
                next_action = ACTION_ROLLUP
                next_stage_index = stage_index
                next_agent_id = None
            else:
                next_stage_index = stage_index + 1
                next_stage = workflow_groups[next_stage_index]
                next_action = ACTION_DISPATCH
                next_agent_id = (
                    str(next_stage["agents"][0]["agentId"])
                    if str(next_stage.get("mode") or "serial") == "serial"
                    else None
                )
            self._conn.execute(
                """
                UPDATE jobs
                SET current_stage_index = ?, waiting_for_agent_id = ?, next_action = ?, updated_at = ?
                WHERE job_ref = ?
                """,
                (next_stage_index, next_agent_id, next_action, registry.now_iso(), job_ref),
            )
            self._conn.commit()
        return gate

    def plan_rollup(self, *, job_ref: str) -> dict[str, Any]:
        return self.enqueue_rollup(job_ref=job_ref)

    def enqueue_rollup(self, *, job_ref: str) -> dict[str, Any]:
        conn = self._require_connection()
        row = self._load_job(job_ref)
        self._require_next_action(row, ACTION_ROLLUP, "只有所有 worker 完成后才能统一收口")
        self._require_all_stage_callbacks(job_ref, row)
        existing = self.store.get_outbound_message(
            team_key=self._team_key_for_row(row),
            job_ref=job_ref,
            message_kind="rollup",
        )
        if existing is not None or registry.flag_value(row["rollup_visible_sent"] if "rollup_visible_sent" in row.keys() else 0):
            raise RuntimeError("rollup 已经计划或发送，不能重复执行")

        payload = {
            "jobRef": job_ref,
            "teamKey": self._team_key_for_row(row),
            "kind": "rollup",
            "message": registry.visible_message_text("rollup", row, conn),
            "delivery": registry.visible_delivery_for_row(row),
            "completionPackets": registry.latest_completion_packets(conn, job_ref),
        }
        enqueue_visible_message(
            self.store,
            team_key=self._team_key_for_row(row),
            job_ref=job_ref,
            message_kind="rollup",
            payload=payload,
        )
        conn.execute("UPDATE jobs SET updated_at = ? WHERE job_ref = ?", (registry.now_iso(), job_ref))
        registry.insert_event(conn, job_ref, "rollup_planned", "controller", payload)
        conn.commit()
        return {
            "jobRef": job_ref,
            "teamKey": self._team_key_for_row(row),
            "deliveryMode": "outbox",
            "messageKind": "rollup",
            "nextAction": ACTION_ROLLUP,
        }

    def close_job(self, *, job_ref: str, status: str = "done") -> dict[str, Any]:
        conn = self._require_connection()
        row = self._load_job(job_ref)
        if status not in {"done", "failed", "cancelled"}:
            raise ValueError(f"unsupported final status: {status}")
        closed_at = registry.now_iso()
        conn.execute(
            """
            UPDATE jobs
            SET status = ?, next_action = NULL, updated_at = ?, closed_at = ?
            WHERE job_ref = ?
            """,
            (status, closed_at, closed_at, job_ref),
        )
        registry.insert_event(conn, job_ref, "job_closed", "controller", {"status": status})
        conn.commit()
        row = self._load_job(job_ref)
        return self._job_snapshot(row)

    def _require_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("TeamController requires a RuntimeStore-backed connection")
        return self._conn

    def _load_job(self, job_ref: str) -> sqlite3.Row:
        conn = self._require_connection()
        row = registry.get_job(conn, job_ref)
        if row is None:
            raise RuntimeError(f"job missing: {job_ref}")
        return row

    def _job_snapshot(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "jobRef": row["job_ref"],
            "status": row["status"],
            "title": row["title"],
            "teamKey": self._team_key_for_row(row),
            "groupPeerId": registry.canonical_group_peer_id_for_row(row),
            "nextAction": str(row["next_action"] or "").strip(),
            "currentStageIndex": self._current_stage_index(row),
            "waitingForAgentId": str(row["waiting_for_agent_id"] or "").strip() or None,
        }

    def _team_key_for_row(self, row: sqlite3.Row) -> str:
        if "team_key" in row.keys():
            value = str(row["team_key"] or "").strip()
            if value:
                return value
        return str(row["group_peer_id"] or "").strip()

    def _current_stage_index(self, row: sqlite3.Row) -> int:
        return int(row["current_stage_index"] or 0)

    def _workflow_agents(self, row: sqlite3.Row) -> list[str]:
        workflow = registry.parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
        if not workflow:
            raise RuntimeError("workflow missing")
        return registry.workflow_stage_agent_ids(workflow)

    def _workflow_groups(self, row: sqlite3.Row) -> list[dict[str, Any]]:
        workflow = registry.parse_workflow_json(row["workflow_json"]) if "workflow_json" in row.keys() else None
        if not workflow:
            raise RuntimeError("workflow missing")
        return registry.workflow_stage_groups(workflow)

    def _participant_map(self, job_ref: str) -> dict[str, sqlite3.Row]:
        return registry.participant_map(self._require_connection(), job_ref)

    def _db_path(self) -> str:
        row = self._require_connection().execute("PRAGMA database_list").fetchone()
        if row and len(row) >= 3 and row[2]:
            return str(row[2])
        return ":memory:"

    def _current_stage_participant(self, job_ref: str, row: sqlite3.Row) -> sqlite3.Row | None:
        waiting_agent_id = str(row["waiting_for_agent_id"] or "").strip()
        if not waiting_agent_id:
            return None
        return self._participant_map(job_ref).get(waiting_agent_id)

    def _current_stage_group(self, row: sqlite3.Row) -> dict[str, Any]:
        groups = self._workflow_groups(row)
        return groups[self._current_stage_index(row)]

    def _require_next_action(self, row: sqlite3.Row, expected: str, message: str) -> None:
        actual = str(row["next_action"] or "").strip()
        if actual != expected:
            raise RuntimeError(f"{message}: expected={expected}, actual={actual or 'none'}")

    def _require_all_stage_callbacks(self, job_ref: str, row: sqlite3.Row) -> None:
        callbacks = self.store.list_stage_callbacks(job_ref=job_ref)
        callback_agents = {item["agentId"] for item in callbacks}
        expected_agents = set(self._workflow_agents(row))
        missing = sorted(expected_agents - callback_agents)
        if missing:
            raise RuntimeError(f"rollup blocked until required callbacks exist: {', '.join(missing)}")

    def _normalize_workflow_agent(self, raw: str | dict[str, Any]) -> dict[str, str]:
        if isinstance(raw, str):
            agent_id = raw.strip()
            role = registry.participant_role_label(agent_id, agent_id)
            visible_label = registry.resolved_visible_label(
                explicit_label="",
                agent_id=agent_id,
                role=role,
                kind="worker",
            )
            return {
                "agentId": agent_id,
                "accountId": agent_id,
                "role": role,
                "visibleLabel": visible_label,
            }
        if not isinstance(raw, dict):
            raise ValueError("workflow_agents item must be str or dict")
        agent_id = str(raw.get("agentId") or "").strip()
        if not agent_id:
            raise ValueError("workflow_agents item requires agentId")
        role = str(raw.get("role") or "").strip() or registry.participant_role_label(agent_id, agent_id)
        visible_label = str(raw.get("visibleLabel") or "").strip() or registry.resolved_visible_label(
            explicit_label="",
            agent_id=agent_id,
            role=role,
            kind="worker",
        )
        account_id = str(raw.get("accountId") or "").strip() or agent_id
        return {
            "agentId": agent_id,
            "accountId": account_id,
            "role": role,
            "visibleLabel": visible_label,
        }

    def _normalize_workflow_definition(
        self,
        *,
        workflow: dict[str, Any] | None,
        workflow_agents: Iterable[str | dict[str, Any]] | None,
    ) -> dict[str, Any]:
        metadata_by_agent: dict[str, dict[str, str]] = {}
        if workflow_agents is not None:
            for agent in workflow_agents:
                normalized_agent = self._normalize_workflow_agent(agent)
                metadata_by_agent[normalized_agent["agentId"]] = normalized_agent
        if workflow is not None:
            normalized = registry.validate_workflow_payload(workflow)
            for raw_stage in workflow.get("stages", []):
                if not isinstance(raw_stage, dict):
                    continue
                if raw_stage.get("agentId"):
                    normalized_agent = self._normalize_workflow_agent(
                        {"agentId": str(raw_stage.get("agentId"))}
                    )
                    metadata_by_agent.setdefault(normalized_agent["agentId"], normalized_agent)
                    continue
                raw_agents = raw_stage.get("agents")
                if not isinstance(raw_agents, list):
                    continue
                for raw_agent in raw_agents:
                    if not isinstance(raw_agent, dict):
                        continue
                    normalized_agent = self._normalize_workflow_agent(raw_agent)
                    metadata_by_agent.setdefault(normalized_agent["agentId"], normalized_agent)
            enriched_stages: list[dict[str, Any]] = []
            for stage in normalized.get("stages", []):
                enriched_agents = []
                for agent in stage.get("agents", []):
                    agent_id = str(agent.get("agentId") or "").strip()
                    normalized_agent = metadata_by_agent.get(agent_id) or self._normalize_workflow_agent(agent_id)
                    enriched_agents.append(dict(normalized_agent))
                enriched_stages.append(
                    {
                        "stageKey": stage["stageKey"],
                        "mode": stage["mode"],
                        "agents": enriched_agents,
                        "publishOrder": list(stage["publishOrder"]),
                    }
                )
            return {
                "mode": normalized["mode"],
                "stages": enriched_stages,
            }
        if workflow_agents is None:
            raise ValueError("workflow or workflow_agents is required")
        normalized_agents = list(metadata_by_agent.values())
        normalized = registry.validate_workflow_payload(
            {
                "stages": [
                    {"agentId": agent["agentId"]}
                    for agent in normalized_agents
                ]
            }
        )
        enriched_stages: list[dict[str, Any]] = []
        for stage in normalized.get("stages", []):
            enriched_agents = []
            for agent in stage.get("agents", []):
                agent_id = str(agent.get("agentId") or "").strip()
                normalized_agent = metadata_by_agent.get(agent_id) or self._normalize_workflow_agent(agent_id)
                enriched_agents.append(dict(normalized_agent))
            enriched_stages.append(
                {
                    "stageKey": stage["stageKey"],
                    "mode": stage["mode"],
                    "agents": enriched_agents,
                    "publishOrder": list(stage["publishOrder"]),
                }
            )
        return {
            "mode": normalized["mode"],
            "stages": enriched_stages,
        }

    def _assert_worker_scope(
        self,
        *,
        job_ref: str,
        participant: sqlite3.Row,
        progress_text: str,
        final_text: str,
    ) -> None:
        contract = registry.worker_visible_contract(
            job_ref,
            participant["agent_id"],
            participant["role"],
            participant["visible_label"],
        )
        progress_title = contract["progressTitle"]
        final_title = contract["finalTitle"]
        if progress_text and not str(progress_text).strip().startswith(progress_title):
            raise ValueError(f"worker progress must start with {progress_title}")
        if final_text and not str(final_text).strip().startswith(final_title):
            raise ValueError(f"worker final must start with {final_title}")

        forbidden_labels = [item.strip() for item in contract["forbiddenRoleLabels"].split(",") if item.strip()]
        text = str(final_text or "")
        for label in forbidden_labels:
            if f"【{label}进度" in text or f"【{label}结论" in text:
                raise ValueError(f"worker final leaks cross-role label: {label}")

        forbidden_sections = [
            item.strip()
            for item in contract["forbiddenSectionKeywords"].split(",")
            if item.strip()
        ]
        for keyword in forbidden_sections:
            pattern = re.compile(rf"(^|\n)\s*(?:[一二三四五六七八九十]+、)?[^\n]*{re.escape(keyword)}")
            if pattern.search(text):
                raise ValueError(f"worker final leaks forbidden section: {keyword}")
