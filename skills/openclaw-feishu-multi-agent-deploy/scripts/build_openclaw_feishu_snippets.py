#!/usr/bin/env python3
"""Build OpenClaw Feishu config snippets from deployment input JSON.

Usage:
  python3 scripts/build_openclaw_feishu_snippets.py \
    --input references/input-template.json \
    --out references/generated
"""

from __future__ import annotations

import argparse
import json
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Tuple


PLUGIN_CHANNEL = "feishu"
LEGACY_CHANNEL = "chat-feishu"


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
    if not isinstance(agents, list) or not agents:
        return None
    if all(isinstance(agent, dict) and agent.get("id") for agent in agents):
        return {"list": agents}
    if all(isinstance(agent, str) and agent for agent in agents):
        return None
    raise ValueError("agents must be either a list of agent ids or a list of agent objects with id")


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

    return patch


def write_json(path: pathlib.Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_summary(path: pathlib.Path, mode: str, patch_file: pathlib.Path, data: Dict[str, Any]) -> None:
    routes = data.get("routes", [])
    lines = [
        "# 生成摘要",
        "",
        f"- 生成时间: {datetime.now().isoformat(timespec='seconds')}",
        f"- 模式: `{mode}`",
        f"- patch 文件: `{patch_file}`",
        f"- 路由条数: `{len(routes)}`",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Build OpenClaw Feishu config snippets")
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--out", default="references/generated", help="Output directory")
    parser.add_argument("--mode", choices=["plugin", "core", "auto"], default="auto")
    args = parser.parse_args()

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

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    patch_file = out_dir / f"openclaw-feishu-{mode}-patch-{timestamp}.json"
    summary_file = out_dir / f"openclaw-feishu-{mode}-summary-{timestamp}.md"

    write_json(patch_file, patch)
    write_summary(summary_file, mode, patch_file, data)

    print(str(patch_file))
    print(str(summary_file))


if __name__ == "__main__":
    main()
