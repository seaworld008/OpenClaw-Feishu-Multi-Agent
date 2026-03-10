#!/usr/bin/env python3
"""Generate V5.1 deployment artifacts and materialize deploy-ready runtime files."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SKILL_ROOT.parent.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from core_feishu_config_builder import (  # noqa: E402
    build_plugin_patch,
    build_v51_runtime_manifest,
    load_json,
    write_json,
    write_summary,
)


OPENCLAW_HOME_TOKEN = "~/.openclaw"
SCRIPT_PATH_PREFIX = "skills/openclaw-feishu-multi-agent-deploy/scripts/"
WORKSPACE_BOOTSTRAP_FILE = "BOOTSTRAP.md"
RUNTIME_SCRIPT_BASENAMES = (
    "v51_team_orchestrator_runtime.py",
    "v51_team_orchestrator_reconcile.py",
    "v51_team_orchestrator_hygiene.py",
    "v51_team_orchestrator_canary.py",
    "core_job_registry.py",
    "core_worker_callback_sink.py",
    "core_runtime_store.py",
    "core_ingress_adapter.py",
    "core_team_controller.py",
    "core_outbox_sender.py",
    "core_openclaw_adapter.py",
    "core_session_hygiene.py",
    "core_canary_engine.py",
)


def rewrite_runtime_value(value: Any, openclaw_home: Path) -> Any:
    if isinstance(value, dict):
        return {key: rewrite_runtime_value(item, openclaw_home) for key, item in value.items()}
    if isinstance(value, list):
        return [rewrite_runtime_value(item, openclaw_home) for item in value]
    if isinstance(value, str):
        if value.startswith(OPENCLAW_HOME_TOKEN):
            suffix = value[len(OPENCLAW_HOME_TOKEN) :].lstrip("/")
            return str(openclaw_home / suffix) if suffix else str(openclaw_home)
        if value.startswith(SCRIPT_PATH_PREFIX):
            return str(openclaw_home / "tools" / "v5" / Path(value).name)
    return value


def materialize_runtime_manifest(runtime_manifest: Dict[str, Any], openclaw_home: Path | str) -> Dict[str, Any]:
    home = Path(openclaw_home).expanduser().resolve()
    return rewrite_runtime_value(copy.deepcopy(runtime_manifest), home)


def resolve_repo_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def render_template(template_path: Path, replacements: Dict[str, str]) -> str:
    content = template_path.read_text(encoding="utf-8")
    for token, value in replacements.items():
        content = content.replace(token, value)
    return content


def write_latest_alias(latest_path: Path, source_path: Path) -> None:
    latest_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")


def supervisor_workspace_files(team: Dict[str, Any]) -> Dict[str, str]:
    supervisor = team["supervisor"]
    team_key = str(team["teamKey"])
    agent_id = str(supervisor["agentId"])
    account_id = str(supervisor["accountId"])
    visible_label = str(supervisor["visibleLabel"])
    role = str(supervisor["role"])
    hidden_main = str(supervisor["hiddenMainSessionKey"])
    allowed_workers = ", ".join(str(item) for item in supervisor.get("allowedWorkerAgentIds", []))

    agents = f"""# AGENTS.md

这是 {team_key} 的 {visible_label} workspace，已经完成 V5.1 Hardening 预置，不允许再跑 bootstrap。

## 角色

- agentId: `{agent_id}`
- accountId: `{account_id}`
- role: `{role}`
- hidden main: `{hidden_main}`
- allowed workers: `{allowed_workers}`

## 工作规则

1. 群会话是 `ingress-only`：真实用户在群里 @ 你后，首轮 assistant 响应必须直接输出 `NO_REPLY`，不得向群发送任何可见文本。
2. 建单、接单、派单、最终统一收口都只能由 `controller -> outbox -> sender` 执行；群会话不得直接运行 `start-job-with-workflow`、`build-visible-ack`、`build-dispatch-payload`、`build-rollup-visible-message`、`record-visible-message`。
3. hidden main 是纯 mailbox，不是评审会。收到遗留 `COMPLETE_PACKET`、明文 callback、`Agent-to-agent announce step.` 或其他 inter-session 消息时，不做业务点评，不追加要求，不复写方案，也不把它们当正式 callback。
4. hidden main / announce 回合只允许输出 `NO_REPLY` 或 `ANNOUNCE_SKIP`。
5. 禁止 `sessions_spawn`、禁止让群可见 supervisor 会话自行派生 subagent、禁止在群里自由发送 `JOB-*`、`TG-*` 接单、接单点评或其他未走控制面的文案。
6. 不要读取或生成 bootstrap 式内容，不要在 hidden main 里扮演真实用户，不要把 worker callback 当成新的业务对话。
"""

    soul = f"""# SOUL.md

你是 {team_key} 的 {role}（{visible_label}），但你的群会话只是 ingress-only 哨兵，不再直接充当控制面执行者。

- 你的职责是保持群会话静默，把真实用户消息留给 controller claim。
- 你的 hidden main 是协议邮箱，不是对 worker 进行点评的聊天窗口。
- 当 worker 回调到 `{hidden_main}` 时，你只消费协议，不提供业务反馈。
- 不要在群里直接发送 `【{visible_label}已接单｜...】` 或 `【{visible_label}最终统一收口｜...】`；这些可见消息只能由 outbox sender 发出。
- 任意 inter-session callback / announce 若不需要可见动作，直接 `NO_REPLY` 或 `ANNOUNCE_SKIP`。
"""

    user = f"""# USER.md

这是系统内置控制面 workspace，不是通用对话空间。

- teamKey: `{team_key}`
- agentId: `{agent_id}`
- accountId: `{account_id}`
- 群会话模式：`ingress-only`
- 群里可见动作由 controller/outbox 统一发送
"""

    identity = f"""# IDENTITY.md

- agentId: `{agent_id}`
- teamKey: `{team_key}`
- role: `{role}`
- visibleLabel: `{visible_label}`
- accountId: `{account_id}`
"""

    tools = """# TOOLS.md

优先使用控制面命令和显式协议字段，不要把 hidden main 当作业务协作聊天窗口。
"""

    heartbeat = """Read the current control-plane state only. If there is no explicit workflow action to execute, reply HEARTBEAT_OK."""

    return {
        "AGENTS.md": agents,
        "SOUL.md": soul,
        "USER.md": user,
        "IDENTITY.md": identity,
        "TOOLS.md": tools,
        "HEARTBEAT.md": heartbeat,
    }


def ingress_workspace_files(team: Dict[str, Any]) -> Dict[str, str]:
    ingress = team["ingress"]
    team_key = str(team["teamKey"])
    peer_id = str(team["group"]["peerId"])
    entry_account_id = str(team["group"]["entryAccountId"])
    agent_id = str(ingress["agentId"])

    agents = f"""# AGENTS.md

这是 {team_key} 的 ingress sentinel workspace。

## 角色

- agentId: `{agent_id}`
- teamKey: `{team_key}`
- entryAccountId: `{entry_account_id}`
- peerId: `{peer_id}`

## 工作规则

1. 这个 agent 只作为 Feishu broadcast 路由占位，不承担任何可见回复责任。
2. 如果它被意外直接 dispatch，唯一正确输出是 `NO_REPLY`。
3. 禁止调用任何控制面命令，禁止 `sessions_spawn`，禁止发送群消息，禁止生成 `JOB-*` / `TG-*` 文案。
4. 真正需要保留的入站消息会由 observer/no-op dispatcher 写入 supervisor group session，再由 controller claim。
"""

    soul = f"""# SOUL.md

你是 {team_key} 的 ingress sentinel。

- 你不是主管，不负责接单、派单、收口。
- 你不向用户可见回复。
- 任意输入都直接 `NO_REPLY`。
"""

    user = f"""# USER.md

- teamKey: `{team_key}`
- agentId: `{agent_id}`
- mode: `ingress-sentinel`
"""

    identity = f"""# IDENTITY.md

- agentId: `{agent_id}`
- teamKey: `{team_key}`
- role: `ingress sentinel`
"""

    tools = """# TOOLS.md

不要使用工具。不要生成任何可见输出。只允许 `NO_REPLY`。
"""

    heartbeat = """Always reply HEARTBEAT_OK. For inbound user content, reply NO_REPLY."""

    return {
        "AGENTS.md": agents,
        "SOUL.md": soul,
        "USER.md": user,
        "IDENTITY.md": identity,
        "TOOLS.md": tools,
        "HEARTBEAT.md": heartbeat,
    }


def worker_workspace_files(team: Dict[str, Any], worker: Dict[str, Any]) -> Dict[str, str]:
    team_key = str(team["teamKey"])
    agent_id = str(worker["agentId"])
    account_id = str(worker["accountId"])
    visible_label = str(worker["visibleLabel"])
    role = str(worker["role"])
    supervisor_label = str(team["supervisor"]["visibleLabel"])
    sibling_labels = [
        str(item.get("visibleLabel") or "").strip()
        for item in team.get("workers", [])
        if str(item.get("agentId") or "") != agent_id and str(item.get("visibleLabel") or "").strip()
    ]
    forbidden_labels = [supervisor_label, *sibling_labels]
    forbidden_labels = [item for index, item in enumerate(forbidden_labels) if item and item not in forbidden_labels[:index]]
    forbidden_labels_text = "、".join(forbidden_labels) if forbidden_labels else "主管"

    agents = f"""# AGENTS.md

这是 {team_key} 的 {visible_label} worker workspace，已经完成 V5.1 Hardening 预置，不允许再跑 bootstrap。

## 角色

- agentId: `{agent_id}`
- accountId: `{account_id}`
- role: `{role}`

## 固定协议

1. `TASK_DISPATCH` 是最高优先级输入。
2. 你不再直接使用 `message` 工具向群发送 `progress/final`。worker 的职责是先完成分析，再一次性调用 `callbackCommand '<JSON payload>'` 提交 `progressDraft / finalDraft / summary / details / risks / actionItems`。
3. `progressDraft` / `finalDraft` 必须原样以 `progressTitle` / `finalTitle` 开头，例如 `【{visible_label}进度｜TG-xxxx】` 与 `【{visible_label}结论｜TG-xxxx】`。
4. 你的 `finalVisibleText` 只允许覆盖 `{visible_label}` 视角。禁止产出 `{forbidden_labels_text}` 标题、章节、预算结论、统一收口或整版总方案。
5. 只允许调用控制面提供的结构化 callback sink，使用单个 `--payload` JSON 提交 `progressDraft / finalDraft / summary / details / risks / actionItems`；如果你已经拿到了真实 `progressMessageId / finalMessageId`，也只能作为附加字段回传给控制面，绝不能再自行决定是否发群。
6. 禁止直接调用 `message` 发送群内可见正文；可见消息只能由 controller -> outbox -> sender 发出。若你直接 message，会造成重复发送，属于协议违规。
7. 如果 callback sink 返回错误，优先修正本次回调 payload，不要退回旧文本协议。
8. 不要读取 bootstrap / memory / USER 背景来决定流程；流程只由 `TASK_DISPATCH`、显式字段和系统提示约束。
9. 禁止使用 `pending`、`sent`、`<pending...>`、`*_placeholder` 这类占位 messageId。
10. 禁止使用 `sessions_spawn`；不要把当前 worker 再拆成子代理树，必须在当前 session 内完成协议闭环。
"""

    soul = f"""# SOUL.md

你是 {team_key} 的 {role}（{visible_label}）。

- 你的任务不是闲聊，而是执行 `TASK_DISPATCH`。
- 你必须产出两段草稿：`progressDraft`、`finalDraft`，再交给控制面顺序发布。
- 你的结论只能停留在 `{visible_label}` 角色边界内，不能提前替 `{forbidden_labels_text}` 写结论或统一收口。
- 你必须调用控制面提供的结构化 callback sink，不再回 hidden main 文本。
- 完成完整 callback 后只输出 `CALLBACK_OK`，不要再继续对话。
"""

    user = f"""# USER.md

这是系统内置 worker workspace，不是通用助手对话空间。

- teamKey: `{team_key}`
- agentId: `{agent_id}`
- accountId: `{account_id}`
- visibleLabel: `{visible_label}`
- callback mode: `structured callback sink only`
"""

    identity = f"""# IDENTITY.md

- agentId: `{agent_id}`
- teamKey: `{team_key}`
- role: `{role}`
- visibleLabel: `{visible_label}`
- accountId: `{account_id}`
"""

    tools = """# TOOLS.md

只把工具用于两类动作：执行结构化 callback sink、读取本地任务上下文。不要直接发送群消息，不要派生新的子代理或额外会话。
"""

    heartbeat = """If there is no fresh TASK_DISPATCH, reply HEARTBEAT_OK. Never invent work from old chats."""

    return {
        "AGENTS.md": agents,
        "SOUL.md": soul,
        "USER.md": user,
        "IDENTITY.md": identity,
        "TOOLS.md": tools,
        "HEARTBEAT.md": heartbeat,
    }


def write_workspace_files(workspace: Path, files: Dict[str, str]) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    bootstrap_path = workspace / WORKSPACE_BOOTSTRAP_FILE
    if bootstrap_path.exists():
        bootstrap_path.unlink()
    for name, content in files.items():
        (workspace / name).write_text(content.strip() + "\n", encoding="utf-8")


def materialize_workspace_contracts(runtime_manifest: Dict[str, Any]) -> None:
    for team in runtime_manifest.get("teams", []):
        ingress_workspace = Path(str(team["ingress"]["workspace"])).expanduser().resolve()
        write_workspace_files(ingress_workspace, ingress_workspace_files(team))
        supervisor_workspace = Path(str(team["supervisor"]["workspace"])).expanduser().resolve()
        write_workspace_files(supervisor_workspace, supervisor_workspace_files(team))
        for worker in team.get("workers", []):
            worker_workspace = Path(str(worker["workspace"])).expanduser().resolve()
            write_workspace_files(worker_workspace, worker_workspace_files(team, worker))


def materialize_runtime_scripts(openclaw_home: Path) -> None:
    tools_dir = openclaw_home / "tools" / "v5"
    tools_dir.mkdir(parents=True, exist_ok=True)
    for basename in RUNTIME_SCRIPT_BASENAMES:
        source = SCRIPT_DIR / basename
        if not source.exists():
            raise FileNotFoundError(f"missing runtime script: {source}")
        shutil.copy2(source, tools_dir / basename)


def clean_invalid_delivery_queue(openclaw_home: Path, *, valid_account_ids: set[str]) -> list[str]:
    queue_dir = openclaw_home / "delivery-queue"
    if not queue_dir.exists():
        return []
    removed: list[str] = []
    for path in sorted(queue_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            path.unlink(missing_ok=True)
            removed.append(path.name)
            continue
        account_id = str(payload.get("accountId") or "").strip()
        target = str(payload.get("target") or "").strip()
        message = str(payload.get("message") or "").strip()
        if not account_id or not target or not message or account_id not in valid_account_ids:
            path.unlink(missing_ok=True)
            removed.append(path.name)
    return removed


def render_systemd_units(
    runtime_manifest: Dict[str, Any],
    *,
    manifest_path: Path,
    openclaw_home: Path,
    systemd_user_dir: Path,
    stale_seconds: int,
) -> None:
    systemd_user_dir.mkdir(parents=True, exist_ok=True)
    for team in runtime_manifest.get("teams", []):
        runtime = team["runtime"]
        watchdog = runtime["watchdog"]
        replacements = {
            "__TEAM_KEY__": str(team["teamKey"]),
            "__RECONCILE_SCRIPT__": str(runtime["controlPlane"]["reconcileScript"]),
            "__MANIFEST_PATH__": str(manifest_path),
            "__OPENCLAW_HOME__": str(openclaw_home),
            "__STALE_SECONDS__": str(stale_seconds),
            "__TEAM_WORKDIR__": str(team["supervisor"]["workspace"]),
            "__SUPERVISOR_AGENT_ID__": str(team["supervisor"]["agentId"]),
        }
        service_path = systemd_user_dir / str(watchdog["systemdServiceName"])
        timer_path = systemd_user_dir / str(watchdog["systemdTimerName"])
        service_path.write_text(
            render_template(resolve_repo_path(watchdog["systemdServiceTemplate"]), replacements),
            encoding="utf-8",
        )
        timer_path.write_text(
            render_template(resolve_repo_path(watchdog["systemdTimerTemplate"]), replacements),
            encoding="utf-8",
        )


def render_launchd_units(
    runtime_manifest: Dict[str, Any],
    *,
    manifest_path: Path,
    openclaw_home: Path,
    launchd_dir: Path,
    stale_seconds: int,
) -> None:
    launchd_dir.mkdir(parents=True, exist_ok=True)
    log_dir = openclaw_home / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    for team in runtime_manifest.get("teams", []):
        runtime = team["runtime"]
        watchdog = runtime["watchdog"]
        replacements = {
            "__TEAM_KEY__": str(team["teamKey"]),
            "__RECONCILE_SCRIPT__": str(runtime["controlPlane"]["reconcileScript"]),
            "__MANIFEST_PATH__": str(manifest_path),
            "__OPENCLAW_HOME__": str(openclaw_home),
            "__STALE_SECONDS__": str(stale_seconds),
            "__TEAM_WORKDIR__": str(team["supervisor"]["workspace"]),
            "__LOG_DIR__": str(log_dir),
        }
        plist_path = launchd_dir / f"{watchdog['launchdLabel']}.plist"
        plist_path.write_text(
            render_template(resolve_repo_path(watchdog["launchdTemplate"]), replacements),
            encoding="utf-8",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build V5.1 deployment artifacts and optionally materialize deploy-ready runtime files"
    )
    parser.add_argument("--input", required=True, help="Unified-entry JSON file")
    parser.add_argument("--out", default="references/generated", help="Artifact output directory")
    parser.add_argument("--mode", choices=["plugin", "auto"], default="plugin")
    parser.add_argument(
        "--openclaw-home",
        help="When provided, write the materialized active runtime manifest to <home>/v51-runtime-manifest.json",
    )
    parser.add_argument(
        "--systemd-user-dir",
        help="Optional target directory for rendered v51-team-*.service/.timer files",
    )
    parser.add_argument(
        "--launchd-dir",
        help="Optional target directory for rendered launchd plist files",
    )
    parser.add_argument("--stale-seconds", type=int, default=180, help="Watchdog stale threshold")
    args = parser.parse_args(argv)

    if (args.systemd_user_dir or args.launchd_dir) and not args.openclaw_home:
        raise SystemExit("--systemd-user-dir/--launchd-dir require --openclaw-home")

    input_path = Path(args.input).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    mode = args.mode
    if mode == "auto":
        mode = "plugin"

    data = load_json(input_path)
    patch = build_plugin_patch(data)
    runtime_manifest = build_v51_runtime_manifest(data)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    patch_file = out_dir / f"openclaw-feishu-{mode}-patch-{timestamp}.json"
    summary_file = out_dir / f"openclaw-feishu-{mode}-summary-{timestamp}.md"
    runtime_manifest_file = out_dir / f"openclaw-feishu-{mode}-v51-runtime-{timestamp}.json"

    write_json(patch_file, patch)
    write_json(runtime_manifest_file, runtime_manifest)
    write_summary(summary_file, mode, patch_file, patch, data, runtime_manifest_file, runtime_manifest)

    latest_patch_file = out_dir / f"openclaw-feishu-{mode}-patch-latest.json"
    latest_summary_file = out_dir / f"openclaw-feishu-{mode}-summary-latest.md"
    latest_runtime_file = out_dir / f"openclaw-feishu-{mode}-v51-runtime-latest.json"
    write_latest_alias(latest_patch_file, patch_file)
    write_latest_alias(latest_summary_file, summary_file)
    write_latest_alias(latest_runtime_file, runtime_manifest_file)

    print(str(patch_file))
    print(str(summary_file))
    print(str(runtime_manifest_file))
    print(str(latest_patch_file))
    print(str(latest_summary_file))
    print(str(latest_runtime_file))

    if args.openclaw_home:
        openclaw_home = Path(args.openclaw_home).expanduser().resolve()
        openclaw_home.mkdir(parents=True, exist_ok=True)
        materialize_runtime_scripts(openclaw_home)
        active_manifest = materialize_runtime_manifest(runtime_manifest, openclaw_home)
        active_manifest_path = openclaw_home / "v51-runtime-manifest.json"
        write_json(active_manifest_path, active_manifest)
        materialize_workspace_contracts(active_manifest)
        removed_queue_entries = clean_invalid_delivery_queue(
            openclaw_home,
            valid_account_ids={str(item["accountId"]) for item in data.get("accounts", []) if str(item.get("accountId") or "").strip()},
        )
        print(str(active_manifest_path))
        if removed_queue_entries:
            print(json.dumps({"removedDeliveryQueueEntries": removed_queue_entries}, ensure_ascii=False))

        if args.systemd_user_dir:
            render_systemd_units(
                active_manifest,
                manifest_path=active_manifest_path,
                openclaw_home=openclaw_home,
                systemd_user_dir=Path(args.systemd_user_dir).expanduser().resolve(),
                stale_seconds=args.stale_seconds,
            )
        if args.launchd_dir:
            render_launchd_units(
                active_manifest,
                manifest_path=active_manifest_path,
                openclaw_home=openclaw_home,
                launchd_dir=Path(args.launchd_dir).expanduser().resolve(),
                stale_seconds=args.stale_seconds,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
