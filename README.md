# OpenClaw Feishu Multi-Agent Skill

一个面向交付的 Skill 仓库，用于在 **OpenClaw + 飞书** 场景中快速完成：

- 单机器人/多机器人多 Agent 路由配置
- 已部署环境（Brownfield）增量改造
- 调试、验收、回滚的标准化流程

目标是让你在客户环境里做到：**少改动、可回滚、可验证、可复用**。

## 适用场景

- 客户已经部署 OpenClaw，你需要新增飞书多 Agent 能力
- 你要把不同群路由到不同 Agent（writer/coder/cfo 等）
- 你希望降低 Token 消耗并减少上下文污染
- 你需要一套可复制的上线与验收 SOP

## 核心能力

- 支持两种部署模式：
  - `single-bot`：一个飞书机器人，多群路由不同 Agent
  - `multi-bot`：多个飞书机器人（多 accountId）路由不同 Agent
- 支持两类改造方式：
  - `incremental`：增量补丁（推荐，客户生产环境）
  - `full_replace`：全量替换（仅在明确需要时）
- 提供完整交付模板：
  - 部署输入清单
  - 单/多 Bot 配置样板
  - Brownfield 变更计划
  - 验收检查清单

## 仓库结构

```text
skills/
  openclaw-feishu-multi-agent-deploy/
    SKILL.md
    templates/
      deployment-inputs.example.yaml
      openclaw-single-bot-route.example.jsonc
      openclaw-multi-bot-route.example.jsonc
      brownfield-change-plan.example.md
      verification-checklist.md
```

## 快速开始

1. 填写部署输入模板  
编辑 `skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml`

2. 明确改造模式  
客户已上线环境建议：
- `existing_deployment: true`
- `change_mode: "incremental"`
- `rollout_strategy: "canary_then_full"`

3. 用 Codex 执行  
将下列指令直接发给 Codex（可按你环境改写）：

```text
请使用 openclaw-feishu-multi-agent-deploy skill，
读取 deployment-inputs.example.yaml 的真实值，
按 brownfield 增量模式修改现有 openclaw.json：
先备份、生成 to_add/to_update/to_keep_unchanged 变更计划、
只 patch channels.feishu + bindings + agentToAgent、
先 canary 群验证通过后再全量，并输出回滚命令和验收报告。
```

## 飞书权限建议（按模式申请）

基线权限（始终需要）：
- `im:message:send_as_bot`
- `im:message.p2p_msg:readonly`

群聊触发策略：
- `requireMention: true`：`im:message.group_at_msg:readonly`
- `requireMention: false`：`im:message.group_msg` 或 `im:message.group_msg:readonly`（租户命名可能不同）

事件订阅：
- `im.message.receive_v1`（必需）
- `card.action.trigger`（仅卡片回调场景）

## Brownfield（已部署环境）原则

- 先备份再改，不直接覆盖整份配置
- 仅修改必要路径（`channels.feishu` / `bindings` / `tools.agentToAgent`）
- 不删除不在本次范围内的既有配置
- 先灰度群验证，再全量切换
- 保留可一键执行的回滚命令

## 交付产物说明

- `SKILL.md`  
主流程与最佳实践（模式选择、配置、排障、验证）

- `deployment-inputs.example.yaml`  
部署前信息采集模板（密钥、群ID、账号、Agent 路由）

- `openclaw-single-bot-route.example.jsonc`  
单机器人多 Agent 路由样板

- `openclaw-multi-bot-route.example.jsonc`  
多机器人多 Agent 路由样板（含 `accountId`）

- `brownfield-change-plan.example.md`  
已部署环境改造计划模板（to_add / to_update / to_keep_unchanged）

- `verification-checklist.md`  
上线前后的验收清单

## 最佳实践来源（交叉验证）

- OpenClaw 官方文档（multi-agent / feishu channel / configuration）
- 飞书开放平台官方 API 与 scope 元数据
- `clawdbot-feishu` 官方 README 与多账号 PR

> 说明：不同版本文档对个别字段（如 `peer.kind`）可能存在差异，落地时请以你当前 OpenClaw 版本 schema 为准。

## 适合谁

- AI 解决方案交付团队
- 企业自动化顾问
- 需要快速上线多 Agent 飞书协作体系的个人/小团队
