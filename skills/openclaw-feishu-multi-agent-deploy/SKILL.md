---
name: openclaw-feishu-multi-agent-deploy
description: Use when delivering production-ready OpenClaw Feishu multi-agent setups, including single-bot or multi-bot routing, brownfield incremental rollout, validation, and upgrade-safe configuration.
---

# Feishu OpenClaw Multi-Agent

## 目标
把 OpenClaw + 飞书多 Agent 配置从“能跑”提升到“可交付”：
- 可配置：单机器人/多机器人、多角色分工
- 可模板化：每个群可定义 `teams`，按 `1` 个 supervisor + `N` 个 worker 自动展开
- 可落地：前提条件清晰、一次配置可执行
- 可升级：兼容 OpenClaw 持续迭代，能做升级后回归
- 可回滚：所有生产改动都有备份和回滚路径

## 默认技术路线（2026-03 起）
- 默认使用官方插件：`@openclaw/feishu`
- 默认 `match.channel = "feishu"`

## 平台兼容策略
- `Linux`：正式推荐，默认按 `systemd --user` 交付
- `macOS`：正式推荐，默认按 `launchd / LaunchAgent` 交付
- `Windows + WSL2`：正式推荐，复用 Linux 运行模型
- `Windows 原生`：不作为默认生产路径；若客户坚持原生部署，必须单独记录偏差与未验证项

平台原则：
1. 平台差异只体现在 service manager、watchdog 模板和运维 SOP。
2. Windows 客户默认输出 `WSL2` 路线，不要把原生 Windows service 写成与 Linux 等价。
3. `V5.1 Hardening` 的 `SQLite + hidden main session + runtime manifest` 运行模型在 Linux / macOS / WSL2 上保持一致。

## 何时使用
- 客户要求在飞书里搭建多 Agent 团队（各司其职）
- 需要把不同群/私聊稳定路由到不同 Agent
- 需要把多个群模板化扩展成独立 team units，而不是共享一套全局 agent
- 需要在已上线环境做增量改造（Brownfield）
- 需要升级 OpenClaw/插件后做兼容修复

## V5.1 Hardening 默认约束

- 一句话原则：每个群固定 1 个 supervisor，外加 N 个 worker
- 当前生产推荐：`V5.1 Hardening`
- 每个群都是一个独立 team unit
- 每个群固定 `1` 个 supervisor
- 每个群可配置 `N` 个 worker
- `roleCatalog` 是 `V5.1` 主线推荐的角色定义入口，统一维护 `name / role / visibleLabel / description / responsibility / identity / mentionPatterns / systemPrompt`
- `teams[].supervisor` 与 `teams[].workers[]` 推荐写成 `profileId + agentId + override`；旧 inline 配置继续兼容，但不再作为主线规范
- `visibleLabel` 是运行时标题与可见消息的单一显示来源；建单后会固化为快照，避免 runtime 再靠 `role` 猜“主管/运营/财务”
- 当前生产推荐标准：`bot 复用，role 固定`
- 同一个 bot 可以跨很多群复用，但它在所有群里都保持同一个角色
- 每个群的角色组合可以不同，只需要在该 `team` 下启用需要的 `workers`
- `teams` 是 `V5.1` 的推荐输入模型
- `workflow.stages` 必须覆盖当前 team 的全部 worker 且不可重复；主管只能在全部 worker 完成后收口
- 每个 agent 都允许独立定制 `name / description / identity / role / responsibility / systemPrompt`
- 不再推荐多个群共享同一套全局 `supervisor_agent / ops_agent / finance_agent`
- `V5.1` 重点是模板化复制 team，而不是做任意 mesh 式 agent 工作流引擎
- `V5.1 Hardening` 固定采用 `Deterministic Orchestrator`
- 一句话原则：`LLM 负责内容，代码负责流程`
- 主管控制面必须优先使用：
  - `start-job-with-workflow`
  - `build-visible-ack`
  - `get-next-action`
  - `build-dispatch-payload`
  - `build-rollup-context`
  - `build-rollup-visible-message`
  - `record-visible-message`
  - `ready-to-rollup`
- watchdog/reconcile 控制面固定脚本：
  - `v51_team_orchestrator_reconcile.py`
  - `resume-job`
  - `reconcile-dispatch`
  - `reconcile-rollup`
- 若 `V5.1 Hardening` 还依赖 `WARMUP` 才能稳定跑主流程，视为部署未完成，而不是正常要求

`V5.1` runtime 命名约定：
- hidden main：`agent:<supervisorAgentId>:main`
- SQLite：`~/.openclaw/teams/<teamKey>/state/team_jobs.db`
- systemd：`v51-team-<teamKey>.service` / `v51-team-<teamKey>.timer`
- launchd：`bot.molt.v51-team-<teamKey>`

当前正式双群基线：
- 内部团队群：`oc_f785e73d3c00954d4ccd5d49b63ef919`
- 外部团队群：`oc_7121d87961740dbd72bd8e50e48ba5e3`
- 当前正式 team units：`internal_main` / `external_main`
- 三个正式机器人：`aoteman` / `xiaolongxia` / `yiran_yibao`
- 当前 hidden main：
  - `agent:supervisor_internal_main:main`
  - `agent:supervisor_external_main:main`

`V5.1` 交付时默认要同时产出：
- OpenClaw patch
- summary
- `v51 runtime manifest`
- `v51 runtime manifest` 中必须写明 `V5.1 Hardening` 控制面命令

Codex 交付入口：
- `references/codex-prompt-templates-v51-team-orchestrator.md`
- `references/input-template-v51-fixed-role-multi-group.json`
- 这份文档必须保留当前 2 个正式群、3 个正式机器人、长版 systemPrompt 和可直接复制的 Codex 指令，不要退化成抽象骨架

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
- 如果现网仍有旧字段结构，先转成 `channels.feishu.*` 再继续交付

3. 收集输入
- 使用 `templates/deployment-inputs.example.yaml`
- 确认 `agents`、`accounts`、`routes` 完整
- 若交付目标是 `V5.1 Hardening`，优先改用 `teams` 模型：每个群定义 `supervisor`、`workers`、`workflow`
- 群/私聊 ID（`peer.id`）必须真实可用

4. 生成配置
- 优先输出最小 patch（不要覆盖整份配置）
- 可用脚本：
```bash
python3 scripts/core_feishu_config_builder.py \
  --input references/input-template-v51-fixed-role-multi-group.json \
  --out references/generated
```
- 当前最新稳定主线 `V5.1 Hardening` 默认使用 `references/input-template-v51-fixed-role-multi-group.json`
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
- 若是 `V5.1 Hardening` 且发生协议字段改动（`roleCatalog / teams / workflow.stages / systemPrompt / COMPLETE_PACKET / hidden main`），先执行：
```bash
python3 scripts/v51_team_orchestrator_hygiene.py \
  --home ~/.openclaw \
  --group-peer-id <teamGroupPeerId> \
  --include-workers \
  --delete-transcripts
```
- 先 canary 群验收，再全量放量

8. 回归与验收
- 使用 `templates/verification-checklist.md`
- 记录验证证据（命令输出、关键日志片段）
- 输出回滚命令
- 若启用了卡片交互，验证 `card.action.trigger` 事件链路
- `V5.1` 验收证据优先级：`~/.openclaw/agents/*/sessions/*.jsonl` 高于 gateway log

## 输出要求（给客户/交付文档）
必须包含：
- 最终 patch（只含本次改动）
- `to_add` / `to_update` / `to_keep_unchanged`
- 变更命令、验证命令、回滚命令
- 按平台分支的 service manager 命令（Linux/WSL2 用 `systemd --user`，macOS 用 `launchd`，Windows 默认给 `WSL2` 方案）
- 验收结果（通过/失败 + 证据）
- （可选）`tools.agentToAgent` 的启用范围与风险说明

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
- `V5.1` 主管返回 `DISPATCH_INCOMPLETE` 但正文声称“已安排”：查 supervisor prompt 是否缺少状态机式硬门控
- `V5.1` 新群首轮无 worker 会话：先对 worker 执行 warm-up，再复测
- `V5.1` 返回 `tool_call_required`：说明 supervisor 本轮没有任何真实工具调用，先查 prompt 是否已更新并确认重启已生效
- `V5.1` 若日志出现 `thread=true` / `subagent_spawning hooks`：说明当前 Feishu 渠道不支持这条自动补会话路径，应改为人工 warm-up
- `V5.1` 若 `sessions_send` 报 `No session found`：先查 sessionKey 是否写错。飞书群聊必须使用官方完整键 `agent:<agentId>:feishu:group:<peerId>`，不要使用 `feishu:chat:...` 或其他自造格式
- `V5.1` 若出现跨群串线：先核对 `teamKey`、hidden main 是否按 team 隔离，以及 runtime manifest 中的 session key / db / watchdog 是否落在当前 team 命名空间
- `V5.1` 若新增第 2/10 个群时行为不一致：优先比对 `teams[]` 模板输入与 runtime manifest，而不是直接手改 `openclaw.json`
- `V5.1` 若主管群 session 对真实用户消息出现裸 NO_REPLY（直接裸返回 `NO_REPLY`）：先执行 `scripts/v51_team_orchestrator_hygiene.py` 清理当前 team 的 supervisor group/main 与 worker group/main 会话；若仍未建单，立刻执行 `scripts/v51_team_orchestrator_reconcile.py --team-key <teamKey> resume-job`，不要直接让用户连续重发。
- `V5.1` 若主管接单/最终收口仍写成普通 assistant 文本：优先回到 `build-visible-ack/build-rollup-visible-message -> message -> record-visible-message` 这条显式路径，不要继续依赖 supervisor 自由发挥可见文案。
- `V5.1` worker 若从 main session 被控制面直派：`TASK_DISPATCH` 必须携带显式 `channel/accountId/target`，worker 必须按这三个字段调用 `message`，不要再依赖 session 默认 delivery context。
- `V5.1` worker 群内若出现“不带 TG 编号”或标题不统一：优先检查 `build-dispatch-payload` 是否已下发 `progressTitle/finalTitle`，并确认 worker prompt 要求首行原样使用 `【角色进度｜<jobRef>】` / `【角色结论｜<jobRef>】`。
- `V5.1` supervisor 最终收口若只有两条摘要拼接：优先检查 worker 回调是否已携带 `summary/details/risks/actionItems`，并确认 `build-rollup-visible-message` 输出的是结构化完整方案，而不是 `agentId: summary` 列表。
- `V5.1` 同一 `jobRef` 若出现两次 `【主管最终统一收口】`：视为控制面幂等缺陷；`rollupVisibleSent=true` 后只允许补 `close-job done`，不允许再次 `message send`。
- `V5.1` reconcile/control-plane 直派 worker 前会自动重置当前 `agent:<worker>:main`，避免旧 transcript 把 `TASK_DISPATCH` 拉回过时协议；手工 hygiene 时 `--include-workers` 也必须覆盖 worker `main + group`。
- `V5.1` 若 hidden main transcript 里已经出现 `COMPLETE_PACKET`，但 DB 没推进：优先执行 `scripts/v51_team_orchestrator_reconcile.py --team-key <teamKey> resume-job`。当前最高标准实现会优先消费最近有效包，跳过 `pending / placeholder / sent / <pending...>` 这类占位包，并在只剩无效包时重派当前 worker。
- `V5.1` 若 hidden main 的最新 `COMPLETE_PACKET` 仍带占位 `messageId`，但 waiting worker 的 `main` transcript 已经出现两个真实 `message` toolResult：必须优先从 worker transcript 恢复 `progressMessageId / finalMessageId` 并推进流程，不能直接删 worker 会话重派。
- `V5.1` 若 hidden main 还没真正收到 `COMPLETE_PACKET`，但 waiting worker 的 `main` transcript 已经出现 callback toolCall 草稿且拿到了两个真实 `message` toolResult：`resume-job` 必须直接把 worker transcript 提升为有效回调并推进下一 stage / rollup，不能把这种情况误判成 worker 裸 `NO_REPLY` 后重派。
- `V5.1` 主管最终统一收口必须优先使用各 worker 的完整 `finalVisibleText` 正文来整理终案方案，而不是只复述 `summary/details` 摘要；用户在群里看到的最终主管消息必须足够详细，能直接当执行底稿。
- `V5.1` 若当前 waiting worker 的新 `main` 会话对 `TASK_DISPATCH` 连续裸回 `NO_REPLY`：`resume-job` 必须在单次执行里做有限次内联重派；不能只重派一次就退出等待下一轮 timer。
- `V5.1` hidden main 包消费后若 stage 已推进，旧 stage 的 `COMPLETE_PACKET` 必须被忽略，不能在下一 stage 被重新判成 invalid packet 并触发误重派。
- `V5.1` worker 回 `COMPLETE_PACKET` 时，必须等两次 message toolResult 都返回真实 `messageId` 后，才允许发送 `status=completed`；禁止使用 `pending`、`sent`、`<pending_from_tool_1>`、`msg_*_placeholder` 等占位值。
- macOS 客户不要套用 `systemctl --user`；应使用 `launchctl bootstrap/print` 与 `templates/launchd/v51-team-watchdog.plist`
- Windows 客户不要默认承诺原生 service 版；应优先交付 `WSL2`，并保留 `templates/windows/wsl.conf.example`
- 公开群里的 `@其他机器人` 只能作为展示层，不应作为控制面正确性的唯一证据

## 可直接复用的文件
- 模板：
  - `templates/deployment-inputs.example.yaml`
  - `templates/openclaw-single-bot-route.example.jsonc`
  - `templates/openclaw-multi-bot-route.example.jsonc`
  - `templates/brownfield-change-plan.example.md`
  - `templates/verification-checklist.md`
  - `templates/systemd/v51-team-watchdog.service`
  - `templates/systemd/v51-team-watchdog.timer`
  - `templates/launchd/v51-team-watchdog.plist`
  - `templates/windows/wsl.conf.example`
- 输入样板：
  - `references/input-template-v51-team-orchestrator.json`
  - `references/input-template-v51-fixed-role-multi-group.json`
- 运行手册：
  - `references/rollout-and-upgrade-playbook.md`
  - `references/codex-prompt-templates-v51-team-orchestrator.md`
  - `references/source-cross-validation-2026-03-04.md`
  - `references/source-cross-validation-2026-03-05.md`
- `templates/systemd/v51-team-watchdog.service`
- `templates/systemd/v51-team-watchdog.timer`
- `templates/launchd/v51-team-watchdog.plist`
- `scripts/v51_team_orchestrator_hygiene.py`
- `scripts/v51_team_orchestrator_reconcile.py`
