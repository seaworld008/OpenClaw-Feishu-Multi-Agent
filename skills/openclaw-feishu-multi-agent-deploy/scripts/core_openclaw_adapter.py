#!/usr/bin/env python3
"""Narrow OpenClaw platform adapter for message delivery, agent invoke, and session access."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator


@dataclass(frozen=True)
class SessionTarget:
    agent_id: str
    session_key: str


@dataclass(frozen=True)
class CapturedInboundEvent:
    source_message_id: str
    requested_by: str
    request_text: str
    supervisor_spawned_session_keys: tuple[str, ...] = ()


class OpenClawAdapter:
    def __init__(
        self,
        *,
        openclaw_home: Path,
        openclaw_bin: str | Path = "openclaw",
        timeout_seconds: int = 90,
    ) -> None:
        self.openclaw_home = Path(openclaw_home).expanduser()
        self.openclaw_bin = str(openclaw_bin)
        self.timeout_seconds = int(timeout_seconds)

    def send_message(self, *, channel: str, account_id: str, target: str, message: str) -> dict[str, Any]:
        return self._run_json_command(
            [
                self.openclaw_bin,
                "message",
                "send",
                "--channel",
                str(channel),
                "--account",
                str(account_id),
                "--target",
                str(target),
                "--message",
                str(message),
                "--json",
            ]
        )

    def invoke_agent(self, *, agent_id: str, message: str) -> dict[str, Any]:
        return self._run_json_command(
            [
                self.openclaw_bin,
                "agent",
                "--agent",
                str(agent_id),
                "--message",
                str(message),
                "--json",
            ]
        )

    def capture_inbound_event(self, *, agent_id: str, session_key: str) -> CapturedInboundEvent | None:
        events = self.capture_inbound_events(agent_id=agent_id, session_key=session_key)
        if not events:
            return None
        return events[-1]

    def capture_inbound_events(self, *, agent_id: str, session_key: str) -> tuple[CapturedInboundEvent, ...]:
        entries = self.load_session_entries(agent_id=agent_id, session_key=session_key)
        if not entries:
            return ()

        user_entries: list[tuple[int, CapturedInboundEvent]] = []
        for index, entry in enumerate(entries):
            if entry.get("type") != "message":
                continue
            message = entry.get("message")
            if not isinstance(message, dict) or str(message.get("role") or "") != "user":
                continue
            pending = self._parse_pending_inbound(self._extract_text_content(message))
            if pending is None:
                continue
            user_entries.append(
                (
                    index,
                    CapturedInboundEvent(
                        source_message_id=pending["source_message_id"],
                        requested_by=pending["requested_by"],
                        request_text=pending["request_text"],
                    ),
                )
            )

        if not user_entries:
            return ()

        events: list[CapturedInboundEvent] = []
        for offset, (entry_index, event) in enumerate(user_entries):
            next_entry_index = user_entries[offset + 1][0] if offset + 1 < len(user_entries) else len(entries)
            spawned = self._extract_spawned_session_keys(entries[entry_index + 1 : next_entry_index])
            events.append(
                CapturedInboundEvent(
                    source_message_id=event.source_message_id,
                    requested_by=event.requested_by,
                    request_text=event.request_text,
                    supervisor_spawned_session_keys=spawned,
                )
            )
        return tuple(events)

    def inspect_or_reset_session(
        self,
        *,
        targets: Iterable[SessionTarget],
        action: str,
        delete_transcripts: bool = False,
        dry_run: bool = False,
    ) -> list[dict[str, Any]]:
        if action not in {"inspect", "reset"}:
            raise ValueError(f"unsupported session action: {action}")

        results: list[dict[str, Any]] = []
        for target in targets:
            session_dir = self._sessions_dir(target.agent_id)
            index_path = session_dir / "sessions.json"
            if not index_path.exists():
                results.append(
                    {
                        "agentId": target.agent_id,
                        "sessionKey": target.session_key,
                        "status": "index_missing",
                    }
                )
                continue

            sessions_index = self._load_sessions_index(index_path)
            entry = sessions_index.get(target.session_key)
            if entry is None:
                results.append(
                    {
                        "agentId": target.agent_id,
                        "sessionKey": target.session_key,
                        "status": "mapping_missing",
                    }
                )
                continue

            transcript_path = self._session_file_for(session_dir, entry)
            result = {
                "agentId": target.agent_id,
                "sessionKey": target.session_key,
                "status": "present" if action == "inspect" else ("would_remove" if dry_run else "removed"),
                "sessionId": self._session_id_for(entry),
            }
            if transcript_path is not None:
                result["transcript"] = str(transcript_path)
                if action == "reset" and delete_transcripts:
                    if transcript_path.exists():
                        result["transcriptStatus"] = "would_delete" if dry_run else "deleted"
                    else:
                        result["transcriptStatus"] = "missing"

            if action == "reset" and not dry_run:
                sessions_index.pop(target.session_key, None)
                self._dump_sessions_index(index_path, sessions_index)
                if delete_transcripts and transcript_path is not None and transcript_path.exists():
                    transcript_path.unlink()

            results.append(result)
        return results

    def load_session_entries(self, *, agent_id: str, session_key: str) -> list[dict[str, Any]]:
        transcript_path = self.resolve_session_transcript_path(agent_id=agent_id, session_key=session_key)
        if transcript_path is None:
            return []
        entries: list[dict[str, Any]] = []
        for line in transcript_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                entries.append(payload)
        return entries

    def resolve_session_transcript_path(self, *, agent_id: str, session_key: str) -> Path | None:
        session_dir = self._sessions_dir(agent_id)
        index_path = session_dir / "sessions.json"
        if not index_path.exists():
            return None
        sessions_index = self._load_sessions_index(index_path)
        entry = sessions_index.get(session_key)
        if entry is None:
            return None
        transcript_path = self._session_file_for(session_dir, entry)
        if transcript_path is None or not transcript_path.exists():
            return None
        return transcript_path

    def iter_session_text_files(self, agent_id: str) -> Iterator[tuple[Path, str]]:
        session_dir = self._sessions_dir(agent_id)
        if not session_dir.exists():
            return
        for transcript_path in session_dir.glob("*.jsonl"):
            try:
                yield transcript_path, transcript_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

    def _run_json_command(self, command: list[str]) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"OpenClaw command timed out after {self.timeout_seconds}s: {' '.join(command)}"
            ) from exc
        if completed.returncode != 0:
            raise RuntimeError(
                f"OpenClaw command failed ({completed.returncode}): {' '.join(command)}\n"
                f"{completed.stderr or completed.stdout}"
            )
        payload = self._parse_last_json_blob(completed.stdout)
        if not isinstance(payload, dict):
            raise RuntimeError(f"OpenClaw command did not return JSON object: {' '.join(command)}")
        return payload

    def _sessions_dir(self, agent_id: str) -> Path:
        return self.openclaw_home / "agents" / str(agent_id) / "sessions"

    @staticmethod
    def _load_sessions_index(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _dump_sessions_index(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _session_id_for(entry: Any) -> str | None:
        if isinstance(entry, str):
            return entry
        if isinstance(entry, dict):
            value = str(entry.get("sessionId") or "").strip()
            return value or None
        return None

    @staticmethod
    def _expand_path(raw: str, *, base: Path | None = None) -> Path:
        path = Path(raw).expanduser()
        if path.is_absolute():
            return path
        if base is not None:
            return (base / path).resolve()
        return path.resolve()

    @classmethod
    def _session_file_for(cls, base_dir: Path, entry: Any) -> Path | None:
        if isinstance(entry, dict):
            raw = str(entry.get("sessionFile") or "").strip()
            if raw:
                return cls._expand_path(raw, base=base_dir)
        session_id = cls._session_id_for(entry)
        if not session_id:
            return None
        return base_dir / f"{session_id}.jsonl"

    @staticmethod
    def _parse_last_json_blob(text: str) -> Any:
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

    @staticmethod
    def _extract_text_content(message: dict[str, Any]) -> str:
        content = message.get("content")
        if not isinstance(content, list):
            return ""
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(str(item.get("text") or ""))
        return "\n".join(chunk for chunk in chunks if chunk)

    @staticmethod
    def _parse_pending_inbound(raw_text: str) -> dict[str, str] | None:
        normalized_text = raw_text.replace("\\r\\n", "\n").replace("\\n", "\n")
        lines = normalized_text.splitlines()
        body_start = None
        source_message_id = ""
        for index, line in enumerate(lines):
            normalized = line.rstrip()
            if normalized.startswith("[message_id: ") and normalized.endswith("]"):
                source_message_id = normalized[len("[message_id: ") : -1].strip()
                body_start = index + 1
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
        return {
            "source_message_id": source_message_id,
            "requested_by": requested_by.strip() or "unknown",
            "request_text": request_text,
        }

    @classmethod
    def _extract_spawned_session_keys(cls, entries: list[dict[str, Any]]) -> tuple[str, ...]:
        keys: list[str] = []
        seen: set[str] = set()
        for entry in entries:
            if entry.get("type") != "message":
                continue
            message = entry.get("message")
            if not isinstance(message, dict):
                continue
            if str(message.get("role") or "") != "toolResult":
                continue
            if str(message.get("toolName") or "") != "sessions_spawn":
                continue
            child_session_key = cls._extract_child_session_key_from_tool_result(message)
            if not child_session_key or child_session_key in seen:
                continue
            seen.add(child_session_key)
            keys.append(child_session_key)
        return tuple(keys)

    @classmethod
    def _extract_child_session_key_from_tool_result(cls, message: dict[str, Any]) -> str:
        found = cls._extract_child_session_key(message.get("details"))
        if found:
            return found
        found = cls._extract_child_session_key(message)
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
                parsed = cls._parse_last_json_blob(raw_text)
            except ValueError:
                continue
            found = cls._extract_child_session_key(parsed)
            if found:
                return found
        return ""

    @classmethod
    def _extract_child_session_key(cls, payload: Any) -> str:
        if isinstance(payload, dict):
            for key in ("childSessionKey", "child_session_key"):
                value = str(payload.get(key) or "").strip()
                if value:
                    return value
            for value in payload.values():
                found = cls._extract_child_session_key(value)
                if found:
                    return found
        elif isinstance(payload, list):
            for item in payload:
                found = cls._extract_child_session_key(item)
                if found:
                    return found
        return ""
