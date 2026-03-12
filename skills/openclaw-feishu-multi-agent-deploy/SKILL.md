---
name: openclaw-feishu-multi-agent-deploy
description: Use when delivering V5.1 Hardening OpenClaw Feishu team-orchestrator setups from a unified-entry config, including brownfield rollout, validation, and upgrade-safe deployment.
---

# Feishu OpenClaw Multi-Agent

## 目标
把 OpenClaw + 飞书多 Agent 配置从“能跑”提升到“可交付”：
- 可配置：统一入口 `accounts + roleCatalog + teams`，支持多机器人、多角色分工
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
- 需要把不同群稳定建模成不同 `team units`，并由 builder 自动派生 `bindings`
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
- `parallel` stage 必须配置 `stageKey / agents / publishOrder`
- `publishOrder` 必须完整覆盖该 stage 中的全部 worker，且顺序唯一
- 每个 agent 都允许独立定制 `name / description / identity / role / responsibility / systemPrompt`
- 不再推荐多个群共享同一套全局 `supervisor_agent / ops_agent / finance_agent`
- `V5.1` 重点是模板化复制 team，而不是做任意 mesh 式 agent 工作流引擎
- `V5.1 Hardening` 固定采用 `Deterministic Orchestrator`
- 一句话原则：`LLM 负责内容，代码负责流程`
- 控制面主路径固定为：`ingress -> controller -> outbox -> sender -> structured worker response`
- worker 只提交 `progressDraft / finalDraft / summary / details / risks / actionItems`
- 群里可见消息只允许由 `controller -> outbox -> sender` 发出
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

当前主线路径统一按下面 4 条理解：
- 正常路径：ingress -> controller -> outbox -> sender -> structured worker response
- ingress transcript 扫描仅用于建单 repair；callback 不再走 hidden main / transcript recovery
- `teamKey` 是唯一内部隔离主键；`group peerId` 只是入口地址
- 插件与 OpenClaw 之间只依赖窄 adapter
- worker 可以并行分析，但群里消息必须由 controller 按 `publishOrder` 顺序发布

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
4. `references/rollout-and-upgrade-playbook.md`
5. `templates/brownfield-change-plan.example.md`

## 交付模式

### 1) 部署拓扑背景（不是第二套配置入口）
- `single-bot`：一个飞书机器人进入多个群，但主线配置入口仍然是 `accounts + roleCatalog + teams`
- `multi-bot`：多个飞书机器人（多 `accountId`）协同服务多个 team，但主线配置入口仍然是 `accounts + roleCatalog + teams`
- 无论采用哪种拓扑，交付时都不应让用户手写另一套 `routes` 入口；`bindings` 继续由 builder 派生

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
- 确认 `accounts`、`roleCatalog`、`teams`、`workflow.stages` 完整
- 主线 schema 固定按 `accounts + roleCatalog + teams(profileId + override)` 组织
- 字段边界和每层职责优先看 [v51-unified-entry-field-guide.md](references/v51-unified-entry-field-guide.md)
- 若只需要一页交付摘要，优先看 [v51-supported-boundaries-summary.md](references/v51-supported-boundaries-summary.md)
- 若采用并行 worker，必须把 `workflow.stages` 写成 stage group，并显式给出 `publishOrder`
- 允许 builder 按输入自动派生 `channels.feishu`、`bindings`、必要的 `agents.list` 与 `v51 runtime manifest`
- `roleCatalog.*.runtime` 与 `teams[].supervisor/teams[].workers[].overrides.runtime` 已是正式能力；builder 会把这些 per-agent runtime override 下沉到生成后的 `agents.list`
- 当前推荐用于统一入口的 runtime override 字段只包括：`model`、`sandbox`；`workspace / agentDir` 仍可按 agent 显式覆盖，`maxConcurrent / subagents` 继续留在顶层 `agents.defaults`
- 群/私聊 ID（`peer.id`）必须真实可用

4. 生成配置
- 优先输出最小 patch（不要覆盖整份配置）
- 推荐直接使用交付 helper，它会同时生成时间戳产物、`latest` 别名，并可选 materialize active runtime manifest：
```bash
python3 scripts/v51_team_orchestrator_deploy.py \
  --input references/input-template-v51-fixed-role-multi-group.json \
  --out references/generated \
  --openclaw-home ~/.openclaw
```
- 当前最新稳定主线 `V5.1 Hardening` 默认使用 `references/input-template-v51-fixed-role-multi-group.json`
- Linux / WSL2 若要直接拿到可启用的 watchdog unit，再加：
```bash
  --systemd-user-dir ~/.config/systemd/user
```
- macOS 若要直接拿到 launchd plist，再加：
```bash
  --launchd-dir ~/Library/LaunchAgents
```
- `references/generated/openclaw-feishu-plugin-v51-runtime-latest.json` 是最近一次生成的产物别名；现网 active manifest 统一写到 `~/.openclaw/v51-runtime-manifest.json`
- 只要传了 `--openclaw-home`，deploy 还必须同步硬化 team workspace：写入 role-specific `AGENTS.md / SOUL.md / USER.md / IDENTITY.md / TOOLS.md / HEARTBEAT.md`，并清掉默认 `BOOTSTRAP.md`
- 这些 workspace 文件属于运行时协议的一部分，不是可选装饰；若仍保留默认 bootstrap/通用人格文件，worker 和控制面可能偏离 `TASK_DISPATCH -> 单个结构化 JSON 响应 -> 控制面入库` 协议
- 当前 `TASK_DISPATCH` 不只下发 `progressTitle/finalTitle`，还会下发 `scopeLabel / forbiddenRoleLabels / forbiddenSectionKeywords / finalScopeRule`；worker 的 `finalVisibleText` 必须严格停留在自己的角色边界内
- 若是 `parallel` stage，worker 仍然只负责分析和 callback；群里 `【角色进度】/【角色结论】` 只能由 controller -> outbox 按 `publishOrder` 顺序发出
- 当前控制面在成功消费 worker callback 后，还会自动轮转 supervisor hidden main 和已完成 worker 的 main session；运行机上看到这两个 session 被清掉是预期行为，不要误判成异常
- 若只想单独生成纯构建产物，仍可直接调用 `scripts/core_feishu_config_builder.py`
- 注意：输入里的 `agents` 若只是字符串列表，脚本不会生成 `agents.list`，以避免覆盖 brownfield 现网中的详细 agent 配置。

5. 绑定排序（关键）
- `bindings` 是构建器派生结果，不是主线手工输入；人工只负责核对排序和命中结果
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
- 若是 `V5.1 Hardening` 且发生协议字段改动（`roleCatalog / teams / workflow.stages / systemPrompt / callbackCommand / hidden main`），先执行：
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
- `V5.1` 若主管群 session 首轮出现裸 NO_REPLY，或没有进入控制面而是先发生 `read/exec/sessions_spawn` 等自由漂移：不要要求用户连续重发。先执行 `scripts/v51_team_orchestrator_reconcile.py --team-key <teamKey> resume-job`；当前主线实现会从 supervisor group transcript 抢占最近未消费的真实用户消息补建单，并清理这条消息之后 supervisor 漂移出来的 subagent session。若仍未恢复，再做 hygiene。
- `V5.1` 若群里顺序乱、hidden main 开始点评 worker、或 worker 没有输出单个结构化 JSON：先核对该 team workspace 是否已经由 `v51_team_orchestrator_deploy.py --openclaw-home ...` 重新硬化；若仍是默认 `BOOTSTRAP.md / 通用 AGENTS.md` 风格文件，应先 clean redeploy，再做 hygiene 和复测。
- `V5.1` 若你在运行机上看到 `agent:supervisor_<teamKey>:main` 或已完成 worker 的 `agent:<worker>:main` 被自动删除：这是控制面在消费成功 callback 后主动做的 session 轮转，用来防止 hidden main 累积点评上下文，不需要手工恢复这些 session。
- `V5.1` 若主管接单/最终收口仍写成普通 assistant 文本：优先检查当前 team 是否真的走了 `controller -> outbox -> sender` 主路径，而不是继续依赖 supervisor 自由发挥可见文案。
- `V5.1` worker 若从 main session 被控制面直派：`TASK_DISPATCH` 必须携带显式 `channel/accountId/target`，但 worker 只产出 `progressDraft / finalDraft`，不要再自己直接 `message send`。
- `V5.1` worker 群内若出现“不带 TG 编号”或标题不统一：优先检查 `build-dispatch-payload` 是否已下发 `progressTitle/finalTitle`，并确认 worker draft 首行原样使用 `【角色进度｜<jobRef>】` / `【角色结论｜<jobRef>】`。
- `V5.1` worker 若在自己的 `finalVisibleText` 中提前写出 sibling 角色章节、主管统一收口、总方案章节，或当前 `jobRef` 下仍派生出 `sessions_spawn` 子代理：视为协议违规；`resume-job` 必须拒绝该回调、清理 job scoped subagent/main session 并重派当前 worker。
- `V5.1` supervisor 最终收口若只有两条摘要拼接：优先检查 worker 回调是否已携带 `summary/details/risks/actionItems`，并确认 `build-rollup-visible-message` 输出的是结构化完整方案，而不是 `agentId: summary` 列表。
- `V5.1` 同一 `jobRef` 若出现两次 `【主管最终统一收口】`：视为控制面幂等缺陷；`rollupVisibleSent=true` 后只允许补 `close-job done`，不允许再次 `message send`。
- `V5.1` reconcile/control-plane 直派 worker 前会自动重置当前 `agent:<worker>:main`，避免旧 transcript 把 `TASK_DISPATCH` 拉回过时协议；手工 hygiene 时 `--include-workers` 也必须覆盖 worker `main + group`。
- `V5.1` 若 worker 群消息已经发出，但 DB 没推进：优先检查 `stage_callbacks` 是否已有入库记录，并确认 worker 最后一条 assistant 是否真的输出了单个结构化 JSON。
- `V5.1` 若结构化响应被控制面拒绝：优先修正真实 `messageId / summary / details / risks / actionItems` 和角色边界，再重派当前 worker；不要退回 hidden main / plaintext / transcript 文本恢复。
- `V5.1` 当前开发主线不再从 hidden main / plaintext / transcript 文本恢复 callback；worker 完成回调只有单个结构化 JSON 响应这一条正式路径。
- `V5.1` 若 hidden main transcript 里仍出现 `COMPLETE_PACKET` 或自由文本回调：视为遗留协议漂移，不作为正式恢复路径；应 clean redeploy + hygiene 后再复测。
- `V5.1` 若 timer 自动恢复与人工 SSH 恢复可能重叠：不要同时跑两份 `resume-job`。当前主线实现已对 `resume-job / reconcile-dispatch / reconcile-rollup` 加 team 级独占锁；若命中锁，会直接返回 `reconcile_already_running`，这是预期行为，不是故障。
- `V5.1` 主管最终统一收口必须优先使用各 worker 的完整 `finalVisibleText` 正文来整理终案方案，而不是只复述 `summary/details` 摘要；用户在群里看到的最终主管消息必须足够详细，能直接当执行底稿。
- `V5.1` 若当前 stage 长时间停在 `wait_worker`：优先检查 worker 是否真的提交了 `progressDraft / finalDraft` 结构化 callback，再决定是否走 repair；不要再把 worker 的 `NO_REPLY` 当作正常完成信号。
- `V5.1` stage callback 一旦入库且 stage 已推进，重复 callback 必须被忽略；控制面只认当前 stage 的结构化 callback。
- `V5.1` worker 的最后一条 assistant 响应必须是单个 JSON 对象，主协议直接提交 `progressDraft / finalDraft / finalVisibleText / summary / details / risks / actionItems`；若附带 messageId，只能是真实 messageId，禁止使用 `pending`、`sent`、`<pending_from_tool_1>`、`msg_*_placeholder` 等占位值。
- `V5.1` gateway 重启后若出现历史 `delivery-recovery` 噪音：优先清理 `~/.openclaw/delivery-queue/` 中旧坏消息，再重启 gateway。
- macOS 客户不要套用 `systemctl --user`；应使用 `launchctl bootstrap/print` 与 `templates/launchd/v51-team-watchdog.plist`
- Windows 客户不要默认承诺原生 service 版；应优先交付 `WSL2`，并保留 `templates/windows/wsl.conf.example`
- 公开群里的 `@其他机器人` 只能作为展示层，不应作为控制面正确性的唯一证据

## 可直接复用的文件
- 模板：
  - `templates/deployment-inputs.example.yaml`
  - `templates/brownfield-change-plan.example.md`
  - `templates/verification-checklist.md`
  - `templates/openclaw-v51-team-orchestrator.example.jsonc`
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
- `templates/systemd/v51-team-watchdog.service`
- `templates/systemd/v51-team-watchdog.timer`
- `templates/launchd/v51-team-watchdog.plist`
- `scripts/v51_team_orchestrator_hygiene.py`
- `scripts/v51_team_orchestrator_reconcile.py`
