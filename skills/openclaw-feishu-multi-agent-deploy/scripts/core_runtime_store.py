#!/usr/bin/env python3
"""Shared team-scoped runtime store for the redesigned V5.1 control plane."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


RUNTIME_STORE_SCHEMA = """
CREATE TABLE IF NOT EXISTS inbound_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_key TEXT NOT NULL,
  source_message_id TEXT NOT NULL,
  canonical_target_id TEXT NOT NULL,
  request_text TEXT,
  requested_by TEXT,
  raw_event_json TEXT,
  claimed_by_job_ref TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(team_key, source_message_id)
);

CREATE INDEX IF NOT EXISTS idx_inbound_events_team_created
ON inbound_events(team_key, created_at);

CREATE TABLE IF NOT EXISTS outbound_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_key TEXT NOT NULL,
  job_ref TEXT NOT NULL,
  message_kind TEXT NOT NULL,
  stage_index INTEGER NOT NULL DEFAULT -1,
  agent_id TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  delivery_message_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(team_key, job_ref, message_kind, stage_index, agent_id)
);

CREATE INDEX IF NOT EXISTS idx_outbound_messages_pending
ON outbound_messages(team_key, status, created_at);

CREATE TABLE IF NOT EXISTS stage_callbacks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_ref TEXT NOT NULL,
  stage_index INTEGER NOT NULL,
  agent_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  publish_state TEXT NOT NULL DEFAULT 'pending_publish',
  published_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(job_ref, stage_index, agent_id)
);

CREATE TABLE IF NOT EXISTS publish_gates (
  job_ref TEXT NOT NULL,
  stage_key TEXT NOT NULL,
  mode TEXT NOT NULL,
  publish_order_json TEXT NOT NULL,
  publish_cursor INTEGER NOT NULL DEFAULT 0,
  stage_status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (job_ref, stage_key)
);

CREATE TABLE IF NOT EXISTS controller_locks (
  team_key TEXT PRIMARY KEY,
  owner TEXT NOT NULL,
  acquired_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def initialize_runtime_store_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(RUNTIME_STORE_SCHEMA)


class RuntimeStore:
    def __init__(self, db_path: str | Path | sqlite3.Connection):
        if isinstance(db_path, sqlite3.Connection):
            self._conn = db_path
            self._owns_connection = False
        else:
            path = str(db_path)
            if path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(path)
            self._owns_connection = True
        self._conn.row_factory = sqlite3.Row

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    def close(self) -> None:
        if self._owns_connection:
            self._conn.close()

    def initialize(self) -> None:
        initialize_runtime_store_schema(self._conn)
        self._conn.commit()

    def record_inbound_event(
        self,
        *,
        team_key: str,
        source_message_id: str,
        canonical_target_id: str,
        request_text: str = "",
        requested_by: str = "",
        raw_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        timestamp = now_iso()
        payload_json = json.dumps(raw_event, ensure_ascii=False) if raw_event is not None else None
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO inbound_events (
              team_key, source_message_id, canonical_target_id,
              request_text, requested_by, raw_event_json,
              claimed_by_job_ref, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                team_key,
                source_message_id,
                canonical_target_id,
                request_text,
                requested_by,
                payload_json,
                timestamp,
                timestamp,
            ),
        )
        created = cursor.rowcount == 1
        row = self._conn.execute(
            """
            SELECT team_key, source_message_id, canonical_target_id, request_text, requested_by,
                   raw_event_json, claimed_by_job_ref, created_at, updated_at
            FROM inbound_events
            WHERE team_key = ? AND source_message_id = ?
            """,
            (team_key, source_message_id),
        ).fetchone()
        self._conn.commit()
        assert row is not None
        return {
            "created": created,
            "teamKey": row["team_key"],
            "sourceMessageId": row["source_message_id"],
            "canonicalTargetId": row["canonical_target_id"],
            "requestText": row["request_text"] or "",
            "requestedBy": row["requested_by"] or "",
            "claimedByJobRef": row["claimed_by_job_ref"] or "",
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def claim_inbound_event(
        self,
        *,
        team_key: str,
        source_message_id: str,
        job_ref: str,
    ) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT team_key, source_message_id, canonical_target_id, request_text, requested_by,
                   raw_event_json, claimed_by_job_ref, created_at, updated_at
            FROM inbound_events
            WHERE team_key = ? AND source_message_id = ?
            """,
            (team_key, source_message_id),
        ).fetchone()
        if row is None:
            return None

        existing_claim = str(row["claimed_by_job_ref"] or "").strip()
        if existing_claim and existing_claim != job_ref:
            return {
                "claimed": False,
                "teamKey": row["team_key"],
                "sourceMessageId": row["source_message_id"],
                "claimedByJobRef": existing_claim,
            }

        self._conn.execute(
            """
            UPDATE inbound_events
            SET claimed_by_job_ref = ?, updated_at = ?
            WHERE team_key = ? AND source_message_id = ?
            """,
            (job_ref, now_iso(), team_key, source_message_id),
        )
        self._conn.commit()
        return {
            "claimed": True,
            "teamKey": row["team_key"],
            "sourceMessageId": row["source_message_id"],
            "canonicalTargetId": row["canonical_target_id"],
            "requestText": row["request_text"] or "",
            "requestedBy": row["requested_by"] or "",
            "claimedByJobRef": job_ref,
        }

    def find_unclaimed_inbound_event_for_team(self, team_key: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT team_key, source_message_id, canonical_target_id, request_text, requested_by,
                   raw_event_json, claimed_by_job_ref, created_at, updated_at
            FROM inbound_events
            WHERE team_key = ? AND (claimed_by_job_ref IS NULL OR claimed_by_job_ref = '')
            ORDER BY id DESC
            LIMIT 1
            """,
            (team_key,),
        ).fetchone()
        if row is None:
            return None
        raw_event_json = str(row["raw_event_json"] or "").strip()
        return {
            "teamKey": row["team_key"],
            "sourceMessageId": row["source_message_id"],
            "canonicalTargetId": row["canonical_target_id"],
            "requestText": row["request_text"] or "",
            "requestedBy": row["requested_by"] or "",
            "rawEvent": json.loads(raw_event_json) if raw_event_json else None,
            "claimedByJobRef": row["claimed_by_job_ref"] or "",
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def enqueue_outbound_message(
        self,
        *,
        team_key: str,
        job_ref: str,
        message_kind: str,
        payload: dict[str, Any],
        stage_index: int = -1,
        agent_id: str = "",
    ) -> dict[str, Any]:
        timestamp = now_iso()
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO outbound_messages (
              team_key, job_ref, message_kind, stage_index, agent_id,
              payload_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                team_key,
                job_ref,
                message_kind,
                stage_index,
                agent_id,
                json.dumps(payload, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )
        created = cursor.rowcount == 1
        row = self._conn.execute(
            """
            SELECT id, team_key, job_ref, message_kind, stage_index, agent_id,
                   payload_json, status, delivery_message_id, created_at, updated_at
            FROM outbound_messages
            WHERE team_key = ? AND job_ref = ? AND message_kind = ? AND stage_index = ? AND agent_id = ?
            """,
            (team_key, job_ref, message_kind, stage_index, agent_id),
        ).fetchone()
        self._conn.commit()
        assert row is not None
        return {
            "created": created,
            "id": row["id"],
            "teamKey": row["team_key"],
            "jobRef": row["job_ref"],
            "messageKind": row["message_kind"],
            "stageIndex": row["stage_index"],
            "agentId": row["agent_id"],
            "status": row["status"],
            "payload": json.loads(row["payload_json"]),
            "deliveryMessageId": row["delivery_message_id"],
        }

    def list_pending_outbound_messages(
        self,
        *,
        team_key: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT id, team_key, job_ref, message_kind, stage_index, agent_id,
                   payload_json, status, delivery_message_id, created_at, updated_at
            FROM outbound_messages
            WHERE status = 'pending'
        """
        params: list[Any] = []
        if team_key:
            sql += " AND team_key = ?"
            params.append(team_key)
        sql += " ORDER BY created_at ASC, id ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(max(int(limit), 1))
        rows = self._conn.execute(sql, tuple(params)).fetchall()
        return [
            {
                "id": row["id"],
                "teamKey": row["team_key"],
                "jobRef": row["job_ref"],
                "messageKind": row["message_kind"],
                "stageIndex": row["stage_index"],
                "agentId": row["agent_id"],
                "payload": json.loads(row["payload_json"]),
                "status": row["status"],
                "deliveryMessageId": row["delivery_message_id"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
            for row in rows
        ]

    def get_outbound_message(
        self,
        *,
        team_key: str,
        job_ref: str,
        message_kind: str,
        stage_index: int = -1,
        agent_id: str = "",
    ) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT id, team_key, job_ref, message_kind, stage_index, agent_id,
                   payload_json, status, delivery_message_id, created_at, updated_at
            FROM outbound_messages
            WHERE team_key = ? AND job_ref = ? AND message_kind = ? AND stage_index = ? AND agent_id = ?
            """,
            (team_key, job_ref, message_kind, stage_index, agent_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "teamKey": row["team_key"],
            "jobRef": row["job_ref"],
            "messageKind": row["message_kind"],
            "stageIndex": row["stage_index"],
            "agentId": row["agent_id"],
            "payload": json.loads(row["payload_json"]),
            "status": row["status"],
            "deliveryMessageId": row["delivery_message_id"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def mark_outbound_message_sent(
        self,
        *,
        team_key: str,
        job_ref: str,
        message_kind: str,
        stage_index: int = -1,
        agent_id: str = "",
        delivery_message_id: str,
    ) -> dict[str, Any]:
        self._conn.execute(
            """
            UPDATE outbound_messages
            SET status = 'sent',
                delivery_message_id = ?,
                updated_at = ?
            WHERE team_key = ? AND job_ref = ? AND message_kind = ? AND stage_index = ? AND agent_id = ?
            """,
            (
                str(delivery_message_id or "").strip(),
                now_iso(),
                team_key,
                job_ref,
                message_kind,
                stage_index,
                agent_id,
            ),
        )
        row = self._conn.execute(
            """
            SELECT id, team_key, job_ref, message_kind, stage_index, agent_id,
                   payload_json, status, delivery_message_id, created_at, updated_at
            FROM outbound_messages
            WHERE team_key = ? AND job_ref = ? AND message_kind = ? AND stage_index = ? AND agent_id = ?
            """,
            (team_key, job_ref, message_kind, stage_index, agent_id),
        ).fetchone()
        self._conn.commit()
        if row is None:
            raise RuntimeError("outbound message missing")
        return {
            "id": row["id"],
            "teamKey": row["team_key"],
            "jobRef": row["job_ref"],
            "messageKind": row["message_kind"],
            "stageIndex": row["stage_index"],
            "agentId": row["agent_id"],
            "payload": json.loads(row["payload_json"]),
            "status": row["status"],
            "deliveryMessageId": row["delivery_message_id"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def record_stage_callback(
        self,
        *,
        job_ref: str,
        stage_index: int,
        agent_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        timestamp = now_iso()
        cursor = self._conn.execute(
            """
            INSERT INTO stage_callbacks (
              job_ref, stage_index, agent_id, payload_json, publish_state, published_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'pending_publish', NULL, ?, ?)
            ON CONFLICT(job_ref, stage_index, agent_id) DO UPDATE SET
              payload_json = excluded.payload_json,
              publish_state = 'pending_publish',
              published_at = NULL,
              updated_at = excluded.updated_at
            """,
            (
                job_ref,
                stage_index,
                agent_id,
                json.dumps(payload, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )
        row = self._conn.execute(
            """
            SELECT job_ref, stage_index, agent_id, payload_json, publish_state, published_at, created_at, updated_at
            FROM stage_callbacks
            WHERE job_ref = ? AND stage_index = ? AND agent_id = ?
            """,
            (job_ref, stage_index, agent_id),
        ).fetchone()
        self._conn.commit()
        assert row is not None
        return {
            "created": cursor.rowcount == 1,
            "jobRef": row["job_ref"],
            "stageIndex": row["stage_index"],
            "agentId": row["agent_id"],
            "payload": json.loads(row["payload_json"]),
            "publishState": row["publish_state"],
            "publishedAt": row["published_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def list_stage_callbacks(self, *, job_ref: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT job_ref, stage_index, agent_id, payload_json, publish_state, published_at, created_at, updated_at
            FROM stage_callbacks
            WHERE job_ref = ?
            ORDER BY stage_index ASC, agent_id ASC
            """,
            (job_ref,),
        ).fetchall()
        return [
            {
                "jobRef": row["job_ref"],
                "stageIndex": row["stage_index"],
                "agentId": row["agent_id"],
                "payload": json.loads(row["payload_json"]),
                "publishState": row["publish_state"],
                "publishedAt": row["published_at"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
            for row in rows
        ]

    def get_stage_callback(
        self,
        *,
        job_ref: str,
        stage_index: int,
        agent_id: str,
    ) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT job_ref, stage_index, agent_id, payload_json, publish_state, published_at, created_at, updated_at
            FROM stage_callbacks
            WHERE job_ref = ? AND stage_index = ? AND agent_id = ?
            LIMIT 1
            """,
            (job_ref, stage_index, agent_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "jobRef": row["job_ref"],
            "stageIndex": row["stage_index"],
            "agentId": row["agent_id"],
            "payload": json.loads(row["payload_json"]),
            "publishState": row["publish_state"],
            "publishedAt": row["published_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def mark_stage_callback_published(
        self,
        *,
        job_ref: str,
        stage_index: int,
        agent_id: str,
    ) -> dict[str, Any]:
        self._conn.execute(
            """
            UPDATE stage_callbacks
            SET publish_state = 'published',
                published_at = ?,
                updated_at = ?
            WHERE job_ref = ? AND stage_index = ? AND agent_id = ?
            """,
            (
                now_iso(),
                now_iso(),
                job_ref,
                stage_index,
                agent_id,
            ),
        )
        self._conn.commit()
        callback = self.get_stage_callback(job_ref=job_ref, stage_index=stage_index, agent_id=agent_id)
        if callback is None:
            raise RuntimeError("stage callback missing")
        return callback

    def mark_stage_callback_publish_queued(
        self,
        *,
        job_ref: str,
        stage_index: int,
        agent_id: str,
    ) -> dict[str, Any]:
        self._conn.execute(
            """
            UPDATE stage_callbacks
            SET publish_state = 'queued_publish',
                updated_at = ?
            WHERE job_ref = ? AND stage_index = ? AND agent_id = ?
            """,
            (
                now_iso(),
                job_ref,
                stage_index,
                agent_id,
            ),
        )
        self._conn.commit()
        callback = self.get_stage_callback(job_ref=job_ref, stage_index=stage_index, agent_id=agent_id)
        if callback is None:
            raise RuntimeError("stage callback missing")
        return callback

    def create_publish_gate(
        self,
        *,
        job_ref: str,
        stage_key: str,
        mode: str,
        publish_order: list[str],
        stage_status: str = "pending",
    ) -> dict[str, Any]:
        if mode not in {"serial", "parallel"}:
            raise ValueError("publish gate mode must be serial or parallel")
        normalized_order = [str(item).strip() for item in publish_order if str(item).strip()]
        if not normalized_order:
            raise ValueError("publish_order must not be empty")
        timestamp = now_iso()
        self._conn.execute(
            """
            INSERT OR IGNORE INTO publish_gates (
              job_ref, stage_key, mode, publish_order_json, publish_cursor, stage_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                job_ref,
                stage_key,
                mode,
                json.dumps(normalized_order, ensure_ascii=False),
                stage_status,
                timestamp,
                timestamp,
            ),
        )
        row = self._conn.execute(
            """
            SELECT job_ref, stage_key, mode, publish_order_json, publish_cursor, stage_status, created_at, updated_at
            FROM publish_gates
            WHERE job_ref = ? AND stage_key = ?
            """,
            (job_ref, stage_key),
        ).fetchone()
        self._conn.commit()
        assert row is not None
        return {
            "jobRef": row["job_ref"],
            "stageKey": row["stage_key"],
            "mode": row["mode"],
            "publishOrder": json.loads(row["publish_order_json"]),
            "publishCursor": row["publish_cursor"],
            "stageStatus": row["stage_status"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "nextAgentId": json.loads(row["publish_order_json"])[row["publish_cursor"]]
            if row["publish_cursor"] < len(json.loads(row["publish_order_json"]))
            else None,
        }

    def update_publish_gate_state(
        self,
        *,
        job_ref: str,
        stage_key: str,
        stage_status: str,
    ) -> dict[str, Any]:
        self._conn.execute(
            """
            UPDATE publish_gates
            SET stage_status = ?, updated_at = ?
            WHERE job_ref = ? AND stage_key = ?
            """,
            (
                stage_status,
                now_iso(),
                job_ref,
                stage_key,
            ),
        )
        self._conn.commit()
        gate = self.get_publish_gate(job_ref=job_ref, stage_key=stage_key)
        if gate is None:
            raise RuntimeError("publish gate missing")
        return gate

    def get_publish_gate(self, *, job_ref: str, stage_key: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT job_ref, stage_key, mode, publish_order_json, publish_cursor, stage_status, created_at, updated_at
            FROM publish_gates
            WHERE job_ref = ? AND stage_key = ?
            """,
            (job_ref, stage_key),
        ).fetchone()
        if row is None:
            return None
        publish_order = json.loads(row["publish_order_json"])
        cursor = int(row["publish_cursor"])
        return {
            "jobRef": row["job_ref"],
            "stageKey": row["stage_key"],
            "mode": row["mode"],
            "publishOrder": publish_order,
            "publishCursor": cursor,
            "stageStatus": row["stage_status"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "nextAgentId": publish_order[cursor] if cursor < len(publish_order) else None,
        }

    def advance_publish_gate(
        self,
        *,
        job_ref: str,
        stage_key: str,
        published_agent_id: str,
    ) -> dict[str, Any]:
        gate = self.get_publish_gate(job_ref=job_ref, stage_key=stage_key)
        if gate is None:
            raise RuntimeError("publish gate missing")
        publish_order = gate["publishOrder"]
        cursor = int(gate["publishCursor"])
        expected_agent = publish_order[cursor] if cursor < len(publish_order) else None
        if expected_agent != published_agent_id:
            raise RuntimeError(
                f"publish gate out of order: expected={expected_agent or 'none'}, actual={published_agent_id}"
            )
        next_cursor = cursor + 1
        next_status = "completed" if next_cursor >= len(publish_order) else "publishing"
        self._conn.execute(
            """
            UPDATE publish_gates
            SET publish_cursor = ?, stage_status = ?, updated_at = ?
            WHERE job_ref = ? AND stage_key = ?
            """,
            (
                next_cursor,
                next_status,
                now_iso(),
                job_ref,
                stage_key,
            ),
        )
        self._conn.commit()
        updated = self.get_publish_gate(job_ref=job_ref, stage_key=stage_key)
        assert updated is not None
        return updated

    def acquire_controller_lock(self, *, team_key: str, owner: str, ttl_seconds: int) -> bool:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        expires_at = now + timedelta(seconds=max(ttl_seconds, 1))
        now_value = now.isoformat()
        expires_value = expires_at.isoformat()

        self._conn.execute(
            "DELETE FROM controller_locks WHERE team_key = ? AND expires_at <= ?",
            (team_key, now_value),
        )
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO controller_locks (team_key, owner, acquired_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (team_key, owner, now_value, expires_value),
        )
        self._conn.commit()
        return cursor.rowcount == 1
