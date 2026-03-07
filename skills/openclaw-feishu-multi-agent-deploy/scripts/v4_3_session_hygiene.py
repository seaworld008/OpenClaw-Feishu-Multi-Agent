#!/usr/bin/env python3
"""Reset V4.3.1 Feishu single-group sessions after protocol changes or stuck runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_sessions_index(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def dump_sessions_index(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def session_id_for(entry) -> str | None:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return entry.get("sessionId")
    return None


def session_file_for(base_dir: Path, entry) -> Path | None:
    if isinstance(entry, dict):
        raw = entry.get("sessionFile")
        if raw:
            return Path(raw).expanduser()
    session_id = session_id_for(entry)
    if not session_id:
        return None
    return base_dir / f"{session_id}.jsonl"


def target_keys(group_peer_id: str, include_workers: bool, worker_agents: list[str], channel: str) -> list[tuple[str, str]]:
    keys = [("supervisor_agent", f"agent:supervisor_agent:{channel}:group:{group_peer_id}")]
    keys.append(("supervisor_agent", "agent:supervisor_agent:main"))
    if include_workers:
        for agent_id in worker_agents:
            keys.append((agent_id, f"agent:{agent_id}:{channel}:group:{group_peer_id}"))
    return keys


def normalize_worker_agents(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", default="~/.openclaw")
    parser.add_argument("--group-peer-id", required=True)
    parser.add_argument("--channel", default="feishu")
    parser.add_argument("--include-workers", action="store_true")
    parser.add_argument("--worker-agents", default="ops_agent,finance_agent")
    parser.add_argument("--delete-transcripts", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    openclaw_home = Path(args.home).expanduser()
    worker_agents = normalize_worker_agents(args.worker_agents)
    results: list[dict] = []

    for agent_id, session_key in target_keys(
        args.group_peer_id,
        include_workers=args.include_workers,
        worker_agents=worker_agents,
        channel=args.channel,
    ):
        session_dir = openclaw_home / "agents" / agent_id / "sessions"
        index_path = session_dir / "sessions.json"
        if not index_path.exists():
            results.append(
                {
                    "agentId": agent_id,
                    "sessionKey": session_key,
                    "status": "index_missing",
                }
            )
            continue

        index_payload = load_sessions_index(index_path)
        entry = index_payload.get(session_key)
        if entry is None:
            results.append(
                {
                    "agentId": agent_id,
                    "sessionKey": session_key,
                    "status": "mapping_missing",
                }
            )
            continue

        transcript_path = session_file_for(session_dir, entry)
        result = {
            "agentId": agent_id,
            "sessionKey": session_key,
            "status": "removed" if not args.dry_run else "would_remove",
            "sessionId": session_id_for(entry),
        }

        if transcript_path is not None:
            result["transcript"] = str(transcript_path)
            if args.delete_transcripts and transcript_path.exists():
                result["transcriptStatus"] = "deleted" if not args.dry_run else "would_delete"
            elif args.delete_transcripts:
                result["transcriptStatus"] = "missing"

        if not args.dry_run:
            index_payload.pop(session_key, None)
            dump_sessions_index(index_path, index_payload)
            if args.delete_transcripts and transcript_path is not None and transcript_path.exists():
                transcript_path.unlink()

        results.append(result)

    print(
        json.dumps(
            {
                "home": str(openclaw_home),
                "groupPeerId": args.group_peer_id,
                "channel": args.channel,
                "includeWorkers": args.include_workers,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
