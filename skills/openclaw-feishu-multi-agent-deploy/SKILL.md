---
name: openclaw-feishu-multi-agent-deploy
description: Use when delivering production-ready OpenClaw Feishu multi-agent setups, including single-bot or multi-bot routing, brownfield incremental rollout, validation, and upgrade-safe configuration.
---

# Feishu OpenClaw Multi-Agent

## 目标
把 OpenClaw + 飞书多 Agent 配置从“能跑”提升到“可交付”：
- 可配置：单机器人/多机器人、多角色分工
- 可落地：前提条件清晰、一次配置可执行
- 可升级：兼容 OpenClaw 持续迭代，能做升级后回归
- 可回滚：所有生产改动都有备份和回滚路径

## 默认技术路线（2026-03 起）
- 默认使用官方插件：`@openclaw/feishu`
- 默认 `match.channel = "feishu"`
- `chat-feishu` 仅作为历史配置兼容路径

## 何时使用
- 客户要求在飞书里搭建多 Agent 团队（各司其职）
- 需要把不同群/私聊稳定路由到不同 Agent
- 需要在已上线环境做增量改造（Brownfield）
- 需要升级 OpenClaw/插件后做兼容修复

## 必读资源（按顺序）
1. `references/prerequisites-checklist.md`
2. `templates/deployment-inputs.example.yaml`
3. `references/openclaw-feishu-multi-agent-notes.md`
4. `references/source-cross-validation-2026-03-04.md`
5. `templates/brownfield-change-plan.example.md`

## 交付模式

### 1) 拓扑模式
- `single-bot`：一个飞书机器人，多群分流到多个 Agent
- `multi-bot`：多个飞书机器人（多 `accountId`）分流到多个 Agent

### 2) 变更模式
- `incremental`（默认推荐）：生产环境只打最小补丁
- `full_replace`：仅用于新部署或用户明确要求全量重构

### 3) 发布策略
- `canary_then_full`（默认推荐）
- `direct_full`（仅低风险场景）

## 执行流程（严格按顺序）
1. 前置校验
- 检查 OpenClaw 与插件版本
- 检查飞书权限与事件订阅
- 明确变更窗口和回滚责任人

2. 模式识别
- 如果现网已用 `channels.feishu.*`，保持插件模式
- 如果现网仍为 `chat-feishu`，先兼容输出，再计划迁移

3. 收集输入
- 使用 `templates/deployment-inputs.example.yaml`
- 确认 `agents`、`accounts`、`routes` 完整
- 群/私聊 ID（`peer.id`）必须真实可用

4. 生成配置
- 优先输出最小 patch（不要覆盖整份配置）
- 可用脚本：
```bash
python3 scripts/build_openclaw_feishu_snippets.py \
  --input references/input-template.json \
  --out references/generated
```
- 注意：输入里的 `agents` 若只是字符串列表，脚本不会生成 `agents.list`，以避免覆盖 brownfield 现网中的详细 agent 配置。

5. 绑定排序（关键）
- 先精确规则（`accountId + peer`）
- 再 `accountId` 级规则
- 最后渠道兜底规则（如 `accountId="*"`）
- 重启前必须做冲突检查：
  - 同一 `channel/accountId/peer.id` 不得映射多个 agent
  - bindings 里不得引用已删除 agent

6. 提及策略
- 默认 `requireMention=true`
- 仅在业务明确要求时启用免 @
- 免 @ 前必须确认 `im:message.group_msg` 已审批
- 多 Bot 群默认 `allowMentionlessInMultiBotGroup=false`

7. Brownfield 上线
- 先备份配置
- 执行 `openclaw config validate`
- 重启网关
- 先 canary 群验收，再全量放量

8. 回归与验收
- 使用 `templates/verification-checklist.md`
- 记录验证证据（命令输出、关键日志片段）
- 输出回滚命令
- 若启用了卡片交互，验证 `card.action.trigger` 事件链路
- V3 主管派单场景必须执行 `scripts/check_v3_dispatch_canary.sh`，未通过不得判定验收成功
- `check_v3_dispatch_canary.sh` 返回 `3` 表示证据不足，不能视为派单成功
- V4/V4.1 单群团队场景必须优先执行 worker warm-up，再跑 `scripts/check_v4_1_team_canary.sh`
- V4/V4.1 验收证据优先级：`~/.openclaw/agents/*/sessions/*.jsonl` 高于 gateway log

## 输出要求（给客户/交付文档）
必须包含：
- 最终 patch（只含本次改动）
- `to_add` / `to_update` / `to_keep_unchanged`
- 变更命令、验证命令、回滚命令
- 验收结果（通过/失败 + 证据）
- （可选）`tools.agentToAgent` 的启用范围与风险说明
- （V3 可选）`tools.allow`（是否包含 `group:sessions`）
- （V3 可选）`tools.sessions` 与 `session.sendPolicy` 的放行策略说明

## 关键约束
- 不得虚构 `agentId`、`accountId`、`peer.id`
- 不得直接覆盖与本次无关配置
- 不得省略备份步骤
- 不得把兜底规则放到精确规则前

## 常见问题快速处理
- 收不到消息：优先查事件订阅与权限
- 群里必须 @：查 `requireMention` 与 `im:message.group_msg`
- 路由串线：查 `bindings` 顺序和重叠规则
- 多账号出站错 bot：查 `defaultAccount` 与 `match.accountId`
- 升级后异常：跑 `openclaw config validate` + canary 回归
- 主管只“写派单文本”不真实派发：查 `tools.allow` 是否缺少 `group:sessions`
- 主管看不到目标群会话：查 `tools.sessions.visibility` 和目标群是否 warm-up 过
- 主管派发被策略拦截：查 `session.sendPolicy` 是否默认放行
- V4/V4.1 主管返回 `DISPATCH_INCOMPLETE` 但正文声称“已安排”：查 supervisor prompt 是否缺少状态机式硬门控
- V4/V4.1 新群首轮无 worker 会话：先对 worker 执行 warm-up，再复测
- V4/V4.1 返回 `tool_call_required`：说明 supervisor 本轮没有任何真实工具调用，先查 prompt 是否已更新并确认重启已生效

## 可直接复用的文件
- 模板：
  - `templates/deployment-inputs.example.yaml`
  - `templates/openclaw-single-bot-route.example.jsonc`
  - `templates/openclaw-multi-bot-route.example.jsonc`
  - `templates/brownfield-change-plan.example.md`
  - `templates/verification-checklist.md`
- 输入样板：
  - `references/input-template.json`
  - `references/input-template-plugin.json`
  - `references/input-template-legacy-chat-feishu.json`
- 运行手册：
  - `references/rollout-and-upgrade-playbook.md`
  - `references/codex-prompt-templates.md`
  - `references/codex-prompt-templates-v3.1.md`
  - `references/codex-prompt-templates-v3.md`
  - `references/codex-prompt-templates-v4-single-group-team.md`
  - `references/codex-prompt-templates-v4.1-single-group-team.md`
- 辅助脚本：
  - `scripts/check_v3_dispatch_canary.sh`
  - `scripts/check_v4_1_team_canary.sh`
