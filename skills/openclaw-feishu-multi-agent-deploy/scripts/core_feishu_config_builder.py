#!/usr/bin/env python3
"""Build OpenClaw Feishu config snippets from deployment input JSON.

Usage:
  python3 scripts/core_feishu_config_builder.py \
    --input references/input-template.json \
    --out references/generated
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple


PLUGIN_CHANNEL = "feishu"
LEGACY_CHANNEL = "chat-feishu"
TEAM_KEY_RE = re.compile(r"^[a-z0-9_]+$")


def load_json(path: pathlib.Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Input JSON must be an object")
    return data


def require(data: Dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"Missing required field: {key}")
    return data[key]


def route_sort_key(route: Dict[str, Any]) -> Tuple[int, int, int]:
    """Sort bindings by specificity: peer > accountId > wildcard/fallback."""
    peer = route.get("peer") if isinstance(route, dict) else None
    account_id = route.get("accountId") if isinstance(route, dict) else None
    has_peer = 0 if isinstance(peer, dict) and peer.get("id") else 1
    has_specific_account = 0 if account_id and account_id != "*" else 1
    has_channel = 0 if route.get("channel") else 1
    return (has_peer, has_specific_account, has_channel)


def validate_accounts(accounts: Any) -> List[Dict[str, Any]]:
    if not isinstance(accounts, list) or not accounts:
        raise ValueError("accounts must be a non-empty array")
    required = ["accountId", "appId", "appSecret"]
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for idx, account in enumerate(accounts):
        if not isinstance(account, dict):
            raise ValueError(f"accounts[{idx}] must be an object")
        for k in required:
            if not account.get(k):
                raise ValueError(f"accounts[{idx}] missing required field: {k}")
        account_id = str(account["accountId"])
        if account_id in seen:
            raise ValueError(f"Duplicate accountId: {account_id}")
        seen.add(account_id)
        out.append(account)
    return out


def build_account_cfg(account: Dict[str, Any]) -> Dict[str, Any]:
    account_cfg = {
        "appId": account["appId"],
        "appSecret": account["appSecret"],
    }
    for key in ["encryptKey", "verificationToken"]:
        value = account.get(key)
        if value:
            account_cfg[key] = value
    if isinstance(account.get("overrides"), dict):
        account_cfg.update(account["overrides"])
    return account_cfg


def build_agents_patch(agents: Any) -> Dict[str, Any] | None:
    if isinstance(agents, dict):
        out: Dict[str, Any] = {}
        defaults = agents.get("defaults")
        if defaults is not None:
            if not isinstance(defaults, dict):
                raise ValueError("agents.defaults must be an object")
            out["defaults"] = defaults
        agent_list = agents.get("list")
        if agent_list is None:
            return out or None
        if not isinstance(agent_list, list) or not agent_list:
            raise ValueError("agents.list must be a non-empty array")
        if all(isinstance(agent, dict) and agent.get("id") for agent in agent_list):
            out["list"] = agent_list
            return out
        if all(isinstance(agent, str) and agent for agent in agent_list):
            return out or None
        raise ValueError("agents.list must be either a list of agent ids or a list of agent objects with id")
    if not isinstance(agents, list) or not agents:
        return None
    if all(isinstance(agent, dict) and agent.get("id") for agent in agents):
        return {"list": agents}
    if all(isinstance(agent, str) and agent for agent in agents):
        return None
    raise ValueError("agents must be either a list of agent ids or a list of agent objects with id")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "agent"


def build_team_role_key(team_key: str, agent: Dict[str, Any], default_role_key: str) -> str:
    explicit = agent.get("roleKey")
    if explicit:
        return slugify(str(explicit))

    agent_id = str(agent.get("agentId") or "").strip()
    candidate = str(default_role_key or agent_id).strip()
    suffix = f"_{team_key}"
    if candidate == agent_id and agent_id.endswith(suffix):
        candidate = agent_id[: -len(suffix)]
    return slugify(candidate)


def build_agent_identity(agent: Dict[str, Any]) -> Dict[str, Any] | None:
    raw = agent.get("identity")
    if not isinstance(raw, dict):
        return None
    identity = {
        key: value
        for key, value in raw.items()
        if key in {"name", "theme", "emoji", "avatar"} and value
    }
    return identity or None


def build_team_agent_record(team_key: str, agent: Dict[str, Any], default_role_key: str) -> Dict[str, Any]:
    role_key = build_team_role_key(team_key, agent, default_role_key)
    identity = build_agent_identity(agent)
    record: Dict[str, Any] = {
        "id": agent["agentId"],
        "name": agent.get("name") or (identity or {}).get("name") or agent.get("role") or agent["agentId"],
        "workspace": agent.get("workspace") or f"~/.openclaw/teams/{team_key}/workspaces/{role_key}",
        "agentDir": agent.get("agentDir") or f"~/.openclaw/teams/{team_key}/agents/{role_key}/agent",
    }
    if identity:
        record["identity"] = identity
    if agent.get("mentionPatterns"):
        record["groupChat"] = {"mentionPatterns": list(agent["mentionPatterns"])}
    return record


def validate_teams(teams: Any, account_ids: set[str]) -> List[Dict[str, Any]]:
    if not isinstance(teams, list) or not teams:
        raise ValueError("teams must be a non-empty array")

    seen_team_keys: set[str] = set()
    seen_group_peer_ids: set[str] = set()
    seen_agent_ids: set[str] = set()
    validated: List[Dict[str, Any]] = []

    for idx, team in enumerate(teams):
        if not isinstance(team, dict):
            raise ValueError(f"teams[{idx}] must be an object")

        team_key = str(team.get("teamKey") or "").strip()
        if not team_key:
            raise ValueError(f"teams[{idx}] missing required field: teamKey")
        if not TEAM_KEY_RE.fullmatch(team_key):
            raise ValueError(f"teams[{idx}].teamKey must match {TEAM_KEY_RE.pattern}")
        if team_key in seen_team_keys:
            raise ValueError(f"Duplicate teamKey: {team_key}")
        seen_team_keys.add(team_key)

        group = team.get("group")
        if not isinstance(group, dict):
            raise ValueError(f"teams[{idx}].group must be an object")
        peer_id = str(group.get("peerId") or "").strip()
        entry_account_id = str(group.get("entryAccountId") or "").strip()
        if not peer_id or not entry_account_id:
            raise ValueError(f"teams[{idx}].group.peerId and teams[{idx}].group.entryAccountId are required")
        if entry_account_id not in account_ids:
            raise ValueError(f"teams[{idx}] references unknown accountId: {entry_account_id}")
        if peer_id in seen_group_peer_ids:
            raise ValueError(f"Duplicate group.peerId across teams: {peer_id}")
        seen_group_peer_ids.add(peer_id)

        supervisor = team.get("supervisor")
        if not isinstance(supervisor, dict):
            raise ValueError(f"teams[{idx}].supervisor must be an object")
        if not supervisor.get("agentId") or not supervisor.get("systemPrompt"):
            raise ValueError(f"teams[{idx}].supervisor.agentId and systemPrompt are required")
        supervisor_account_id = str(supervisor.get("accountId") or entry_account_id)
        if supervisor_account_id not in account_ids:
            raise ValueError(f"teams[{idx}] references unknown supervisor accountId: {supervisor_account_id}")

        workers = team.get("workers")
        if not isinstance(workers, list) or not workers:
            raise ValueError(f"teams[{idx}].workers must be a non-empty array")

        account_peer_pairs = {(supervisor_account_id, peer_id)}
        team_agent_ids = [str(supervisor["agentId"])]

        for agent_id in team_agent_ids:
            if agent_id in seen_agent_ids:
                raise ValueError(f"Duplicate agentId across teams: {agent_id}")
            seen_agent_ids.add(agent_id)

        normalized_workers: List[Dict[str, Any]] = []
        for worker_idx, worker in enumerate(workers):
            if not isinstance(worker, dict):
                raise ValueError(f"teams[{idx}].workers[{worker_idx}] must be an object")
            worker_agent_id = str(worker.get("agentId") or "").strip()
            worker_account_id = str(worker.get("accountId") or "").strip()
            if not worker_agent_id or not worker_account_id or not worker.get("systemPrompt"):
                raise ValueError(
                    f"teams[{idx}].workers[{worker_idx}] requires agentId, accountId and systemPrompt"
                )
            if worker_account_id not in account_ids:
                raise ValueError(f"teams[{idx}] references unknown worker accountId: {worker_account_id}")
            if worker_agent_id in seen_agent_ids:
                raise ValueError(f"Duplicate agentId across teams: {worker_agent_id}")
            seen_agent_ids.add(worker_agent_id)
            if (worker_account_id, peer_id) in account_peer_pairs:
                raise ValueError(
                    f"teams[{idx}] reuses accountId {worker_account_id} in group {peer_id}; account+group must map to exactly one agent"
                )
            visibility = str(worker.get("visibility") or "visible").strip()
            if visibility not in {"visible", "hidden"}:
                raise ValueError(f"teams[{idx}].workers[{worker_idx}].visibility must be visible or hidden")
            account_peer_pairs.add((worker_account_id, peer_id))
            normalized_workers.append(worker)

        workflow = team.get("workflow")
        if not isinstance(workflow, dict):
            raise ValueError(f"teams[{idx}].workflow must be an object")
        mode = str(workflow.get("mode") or "serial").strip()
        if mode not in {"serial", "parallel"}:
            raise ValueError(f"teams[{idx}].workflow.mode must be serial or parallel")
        stages = workflow.get("stages")
        if not isinstance(stages, list) or not stages:
            raise ValueError(f"teams[{idx}].workflow.stages must be a non-empty array")
        valid_stage_agent_ids = {str(worker["agentId"]) for worker in normalized_workers}
        stage_agent_ids: List[str] = []
        for stage_idx, stage in enumerate(stages):
            if not isinstance(stage, dict) or not stage.get("agentId"):
                raise ValueError(f"teams[{idx}].workflow.stages[{stage_idx}] requires agentId")
            stage_agent_id = str(stage["agentId"])
            if stage_agent_id not in valid_stage_agent_ids:
                raise ValueError(
                    f"teams[{idx}].workflow.stages[{stage_idx}].agentId must reference a worker in the same team"
                )
            if stage_agent_id in stage_agent_ids:
                raise ValueError(
                    f"teams[{idx}].workflow.stages contains duplicate agentId: {stage_agent_id}"
                )
            stage_agent_ids.append(stage_agent_id)
        missing_stage_agents = sorted(valid_stage_agent_ids - set(stage_agent_ids))
        if missing_stage_agents:
            raise ValueError(
                f"teams[{idx}].workflow.stages must include every worker agentId exactly once; "
                f"missing: {', '.join(missing_stage_agents)}"
            )

        validated.append(team)

    return validated


def build_messages_patch(data: Dict[str, Any], teams: List[Dict[str, Any]] | None = None) -> Dict[str, Any] | None:
    out = dict(data["messages"]) if isinstance(data.get("messages"), dict) else {}
    mention_patterns: List[str] = []
    group_chat = out.get("groupChat")
    if isinstance(group_chat, dict) and isinstance(group_chat.get("mentionPatterns"), list):
        mention_patterns.extend([str(item) for item in group_chat["mentionPatterns"] if str(item).strip()])
    if teams:
        for team in teams:
            supervisor = team.get("supervisor")
            if not isinstance(supervisor, dict):
                continue
            for item in supervisor.get("mentionPatterns") or []:
                text = str(item).strip()
                if text and text not in mention_patterns:
                    mention_patterns.append(text)
    if mention_patterns:
        out.setdefault("groupChat", {})["mentionPatterns"] = mention_patterns
    return out or None


def build_v5_runtime_manifest(data: Dict[str, Any]) -> Dict[str, Any]:
    accounts = validate_accounts(require(data, "accounts"))
    account_ids = {str(account["accountId"]) for account in accounts}
    teams = validate_teams(require(data, "teams"), account_ids)
    manifest_teams: List[Dict[str, Any]] = []

    for team in teams:
        team_key = str(team["teamKey"])
        group = team["group"]
        peer_id = str(group["peerId"])
        supervisor = team["supervisor"]
        supervisor_account_id = str(supervisor.get("accountId") or group["entryAccountId"])
        supervisor_record = build_team_agent_record(team_key, supervisor, "supervisor")
        allowed_worker_agent_ids: List[str] = []
        worker_records: List[Dict[str, Any]] = []
        worker_session_keys: List[str] = []

        for worker in team["workers"]:
            worker_record = build_team_agent_record(team_key, worker, worker["agentId"])
            worker_agent_id = str(worker_record["id"])
            worker_session_key = f"agent:{worker_agent_id}:{PLUGIN_CHANNEL}:group:{peer_id}"
            allowed_worker_agent_ids.append(worker_agent_id)
            worker_session_keys.append(worker_session_key)
            worker_records.append(
                {
                    "agentId": worker_agent_id,
                    "accountId": worker["accountId"],
                    "name": worker_record["name"],
                    "description": worker.get("description"),
                    "identity": worker_record.get("identity"),
                    "role": worker.get("role"),
                    "responsibility": worker.get("responsibility"),
                    "visibility": worker.get("visibility", "visible"),
                    "workspace": worker_record["workspace"],
                    "agentDir": worker_record["agentDir"],
                    "groupSessionKey": worker_session_key,
                    "systemPrompt": worker["systemPrompt"],
                }
            )

        hidden_main = f"agent:{supervisor_record['id']}:main"
        manifest_teams.append(
            {
                "teamKey": team_key,
                "displayName": team.get("displayName") or team_key,
                "group": {
                    "peerId": peer_id,
                    "entryAccountId": group["entryAccountId"],
                    "requireMention": group.get("requireMention"),
                },
                "supervisor": {
                    "agentId": supervisor_record["id"],
                    "accountId": supervisor_account_id,
                    "name": supervisor_record["name"],
                    "description": supervisor.get("description"),
                    "identity": supervisor_record.get("identity"),
                    "role": supervisor.get("role"),
                    "responsibility": supervisor.get("responsibility"),
                    "mentionPatterns": list(supervisor.get("mentionPatterns") or []),
                    "workspace": supervisor_record["workspace"],
                    "agentDir": supervisor_record["agentDir"],
                    "hiddenMainSessionKey": hidden_main,
                    "allowedWorkerAgentIds": allowed_worker_agent_ids,
                    "systemPrompt": supervisor["systemPrompt"],
                },
                "workers": worker_records,
                "workflow": team["workflow"],
                "runtime": {
                    "orchestratorVersion": "V5.1 Hardening",
                    "dbPath": f"~/.openclaw/teams/{team_key}/state/team_jobs.db",
                    "hiddenMainSessionKey": hidden_main,
                    "entryAccountId": group["entryAccountId"],
                    "entryChannel": PLUGIN_CHANNEL,
                    "entryTarget": f"chat:{peer_id}",
                    "controlPlane": {
                        "registryScript": "skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py",
                        "reconcileScript": "skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py",
                        "commands": {
                            "startJob": "start-job-with-workflow",
                            "nextAction": "get-next-action",
                            "buildDispatchPayload": "build-dispatch-payload",
                            "buildVisibleAck": "build-visible-ack",
                            "buildRollupContext": "build-rollup-context",
                            "buildRollupVisibleMessage": "build-rollup-visible-message",
                            "recordVisibleMessage": "record-visible-message",
                            "readyToRollup": "ready-to-rollup",
                            "reconcileDispatch": "reconcile-dispatch",
                            "reconcileRollup": "reconcile-rollup",
                            "resumeJob": "resume-job",
                        },
                    },
                    "sessionKeys": {
                        "supervisorGroup": f"agent:{supervisor_record['id']}:{PLUGIN_CHANNEL}:group:{peer_id}",
                        "supervisorMain": hidden_main,
                        "workers": worker_session_keys,
                    },
                    "watchdog": {
                        "systemdServiceTemplate": "skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v5-team-watchdog.service",
                        "systemdTimerTemplate": "skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v5-team-watchdog.timer",
                        "launchdTemplate": "skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v5-team-watchdog.plist",
                        "systemdServiceName": f"v5-team-{team_key}.service",
                        "systemdTimerName": f"v5-team-{team_key}.timer",
                        "launchdLabel": f"bot.molt.v5-team-{team_key}",
                    },
                },
            }
        )

    return {
        "versionLine": "V5 Team Orchestrator / V5.1 Hardening",
        "orchestratorVersion": "V5.1 Hardening",
        "teamCount": len(manifest_teams),
        "teams": manifest_teams,
    }


def build_v5_plugin_patch(data: Dict[str, Any], accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
    account_ids = {str(account["accountId"]) for account in accounts}
    teams = validate_teams(require(data, "teams"), account_ids)
    optional = data.get("optional") if isinstance(data.get("optional"), dict) else {}

    feishu: Dict[str, Any] = {
        "enabled": True,
        "connectionMode": data.get("connectionMode", "websocket"),
        "accounts": {},
    }

    for key in [
        "domain",
        "defaultAccount",
        "dmPolicy",
        "allowFrom",
        "groupPolicy",
        "groupAllowFrom",
    ]:
        if key in data:
            feishu[key] = data[key]

    if "defaultAccount" not in feishu:
        feishu["defaultAccount"] = accounts[0]["accountId"]

    for key in ["requireMention", "allowMentionlessInMultiBotGroup", "groupCommandMentionBypass"]:
        if key in optional:
            feishu[key] = optional[key]

    group_overrides: Dict[str, Dict[str, Any]] = {}
    for account in accounts:
        account_id = str(account["accountId"])
        feishu["accounts"][account_id] = build_account_cfg(account)

    agents_list: List[Dict[str, Any]] = []
    bindings: List[Dict[str, Any]] = []
    generated_agent_ids: List[str] = []

    for team in teams:
        team_key = str(team["teamKey"])
        group = team["group"]
        peer_id = str(group["peerId"])
        supervisor = team["supervisor"]
        supervisor_account_id = str(supervisor.get("accountId") or group["entryAccountId"])
        supervisor_record = build_team_agent_record(team_key, supervisor, "supervisor")
        agents_list.append(supervisor_record)
        generated_agent_ids.append(supervisor_record["id"])
        bindings.append(
            {
                "agentId": supervisor_record["id"],
                "match": {
                    "channel": PLUGIN_CHANNEL,
                    "accountId": supervisor_account_id,
                    "peer": {"kind": "group", "id": peer_id},
                },
            }
        )
        feishu["accounts"][supervisor_account_id].setdefault("groups", {})[peer_id] = {
            "systemPrompt": supervisor["systemPrompt"]
        }
        if "requireMention" in group:
            group_overrides.setdefault(peer_id, {})["requireMention"] = group["requireMention"]

        for worker in team["workers"]:
            worker_account_id = str(worker["accountId"])
            worker_record = build_team_agent_record(team_key, worker, worker["agentId"])
            agents_list.append(worker_record)
            generated_agent_ids.append(worker_record["id"])
            bindings.append(
                {
                    "agentId": worker_record["id"],
                    "match": {
                        "channel": PLUGIN_CHANNEL,
                        "accountId": worker_account_id,
                        "peer": {"kind": "group", "id": peer_id},
                    },
                }
            )
            feishu["accounts"][worker_account_id].setdefault("groups", {})[peer_id] = {
                "systemPrompt": worker["systemPrompt"]
            }

    if group_overrides:
        feishu["groups"] = group_overrides

    agents_patch = build_agents_patch(data.get("agents")) or {}
    if agents_patch.get("list"):
        raise ValueError("V5 teams input must not provide agents.list; team agents are generated from teams")
    agents_patch["list"] = agents_list

    patch: Dict[str, Any] = {
        "channels": {"feishu": feishu},
        "bindings": bindings,
        "agents": agents_patch,
    }

    tools_patch: Dict[str, Any] = {}
    if isinstance(data.get("agentToAgent"), dict) and data["agentToAgent"]:
        agent_to_agent = dict(data["agentToAgent"])
        if agent_to_agent.get("enabled") and not agent_to_agent.get("allow"):
            agent_to_agent["allow"] = generated_agent_ids
        tools_patch["agentToAgent"] = agent_to_agent
    if isinstance(data.get("tools"), dict):
        tools = data["tools"]
        if isinstance(tools.get("allow"), list) and tools["allow"]:
            tools_patch["allow"] = tools["allow"]
        if isinstance(tools.get("sessions"), dict) and tools["sessions"]:
            tools_patch["sessions"] = tools["sessions"]
    if tools_patch:
        patch["tools"] = tools_patch

    if isinstance(data.get("session"), dict) and data["session"]:
        patch["session"] = data["session"]

    messages_patch = build_messages_patch(data, teams)
    if messages_patch:
        patch["messages"] = messages_patch

    return patch


def validate_routes(routes: Any) -> List[Dict[str, Any]]:
    if not isinstance(routes, list) or not routes:
        raise ValueError("routes must be a non-empty array")
    out: List[Dict[str, Any]] = []
    for idx, route in enumerate(routes):
        if not isinstance(route, dict):
            raise ValueError(f"routes[{idx}] must be an object")
        for k in ["agentId", "accountId", "peer"]:
            if k not in route:
                raise ValueError(f"routes[{idx}] missing required field: {k}")
        peer = route.get("peer")
        if not isinstance(peer, dict):
            raise ValueError(f"routes[{idx}].peer must be an object")
        if not peer.get("kind") or not peer.get("id"):
            raise ValueError(f"routes[{idx}].peer.kind and routes[{idx}].peer.id are required")
        out.append(route)
    out.sort(key=route_sort_key)
    return out


def build_plugin_patch(data: Dict[str, Any]) -> Dict[str, Any]:
    accounts = validate_accounts(require(data, "accounts"))
    if data.get("teams") is not None:
        return build_v5_plugin_patch(data, accounts)

    routes = validate_routes(require(data, "routes"))

    optional = data.get("optional") if isinstance(data.get("optional"), dict) else {}

    feishu: Dict[str, Any] = {
        "enabled": True,
        "connectionMode": data.get("connectionMode", "websocket"),
        "accounts": {},
    }

    for key in [
        "domain",
        "defaultAccount",
        "dmPolicy",
        "allowFrom",
        "groupPolicy",
        "groupAllowFrom",
    ]:
        if key in data:
            feishu[key] = data[key]

    if "defaultAccount" not in feishu:
        feishu["defaultAccount"] = accounts[0]["accountId"]

    for key in ["requireMention", "allowMentionlessInMultiBotGroup", "groupCommandMentionBypass"]:
        if key in optional:
            feishu[key] = optional[key]

    if isinstance(optional.get("groups"), dict) and optional["groups"]:
        feishu["groups"] = optional["groups"]

    for account in accounts:
        account_id = account["accountId"]
        feishu["accounts"][account_id] = build_account_cfg(account)

    bindings: List[Dict[str, Any]] = []
    for route in routes:
        bindings.append(
            {
                "agentId": route["agentId"],
                "match": {
                    "channel": route.get("channel") or PLUGIN_CHANNEL,
                    "accountId": route["accountId"],
                    "peer": {
                        "kind": route["peer"]["kind"],
                        "id": route["peer"]["id"],
                    },
                },
            }
        )

    patch: Dict[str, Any] = {
        "channels": {"feishu": feishu},
        "bindings": bindings,
    }

    agents_patch = build_agents_patch(data.get("agents"))
    if agents_patch:
        patch["agents"] = agents_patch

    tools_patch: Dict[str, Any] = {}
    if isinstance(data.get("agentToAgent"), dict) and data["agentToAgent"]:
        tools_patch["agentToAgent"] = data["agentToAgent"]
    if isinstance(data.get("tools"), dict):
        tools = data["tools"]
        if isinstance(tools.get("allow"), list) and tools["allow"]:
            tools_patch["allow"] = tools["allow"]
        if isinstance(tools.get("sessions"), dict) and tools["sessions"]:
            tools_patch["sessions"] = tools["sessions"]
    if tools_patch:
        patch["tools"] = tools_patch

    if isinstance(data.get("session"), dict) and data["session"]:
        patch["session"] = data["session"]

    messages_patch = build_messages_patch(data)
    if messages_patch:
        patch["messages"] = messages_patch

    return patch


def build_legacy_patch(data: Dict[str, Any]) -> Dict[str, Any]:
    accounts = validate_accounts(require(data, "accounts"))
    routes = validate_routes(require(data, "routes"))

    channel = {
        "kind": LEGACY_CHANNEL,
        "bindAddress": data.get("bindAddress", "0.0.0.0"),
        "port": data.get("port", 8090),
        "apiPath": data.get("apiPath", "/openapi/v2/interactives"),
        "chatAnywhere": data.get("chatAnywhere", True),
        "accounts": [
            {
                "accountId": a["accountId"],
                **build_account_cfg(a),
            }
            for a in accounts
        ],
    }

    bindings: List[Dict[str, Any]] = []
    for route in routes:
        bindings.append(
            {
                "agentId": route["agentId"],
                "match": {
                    "channel": route.get("channel") or LEGACY_CHANNEL,
                    "accountId": route["accountId"],
                    "peer": {
                        "kind": route["peer"]["kind"],
                        "id": route["peer"]["id"],
                    },
                },
            }
        )

    patch = {
        "channels": [channel],
        "bindings": bindings,
    }

    tools_patch: Dict[str, Any] = {}
    if isinstance(data.get("agentToAgent"), dict) and data["agentToAgent"]:
        tools_patch["agentToAgent"] = data["agentToAgent"]
    if isinstance(data.get("tools"), dict):
        tools = data["tools"]
        if isinstance(tools.get("allow"), list) and tools["allow"]:
            tools_patch["allow"] = tools["allow"]
        if isinstance(tools.get("sessions"), dict) and tools["sessions"]:
            tools_patch["sessions"] = tools["sessions"]
    if tools_patch:
        patch["tools"] = tools_patch

    if isinstance(data.get("session"), dict) and data["session"]:
        patch["session"] = data["session"]

    messages_patch = build_messages_patch(data)
    if messages_patch:
        patch["messages"] = messages_patch

    return patch


def write_json(path: pathlib.Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_summary(
    path: pathlib.Path,
    mode: str,
    patch_file: pathlib.Path,
    patch: Dict[str, Any],
    data: Dict[str, Any],
    runtime_manifest_file: pathlib.Path | None = None,
    runtime_manifest: Dict[str, Any] | None = None,
) -> None:
    bindings = patch.get("bindings") if isinstance(patch, dict) else []
    binding_count = len(bindings) if isinstance(bindings, list) else 0
    lines = [
        "# 生成摘要",
        "",
        f"- 生成时间: {datetime.now().isoformat(timespec='seconds')}",
        f"- 模式: `{mode}`",
        f"- patch 文件: `{patch_file}`",
        f"- binding 条数: `{binding_count}`",
    ]
    if runtime_manifest_file is not None:
        lines.append(f"- runtime manifest: `{runtime_manifest_file}`")
    if runtime_manifest is not None:
        lines.append(f"- team 数量: `{runtime_manifest.get('teamCount', 0)}`")
    lines.extend(
        [
        "",
        "## 推荐验证命令",
        "",
        "```bash",
        "openclaw config validate",
        "openclaw gateway restart",
        "openclaw logs --follow",
        "openclaw agents list --bindings",
        "```",
        "",
        "## 检查点",
        "",
        "- 绑定顺序是否为精确规则在前、兜底在后",
        "- defaultAccount 是否存在且可用（插件模式）",
        "- requireMention=false 时是否已申请 im:message.group_msg",
        "- 若需主管跨会话派单：tools.allow 是否包含 group:sessions",
        "- 若需主管跨会话派单：tools.sessions.visibility / session.sendPolicy 是否放行",
        ]
    )
    if runtime_manifest is not None:
        lines.extend(
            [
                "- V5 team runtime manifest 是否与快照和 watchdog 命名一致",
                "- hidden main session key 是否按 team 隔离",
            ]
        )
    agents = data.get("agents")
    if isinstance(agents, list) and agents and all(isinstance(agent, str) for agent in agents):
        lines.extend(
            [
                "",
                "## 注意",
                "",
                "- 输入里的 `agents` 为字符串列表时，脚本不会输出 `agents.list`，以避免覆盖 brownfield 现网的详细 agent 配置。",
                "- 若需要脚本生成 `agents.list`，请改为传入完整 agent 对象数组（至少包含 `id`）。",
            ]
        )
    with path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build OpenClaw Feishu config snippets")
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--out", default="references/generated", help="Output directory")
    parser.add_argument("--mode", choices=["plugin", "core", "auto"], default="auto")
    args = parser.parse_args(argv)

    input_path = pathlib.Path(args.input).expanduser().resolve()
    out_dir = pathlib.Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    data = load_json(input_path)
    mode = args.mode
    if mode == "auto":
        mode = "core" if data.get("mode") == "core" else "plugin"

    if mode == "plugin":
        patch = build_plugin_patch(data)
    else:
        patch = build_legacy_patch(data)
    runtime_manifest = build_v5_runtime_manifest(data) if mode == "plugin" and data.get("teams") is not None else None

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    patch_file = out_dir / f"openclaw-feishu-{mode}-patch-{timestamp}.json"
    summary_file = out_dir / f"openclaw-feishu-{mode}-summary-{timestamp}.md"
    runtime_manifest_file = (
        out_dir / f"openclaw-feishu-{mode}-v5-runtime-{timestamp}.json" if runtime_manifest is not None else None
    )

    write_json(patch_file, patch)
    if runtime_manifest_file is not None:
        write_json(runtime_manifest_file, runtime_manifest)
    write_summary(summary_file, mode, patch_file, patch, data, runtime_manifest_file, runtime_manifest)

    print(str(patch_file))
    print(str(summary_file))
    if runtime_manifest_file is not None:
        print(str(runtime_manifest_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
