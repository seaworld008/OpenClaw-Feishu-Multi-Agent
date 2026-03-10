#!/usr/bin/env python3
"""Reset OpenClaw Feishu team sessions after protocol changes or stuck runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core_openclaw_adapter import OpenClawAdapter, SessionTarget


def target_keys(
    group_peer_id: str,
    include_workers: bool,
    worker_agents: list[str],
    channel: str,
    supervisor_agent: str,
) -> list[tuple[str, str]]:
    keys = [(supervisor_agent, f"agent:{supervisor_agent}:{channel}:group:{group_peer_id}")]
    keys.append((supervisor_agent, f"agent:{supervisor_agent}:main"))
    if include_workers:
        for agent_id in worker_agents:
            keys.append((agent_id, f"agent:{agent_id}:main"))
            keys.append((agent_id, f"agent:{agent_id}:{channel}:group:{group_peer_id}"))
    return keys


def normalize_worker_agents(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def remove_session_keys(
    openclaw_home: Path,
    keys: list[tuple[str, str]],
    *,
    delete_transcripts: bool = False,
    dry_run: bool = False,
) -> list[dict]:
    adapter = OpenClawAdapter(openclaw_home=openclaw_home)
    return adapter.inspect_or_reset_session(
        targets=[SessionTarget(agent_id=agent_id, session_key=session_key) for agent_id, session_key in keys],
        action="reset",
        delete_transcripts=delete_transcripts,
        dry_run=dry_run,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", default="~/.openclaw")
    parser.add_argument("--group-peer-id", required=True)
    parser.add_argument("--channel", default="feishu")
    parser.add_argument("--team-key")
    parser.add_argument("--supervisor-agent", default="supervisor_agent")
    parser.add_argument("--include-workers", action="store_true")
    parser.add_argument("--worker-agents", default="ops_agent,finance_agent")
    parser.add_argument("--delete-transcripts", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    openclaw_home = Path(args.home).expanduser()
    worker_agents = normalize_worker_agents(args.worker_agents)
    results = remove_session_keys(
        openclaw_home,
        target_keys(
            args.group_peer_id,
            include_workers=args.include_workers,
            worker_agents=worker_agents,
            channel=args.channel,
            supervisor_agent=args.supervisor_agent,
        ),
        delete_transcripts=args.delete_transcripts,
        dry_run=args.dry_run,
    )

    print(
        json.dumps(
            {
                "home": str(openclaw_home),
                "teamKey": args.team_key,
                "groupPeerId": args.group_peer_id,
                "channel": args.channel,
                "supervisorAgent": args.supervisor_agent,
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
