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

## 平台兼容策略
- `Linux`：正式推荐，默认按 `systemd --user` 交付
- `macOS`：正式推荐，默认按 `launchd / LaunchAgent` 交付
- `Windows + WSL2`：正式推荐，复用 Linux 运行模型
- `Windows 原生`：不作为默认生产路径；若客户坚持原生部署，必须单独记录偏差与未验证项

平台原则：
1. `V4.3.1` 的协议、SQLite、canary、WARMUP 不分平台分叉。
2. 平台差异只体现在 service manager、watchdog 模板和运维 SOP。
3. Windows 客户默认输出 `WSL2` 路线，不要把原生 Windows service 写成与 Linux 等价。

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
- 明确目标平台：`linux` / `macos` / `wsl2`；若是 Windows，默认先收敛为 `wsl2`
- 明确 service manager：`systemd --user` / `launchd` / `manual`

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
- V4/V4.2 单群最佳实践场景优先使用 `scripts/check_v4_2_team_canary.sh`
- 若交付要求“群里必须看见 worker 发言”，单群演示推荐使用 `V4.2.1`，并在 canary 中追加 `--require-visible-messages`
- 若交付目标是“真实长期上线且用户不手输 taskId”，单群生产推荐直接按 `V4.3.1` 设计：supervisor 自动生成 `jobRef`，并引入外部状态层、一次性初始化、watchdog 与 activeJob/queue 机制
- `V4.3.1` 验收优先使用 `scripts/check_v4_3_canary.py`
- V4/V4.1/V4.2 验收证据优先级：`~/.openclaw/agents/*/sessions/*.jsonl` 高于 gateway log

## 输出要求（给客户/交付文档）
必须包含：
- 最终 patch（只含本次改动）
- `to_add` / `to_update` / `to_keep_unchanged`
- 变更命令、验证命令、回滚命令
- 按平台分支的 service manager 命令（Linux/WSL2 用 `systemd --user`，macOS 用 `launchd`，Windows 默认给 `WSL2` 方案）
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
- V4/V4.1/V4.2 主管返回 `DISPATCH_INCOMPLETE` 但正文声称“已安排”：查 supervisor prompt 是否缺少状态机式硬门控
- V4/V4.1/V4.2 新群首轮无 worker 会话：先对 worker 执行 warm-up，再复测
- V4/V4.1/V4.2 返回 `tool_call_required`：说明 supervisor 本轮没有任何真实工具调用，先查 prompt 是否已更新并确认重启已生效
- V4/V4.1/V4.2 若日志出现 `thread=true` / `subagent_spawning hooks`：说明当前 Feishu 渠道不支持这条 `sessions_spawn` 自动补会话路径，应改为人工 warm-up
- V4/V4.1/V4.2 单群团队推荐采用 send-first probe：优先验证真实 `sessions_send`，不要只依赖 `sessions_list`
- V4.2 若出现 `SEND_PATH_AVAILABLE_BUT_LIST_MISS`：说明固定 sessionKey 的 send 路径已可用，但 `sessions_list` 不能再作为唯一存在性判断
- V4.2 若出现 `TIMEOUT_BUT_WORKER_DELIVERED`：说明 worker 已执行但 supervisor 仍以 timeout 未收口，应优先补 timeout 二次判定或 ACK 双阶段派单
- V4.2 若 ACK 成功但详细任务持续超时：优先改为 `ACK timeoutSeconds=15 + 详细任务 timeoutSeconds=0 + sessions_history 二次收口`
- V4.2 若出现 `TRIGGER_MISS_ON_MENTION_OR_FORMAT_WRAP`：说明被提及后仍没进入工具链，应优先同时补 `messages.groupChat.mentionPatterns`、`agents.list[].groupChat.mentionPatterns` 与 `PLAIN_TEXT` / 代码块包裹兼容
- V4.2 若配置已经升级但 supervisor 仍表现出旧行为：优先怀疑 stale group session。群级 system prompt 只在新 group session 第一轮生效，应先单独发送 `/reset`，或由运维清理该 group 的 supervisor session 映射并重启 gateway，再用新 `taskId` 复测
- V4.2 若 fresh session 已创建但 supervisor 仍持续 `tool_call_required/no_tool_call`：继续检查 `supervisor_agent` workspace 是否残留默认 `BOOTSTRAP.md` 与空白身份模板；生产单群团队 Agent 不应保留首次引导工作区残留
- V4.2 若 `sessions_send` 报 `No session found`：先查 sessionKey 是否写错。飞书群聊必须使用官方完整键 `agent:<agentId>:feishu:group:<peerId>`，不要使用 `feishu:chat:...` 或其他自造格式
- V4.2.1 若控制面已经跑通但群里看不到其他机器人发言：不要继续依赖隐式 announce。应在 worker 详细任务中显式调用 `message` 工具，用各自 `accountId` 往团队群发送短摘要，并在 worker session 中保留真实 `messageId`
- V4.2.1 若 worker 已生成摘要文本但 gateway 没有对应 `dispatch complete`：优先检查 `message` 工具的 `channel/account/target` 是否正确，尤其是 `target=chat:<peerId>`
- V4.3 若客户环境仍要求用户手工输入 `taskId`：优先判断这是不是把测试手段误当成产品方案；生产建议改为 supervisor 自动生成内部 `jobRef`
- V4.3 若单群连续收到多个独立任务：不要继续只靠 transcript 自然上下文；应引入外部状态层，显式维护 `active / queued / done / failed`
- V4.3 若用户补充说明被错误识别成新任务：先补“消息分类”规则，再补状态层，不要继续堆 prompt 文案
- V4.3.1 若 worker 频繁卡在旧行为：优先怀疑旧 team session 沿用了旧 prompt；应关闭当前 active job，清空三方 team session，并重新执行一次性 `WARMUP`
- V4.3.1 若任务长期卡住阻塞后续消息：不要要求用户重发或手工排障；优先执行 `watchdog-tick`，让 stale active job 自动失败并释放队列
- macOS 客户不要套用 `systemctl --user`；应使用 `launchctl bootstrap/print` 与 `templates/launchd/v4-3-watchdog.plist`
- Windows 客户不要默认承诺原生 service 版；应优先交付 `WSL2`，并引用 `references/windows-wsl2-deployment-notes.md`
- V4.3.1 若需要证明“真的稳定”，不要只看群聊观感；必须同时核对 SQLite `jobs/job_participants` 与 `check_v4_3_canary.py`
- V4.3.1 若群里仍泄漏 `ACK_READY / REPLY_SKIP / COMPLETE_PACKET`：优先检查 worker 的 callback 是否仍打到主管群会话；生产版必须统一回到 `agent:supervisor_agent:main`，内部协议最终只输出 `NO_REPLY`
- V4.3.1 若主管收不到最终完成包：优先检查 `mark-worker-complete` 是否仍强依赖 `--account-id/--role`；当前稳定版应允许这两个参数兜底，不应因字段漂移卡死
- V4.3.1 若演示效果不足：不要把 worker 结论压成一句话；群里的运营/财务结论允许多行完整输出，只对 `COMPLETE_PACKET` 做长度约束
- 公开群里的 `@其他机器人` 只能作为展示层，不应作为控制面正确性的唯一证据

## 可直接复用的文件
- 模板：
  - `templates/deployment-inputs.example.yaml`
  - `templates/openclaw-single-bot-route.example.jsonc`
  - `templates/openclaw-multi-bot-route.example.jsonc`
  - `templates/brownfield-change-plan.example.md`
  - `templates/verification-checklist.md`
  - `templates/systemd/v4-3-watchdog.service`
  - `templates/systemd/v4-3-watchdog.timer`
  - `templates/launchd/v4-3-watchdog.plist`
  - `templates/windows/wsl.conf.example`
  - `references/windows-wsl2-deployment-notes.md`
  - `references/source-cross-validation-2026-03-07-platforms.md`
- 输入样板：
  - `references/input-template.json`
  - `references/input-template-plugin.json`
  - `references/input-template-legacy-chat-feishu.json`
- 运行手册：
  - `references/rollout-and-upgrade-playbook.md`
  - `references/source-cross-validation-2026-03-06.md`
  - `references/codex-prompt-templates.md`
  - `references/codex-prompt-templates-v3.1.md`
  - `references/codex-prompt-templates-v3.md`
  - `references/codex-prompt-templates-v4-single-group-team.md`
  - `references/codex-prompt-templates-v4.1-single-group-team.md`
  - `references/codex-prompt-templates-v4.2-single-group-team.md`
  - `references/codex-prompt-templates-v4.2.1-single-group-team.md`
  - `references/codex-prompt-templates-v4.3-single-group-production.md`
  - `references/codex-prompt-templates-v4.3.1-single-group-production.md`
  - `references/source-cross-validation-2026-03-07.md`
- 辅助脚本：
  - `scripts/check_v3_dispatch_canary.sh`
  - `scripts/check_v4_1_team_canary.sh`
  - `scripts/check_v4_2_team_canary.sh`
  - `scripts/check_v4_3_canary.py`
