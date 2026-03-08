# OpenClaw-Feishu-Multi-Agent

面向交付团队的通用 Skill 仓库：用于基于 OpenClaw 搭建飞书多机器人多角色多 Agent 协作体系，支持客户环境快速落地、增量上线、可回滚与可升级。

## 当前版本

- `v1.6.1`（2026-03-08）
- 默认技术路线：官方插件 `@openclaw/feishu`
- 兼容路线：legacy `chat-feishu`
- 当前主线版本：`V3.1` 跨群生产、`V4.3.1` 单群生产、`V5 Team Orchestrator` 多群模板化生产
- 当前 `V5` 的推荐生产形态：`V5.1 Hardening`
- 客户定制保留件：`V4.3.1-C1.0`（与 `V4.3.1` 同协议，保留客户专属群与机器人配置）

## 仓库结构

```text
agents/
  openai.yaml
skills/
  openclaw-feishu-multi-agent-deploy/
    SKILL.md
    templates/
    references/
    scripts/
CHANGELOG.md
VERSION
README.md
```

## 核心能力

- 单机器人/多机器人多 Agent 路由（single-bot / multi-bot）
- Brownfield 增量改造（incremental）与灰度放量（canary）
- 配置生成脚本（从输入 JSON 生成 patch + 验证摘要）
- 前置条件、验收清单、回滚流程、升级回归手册
- `V5 Team Orchestrator`：多个飞书群，每群 `1` 个主管 + `N` 个 worker，可模板化扩展角色、职能与提示词
- `V5.1 Hardening`：在 `V5` 上把流程推进下沉到确定性控制面，`LLM 负责内容，代码负责流程`
- 直接给 Codex 使用的完整交付模板、真实双群示例和 `v5 runtime manifest`

## 平台兼容矩阵

| 平台 | 交付建议 | service 管理 | 当前建议 |
|---|---|---|---|
| `Linux` | 正式推荐 | `systemd --user` | 生产首选 |
| `macOS` | 正式推荐 | `launchd` / `LaunchAgent` | 生产可用 |
| `Windows + WSL2` | 正式推荐 | 复用 Linux 路线（建议启用 `systemd`） | Windows 客户首选 |
| `Windows 原生` | 不作为默认生产路径 | 需单独评估 | 不默认承诺 |

核心原则：
1. `V4.3.1` 的运行模型不按平台分叉，分叉的是 service 管理与运维模板。
2. Windows 客户默认按 `WSL2` 交付，不把 Windows 原生 service 当成标准路线。
3. `SQLite + hidden main session + 6 类群内可见消息` 这套协议，在 Linux / macOS / WSL2 上保持一致。

## 快速使用

1. 进入 Skill 目录

```bash
cd skills/openclaw-feishu-multi-agent-deploy
```

2. 填写输入模板（任选其一）

- `references/input-template.json`（默认 plugin）
- `references/input-template-plugin.json`（plugin 完整示例）
- `references/input-template-legacy-chat-feishu.json`（legacy 兼容）
- `references/input-template-v5-team-orchestrator.json`（`V5 Team Orchestrator` 多群模板化示例）
- `references/input-template-v5-fixed-role-multi-group.json`（固定 bot-role 映射、群级角色组合自由的正式推荐模板）

3. 生成 patch

```bash
python3 scripts/core_feishu_config_builder.py \
  --input references/input-template.json \
  --out references/generated
```

4. 在 OpenClaw 环境执行验证

```bash
openclaw config validate
openclaw gateway restart
openclaw agents list --bindings
```

## V5 Team Orchestrator 快速入口

如果你的目标是“多个飞书群，每个群内都是多个 agent，且每个群都能自定义角色、职能与提示词”，优先按 `V5 Team Orchestrator` 建模：

当前生产推荐直接采用 `V5.1 Hardening`：
- 不再让 supervisor prompt 自己判断下一步
- 必须使用 `start-job-with-workflow`
- 必须使用 `build-visible-ack`
- 必须使用 `get-next-action`
- 必须使用 `build-dispatch-payload`
- 最终收口前必须使用 `build-rollup-context` 和 `build-rollup-visible-message`
- 群里主管可见消息发出后，必须执行 `record-visible-message`
- timer 必须运行 `v51_team_orchestrator_reconcile.py resume-job`
- 不把 `WARMUP` 当成常规运行依赖
- 若主管群 session 对真实用户消息直接裸返回 `NO_REPLY`，先执行 `v51_team_orchestrator_hygiene.py` 清理 team 会话；若仍未建单，交给 `v51_team_orchestrator_reconcile.py` 从 transcript 补建单与补派发
- 若当前 waiting worker 的新 `main` 会话对 `TASK_DISPATCH` 裸回 `NO_REPLY`，`resume-job` 必须在单次执行里做有限次内联重派，而不是只重派一次后等待下一轮 timer

1. 输入模板：
- [V5 Team Orchestrator 输入模板](skills/openclaw-feishu-multi-agent-deploy/references/input-template-v5-team-orchestrator.json)
- [V5 固定角色多群模板](skills/openclaw-feishu-multi-agent-deploy/references/input-template-v5-fixed-role-multi-group.json)

2. 交付文档：
- [V5 Team Orchestrator 交付模板](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v5-team-orchestrator.md)
- [V5.1 新机器快速启动 SOP](skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md)
- [客户首次使用信息清单](skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用信息清单.md)
- [客户首次使用-Codex提示词](skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用-Codex提示词.md)
- [客户首次使用真实案例](skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md)

3. 去敏配置快照：
- [V5 Team Orchestrator JSONC 参考快照](skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v5-team-orchestrator.example.jsonc)

4. runtime 模板：
- `templates/systemd/v5-team-watchdog.service`
- `templates/systemd/v5-team-watchdog.timer`
- `templates/launchd/v5-team-watchdog.plist`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py`

5. 生成器额外产物：
- `openclaw-feishu-plugin-v5-runtime-<timestamp>.json`
- 该文件就是 `v5 runtime manifest`，用于 Codex、watchdog、session hygiene、canary 和回滚脚本按 `teamKey` 取值

当前正式双群基线：
- 内部团队群：`oc_f785e73d3c00954d4ccd5d49b63ef919`
- 外部团队群：`oc_7121d87961740dbd72bd8e50e48ba5e3`
- 三个正式机器人：`aoteman` / `xiaolongxia` / `yiran_yibao`
- 当前 `V5` 正式 teamKey：`internal_main` / `external_main`

设计原则：
- 每个群都是一个独立 `team unit`
- `One Team = 1 Supervisor + N Workers`
- 当前生产推荐标准：`bot 复用，role 固定`
- 同一个 bot 可以跨很多群复用，但它在所有群里都保持同一个角色
- 每个群的角色组合可以不同，只需要在该 `team` 下启用需要的 `workers`
- `teamKey` 驱动 agentId / workspace / memory / watchdog 命名
- `workflow.stages` 必须把当前 team 的每个 worker 恰好声明一次；主管最终收口前必须等所有已登记 worker 完成
- 每个 agent 都允许单独定制 `name / description / identity / role / responsibility / systemPrompt`
- 不再推荐多个群共享同一套全局 `supervisor_agent / ops_agent / finance_agent`
- `V5.1 Hardening` 采用 `Deterministic Orchestrator`：`watchdog-tick -> v51_team_orchestrator_reconcile.py resume-job -> start-job-with-workflow -> build-visible-ack -> record-visible-message -> get-next-action -> build-dispatch-payload -> reset waiting worker main session -> mark-dispatch/mark-worker-complete -> build-rollup-context -> build-rollup-visible-message -> record-visible-message -> close-job`
- `resume-job` 必须优先消费 hidden main transcript 中最近的有效 `COMPLETE_PACKET`；若最新包是 `pending / placeholder / sent / <pending...>` 之类占位值，必须忽略并继续向后找最近有效包；若当前只剩无效包，则强制重派当前 worker
- 若 hidden main 里的 `COMPLETE_PACKET` 仍是占位 messageId，但当前 waiting worker 的 `main` transcript 已经拿到了两个真实 `message` toolResult，`resume-job` 必须先从 worker transcript 恢复真实 `progressMessageId / finalMessageId`，再推进下一 stage / rollup，不能直接删会话重派
- `resume-job` 在当前 stage 还未完成时，必须忽略已消费旧 stage 的 hidden main 包；旧包不能在下一 stage 被重新当成 invalid packet 触发误重派
- 一句话原则：`LLM 负责内容，代码负责流程`

推荐固定映射：
- `aoteman -> supervisor`
- `xiaolongxia -> ops`
- `yiran_yibao -> finance`

## 默认专家库 / Default Expert Catalog

适用原则：
- 下面这 30 个默认专家按职能分类，可跨行业复用
- 专家名称使用英文，便于直接复用到 `agentId / role / prompt seed`
- 专家描述使用中文，便于交付时快速理解和改写

### 管理与协调 / Management & Orchestration
- `TeamOrchestrator`：负责任务接单、拆解、调度、统一收口，适合作为多专家团队主管。
- `ProjectCoordinator`：负责里程碑、依赖关系、执行节奏和跨角色协同推进。
- `DecisionAdvisor`：负责方案比较、优先级判断和关键决策建议输出。

### 增长与营销 / Growth & Marketing
- `GrowthStrategist`：负责增长目标拆解、渠道策略、拉新与转化路径设计。
- `CampaignPlanner`：负责活动方案、传播节奏、内容日历和落地动作安排。
- `BrandCopyLead`：负责品牌表达、核心卖点提炼、传播话术和文案方向。

### 销售与商务 / Sales & Business
- `SalesCloser`：负责商机推进、成交路径设计、异议处理和成单建议。
- `AccountPlanner`：负责客户分层、机会盘点、跟进节奏和客户经营计划。
- `PartnershipManager`：负责渠道合作、商务拓展、联合方案与资源置换设计。

### 财务与风控 / Finance & Risk
- `FinancialController`：负责预算控制、毛利测算、ROI 校验和财务红线管理。
- `BudgetPlanner`：负责成本分配、投入节奏、预算方案和资源使用建议。
- `RiskOfficer`：负责识别经营、履约、现金流和合规风险，并给出防控措施。

### 产品与项目 / Product & Delivery
- `ProductLead`：负责需求澄清、方案定义、优先级判断和产品路径规划。
- `ProductAnalyst`：负责用户问题分析、需求洞察、功能拆解和价值判断。
- `DeliveryManager`：负责交付计划、推进节奏、风险提醒和结果验收对齐。

### 运营与履约 / Operations & Fulfillment
- `OperationsManager`：负责日常运营策略、执行节奏、资源协调和流程落地。
- `FulfillmentManager`：负责履约链路、库存协同、交付质量和异常处理。
- `SOPDesigner`：负责标准流程设计、执行规范、检查清单和流程优化建议。

### 客户成功与服务 / Customer Success & Service
- `CustomerSuccessLead`：负责客户目标对齐、续约策略、满意度提升和长期经营。
- `ServiceQualityManager`：负责服务标准、质量巡检、反馈闭环和服务改进。
- `RetentionSpecialist`：负责留存策略、流失预警、召回动作和客户活跃提升。

### 数据与分析 / Data & Analytics
- `DataAnalyst`：负责数据整理、指标拆解、趋势分析和关键结论输出。
- `RevenueAnalyst`：负责收入结构分析、利润表现、价格影响和增长机会识别。
- `InsightResearcher`：负责调研信息汇总、洞察提炼、问题定位和决策输入。

### 人力与组织 / HR & Organization
- `TalentPartner`：负责人岗匹配、组织支持、人才盘点和关键岗位建议。
- `RecruiterLead`：负责招聘策略、岗位画像、候选人筛选和招聘节奏设计。
- `OrgDevelopmentManager`：负责组织协同、机制优化、绩效节奏和团队发展建议。

### 法务与合规 / Legal & Compliance
- `ComplianceCounsel`：负责合规审查、制度边界识别和风险提示，不替代正式法律意见。
- `ContractManager`：负责合同条款梳理、履约约束识别和关键条款风险提醒。
- `PolicyAdvisor`：负责政策理解、监管变化跟踪和业务规则适配建议。

runtime 命名约定：
- hidden main：`agent:<supervisorAgentId>:main`
- SQLite：`~/.openclaw/teams/<teamKey>/state/team_jobs.db`
- systemd：`v5-team-<teamKey>.service` / `v5-team-<teamKey>.timer`
- launchd：`bot.molt.v5-team-<teamKey>`

当前双群对应 hidden main：
- `agent:supervisor_internal_main:main`
- `agent:supervisor_external_main:main`

Codex 交付入口：
- [V5 Team Orchestrator 交付模板](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v5-team-orchestrator.md)
- 这份文档已经写入当前 2 个正式群、3 个正式机器人、可直接复制给 Codex 的长版提示词和运行命令
- 其中 `V5.1 Hardening` 的控制面命令必须明确出现：`start-job-with-workflow`、`build-visible-ack`、`get-next-action`、`build-dispatch-payload`、`build-rollup-context`、`build-rollup-visible-message`、`record-visible-message`，以及 `v51_team_orchestrator_reconcile.py` 的 `resume-job / reconcile-dispatch / reconcile-rollup`

## V4.3.1 快速启动

如果你的目标是“在一台新机器上快速拉起单群生产稳定版”，直接按这两个入口执行：

1. 完整上线手册：
- [V4.3.1 新机器快速启动 SOP](skills/openclaw-feishu-multi-agent-deploy/references/v4-3-1-quick-start.md)

2. Codex 真实交付模板：
- [V4.3.1 单群生产稳定版模板](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md)
- [V4.3.1-C1.0 客户定制模板](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production-C1.0.md)

3. 去敏配置快照：
- [V4.3.1 单群生产配置快照](skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v4-3-1-single-group-production.example.jsonc)

其中最关键的两个命令是：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_runtime.py \
  --db ~/.openclaw/workspace-supervisor_agent/.openclaw/team_jobs.db \
  init-db
```

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_hygiene.py \
  --home ~/.openclaw \
  --group-peer-id oc_f785e73d3c00954d4ccd5d49b63ef919 \
  --include-workers \
  --delete-transcripts
```

作用：
1. `init-db`：初始化 SQLite 状态层
2. `v431_single_group_hygiene.py`：在首次上线、协议变更或脏上下文后，一次性清理 `supervisor group/main + worker group` 会话，避免旧会话污染新任务

## V4.3.1 跨平台部署路线

`V4.3.1` 的核心运行模型一致，差异只在 watchdog 和服务托管方式。

### Linux / WSL2

- OpenClaw 主运行时：官方 CLI + `systemd --user`
- watchdog：
  - [systemd service 模板](skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v4-3-watchdog.service)
  - [systemd timer 模板](skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v4-3-watchdog.timer)
- 典型安装：

```bash
systemctl --user daemon-reload
systemctl --user enable --now v4-3-watchdog.timer
systemctl --user status v4-3-watchdog.timer
```

### macOS

- OpenClaw 主运行时：官方 CLI + `launchd` / `LaunchAgent`
- watchdog：
  - [launchd 模板](skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v4-3-watchdog.plist)
- 典型安装：

```bash
mkdir -p ~/Library/LaunchAgents ~/.openclaw/logs
cp skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v4-3-watchdog.plist ~/Library/LaunchAgents/bot.molt.v4-3-watchdog.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/bot.molt.v4-3-watchdog.plist 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/bot.molt.v4-3-watchdog.plist
launchctl print gui/$(id -u)/bot.molt.v4-3-watchdog
```

### Windows

- 默认推荐：`Windows + WSL2`，不要把 OpenClaw 主运行时直接放在 Windows 原生 service。
- 参考文档：
  - [Windows / WSL2 部署说明](skills/openclaw-feishu-multi-agent-deploy/references/windows-wsl2-deployment-notes.md)
  - [WSL2 systemd 示例](skills/openclaw-feishu-multi-agent-deploy/templates/windows/wsl.conf.example)

说明：
- `openclaw gateway restart` 这条 CLI 命令在三条推荐路线中保持一致。
- `WARMUP` 仍然是一次性初始化动作，不是最终用户日常操作。

## 飞书与 OpenClaw 信息采集（你现在最容易卡的点）

先把这三类 ID 和凭据补齐，不然会出现“绑定找不到”“路由命中不到”的问题。  
你给的群已经建好但找不到群 ID 时，按这个顺序执行。

### 一、如何拿到飞书群 `chat_id`

方法 1（建议）：用飞书事件日志拿 `chat_id`  
1. 让任意一位群成员发一条测试消息（@机器人即可）到目标群。  
2. 打开 OpenClaw 实时日志或事件日志：  
   `openclaw logs --follow`  
3. 找到飞书入站事件里 `peer.id` 字段（群聊会是 `peer.kind=group`），例如 `oc_9f31a...`。  
4. 这里的 `peer.id` 就是你要用的群 ID。

方法 2：通过事件订阅测试拉到真实回调  
1. 飞书开放平台应用后台开启 `im.message.receive_v1`。  
2. 发一次测试消息后，在回调内容里读取：  
   `event.message.chat_id` 或 `event.message.chat_id`/`event.chat_id` 对应到的会话 ID。  
3. 群聊通常与 `peer.id` 一致，可直接用于 `match.peer.id`。

方法 3（兜底）：从历史日志回溯  
1. 找到最近一条群消息在 openclaw 的日志。  
2. 从原始入站 JSON 中提取 `peer.id`。  
3. 优先用方法 1/2 采集到的 ID。

### 二、如何拿到 Agent 和账号的真实标识

1) Agent ID（`agentId`）  
- 用命令：`openclaw agents list`  
- 以 `agentId` 名称为准（`agents` 的内部 ID）。  
- 不要用中文名字、头像、用途说明充当 id。  

2) 飞书机器人账号（`accountId`）  
- 在现网配置里读取：`channels.feishu.accounts` 的键名即是 `accountId`。  
- 不要把 `appId` 当成 `accountId`。  
- 绑定里 `match.accountId` 必须和这个键名完全一致。  

3) 应用凭据（`appId` / `appSecret`）  
- 统一来自飞书应用控制台（多 bot 分别独立记录）。  
- 建议先把应用信息写入一个加密的 `credentials` 表（至少包含 `accountId`、`appId`、`appSecret`、`encryptKey`、`verificationToken`）。

4) 事件校验参数（`encryptKey` / `verificationToken`）  
- 来源：飞书开放平台 -> 应用 -> 开发配置 -> 事件与回调。  
- 每个机器人（每个应用）各自独立一套，不能混用。  
- 生产配置建议必填，避免事件校验或回调链路异常。

### 三、按你的示例写一版可直接落地的映射

你当前真实值（基于日志探测）可直接用：

- 销售群：`oc_ffab0130d2cfb80f70c150918b4d4e87`  
- 运营群：`oc_da719e85a3f75d9a6050343924d9aa62`  
- 财务群：`oc_1a3c32a99d6a8120f9ca7c4343263b24`  
- Agent ID：`sales_agent`、`ops_agent`、`finance_agent`  
- 账号：`aoteman`、`xiaolongxia`、`yiran_yibao`

机器人名称与账号对照（你当前私有测试）：
- 奥特曼：`accountId=aoteman`，`appId=cli_a923c749bab6dcba`
- 小龙虾找妈妈：`accountId=xiaolongxia`，`appId=cli_a9f1849b67f9dcc2`
- 易燃易爆：`accountId=yiran_yibao`，`appId=cli_a923c71498b8dcc9`

匹配关系应写成：

```text
peer: oc_ffab0130d2cfb80f70c150918b4d4e87 -> agentId: sales_agent，accountId: aoteman
peer: oc_da719e85a3f75d9a6050343924d9aa62 -> agentId: ops_agent，accountId: xiaolongxia
peer: oc_1a3c32a99d6a8120f9ca7c4343263b24 -> agentId: finance_agent，accountId: yiran_yibao
```

### 四、群角色与权限（业内最佳实践）
- 开场默认用 `requireMention: true`，避免无意识触发。  
- 如果某些群允许免 `@`，只对特定群级别开启 `requireMention: false` 并确认飞书已开通 `im:message.group_msg`。  
- 多 bot 同群时默认 `allowMentionlessInMultiBotGroup: false`，再按业务谨慎逐群放开。  
- 以 `agentId` 能映射为准，`peer.kind` 一般用 `group`。  
- 尽量保持 `channels.feishu.defaultAccount` 为当前主 bot，避免回退路由不可控。  

### 五、飞书权限清单（含多维表格）

以下按“你能否稳定跑通”分层。建议在飞书开放平台 `权限管理 -> 批量导入/手动勾选` 统一处理。

#### 1) 消息与路由基础（必需）
- `im:message`
- `im:message.p2p_msg:readonly`
- `im:message.group_at_msg:readonly`
- `im:message:send_as_bot`
- `im:resource`

#### 2) 群免 @（按需）
- `im:message.group_msg`

说明：未开启该权限时，请保持 `requireMention=true`。

#### 2.1) 外部群补充说明（很容易误判）

如果目标群是飞书外部群，优先检查的不是额外 `scope`，而是应用是否已开启“对外共享/允许外部用户使用”并完成审批。
外部群能力不应通过在 `scopes` 里继续追加猜测性的权限来排障；生产上应先确认：

- 应用已经开启对外共享，且当前版本已重新发布并审批生效
- 机器人可以被搜索并成功加入外部群
- 外部群中的 `@机器人` 消息能真实进入事件订阅与 gateway 日志

注意：
- “群里是否出现已查看/已读标志”不是 OpenClaw 飞书通道的验收标准，尤其不适合作为外部群权限是否正常的唯一依据
- 外部群验收应以 `openclaw logs --follow`、真实 `messageId`、以及 canary 结果为准

#### 3) 文档/知识（按需）
- `docs:document.content:read`
- `sheets:spreadsheet`
- `wiki:wiki:readonly`

#### 4) 多维表格（Bitable/Base，按需）

飞书租户和 API 版本可能展示为不同命名体系（`bitable:*` 或 `base:*`）。  
实操建议：先在你要调用的 API 文档页右侧查看“权限要求”，按该页面显示为准。

推荐最小集合：
- 只读场景：`bitable:app:readonly`（或同义 `base:*` 只读权限）
- 读写场景：`bitable:app`（或同义 `base:*` 读写权限）

如果你的 Agent 要做“查表 + 写记录 + 改字段/表结构”，通常需要覆盖：
- 应用级权限（app/base）
- 记录级权限（record）
- 表级权限（table/field）

上线前务必用真实 token 试一条最小 API（例如读 1 行、写 1 行）验证权限闭环。

#### 5) 权限汇总（推荐生产，一键复制）

下面这份是“多 Agent + 多路由 + 文档 + 多维表格”可用的推荐汇总权限。  
你可以直接在飞书开放平台权限管理里批量导入。

```json
{
  "scopes": {
    "tenant": [
      "im:message",
      "im:message.p2p_msg:readonly",
      "im:message.group_at_msg:readonly",
      "im:message.group_msg",
      "im:message:readonly",
      "im:message:send_as_bot",
      "im:message:update",
      "im:message:recall",
      "im:message.reactions:read",
      "im:resource",
      "im:chat",
      "im:chat.members:bot_access",
      "im:chat.access_event.bot_p2p_chat:read",
      "contact:user.base:readonly",
      "contact:contact.base:readonly",
      "docs:document.content:read",
      "sheets:spreadsheet",
      "docx:document:readonly",
      "docx:document",
      "docx:document.block:convert",
      "drive:drive:readonly",
      "drive:drive",
      "wiki:wiki:readonly",
      "wiki:wiki",
      "bitable:app:readonly",
      "bitable:app",
      "task:task:read",
      "task:task:write"
    ],
    "user": []
  }
}
```

说明：
- 多维表格权限在部分租户控制台会显示为 `base:*` 命名；若你的控制台没有 `bitable:*`，按页面提示替换为对应的 `base:*` 等价权限即可。
- 如果你不需要“免 @ 群触发”，可去掉 `im:message.group_msg` 并保持 `requireMention=true`。
- 如果目标是飞书外部群，不需要在这份 JSON 里额外追加“外部群专用 scope”；应改查应用是否已开启对外共享并审批通过。

### 六、ID 对照表（避免把名字当 ID）

| 名称 | 示例 | 在哪拿到 | 是否用于路由 |
|---|---|---|---|
| 群 ID（`chat_id` / `peer.id`） | `oc_ffab0130d2cfb80f70c150918b4d4e87` | 群里发消息后看 `openclaw logs --follow` | 是（`match.peer.id`） |
| 用户 Open ID（`open_id`） | `ou_xxx` | 私聊发消息后看 `openclaw logs --follow` 或 `openclaw pairing list feishu` | 否（常用于 allowFrom） |
| 机器人账号 ID（`accountId`） | `aoteman` | 你在 `channels.feishu.accounts` 的键名（自己定义） | 是（`match.accountId`） |
| 飞书应用 ID（`appId`） | `cli_xxx` | 飞书开放平台 `凭证与基础信息` | 否（用于账号凭据） |
| 机器人 Open ID（bot open_id） | `ou_bot_xxx` | 飞书事件体 / 平台调试信息 | 否（通常不直接配路由） |
| Agent ID（`agentId`） | `sales_agent` | `openclaw agents list` | 是（`binding.agentId`） |

### 七、一步一步配置流程（照着做可落地）

1. 飞书后台准备  
- 按路由架构创建应用（可 1 个，也可多个；生产常见是 2~4 个）。  
- 开启机器人能力。  
- 在权限管理里完成“基础权限 + 按需权限（文档/多维表格）”。  
- 订阅事件至少包含：`im.message.receive_v1`。  

2. OpenClaw 账号配置  
- 在 `channels.feishu.accounts` 配置实际 `accountId` 及凭据（一个 bot 对应一个 accountId）。  
- 显式设置 `defaultAccount`。  

3. 收集路由 ID  
- 在销售/运营/财务群分别发测试消息。  
- 执行 `openclaw logs --follow`，记录三个 `oc_...`。  
- 执行 `openclaw agents list`，确认 `sales_agent` / `ops_agent` / `finance_agent` 已存在。  

4. 绑定与排序  
- 为每个群配置一条精确 binding：`channel + accountId + peer.id -> agentId`。  
- 保证顺序：精确规则在前，兜底在后。  

5. 变更上线  
- 先备份配置。  
- 运行 `openclaw config validate`。  
- 重启 `openclaw gateway`。  
- 执行 `openclaw agents list --bindings` 检查结果。  
- 先 canary 群验证，再全量。  

6. 扩展策略  
- 新增群：新增一条 route。  
- 新增 agent：新增 `agentId` + route。  
- 新增机器人：新增 `accountId` + 凭据 + routes。  

### 八、路由架构选型（如何选“一群一Bot”或“一Bot多群”）

#### 模式 A：一群一Bot（推荐）

定义：每个业务群只放一个机器人，且该机器人只服务该群（或少量同类群）。

优点：
- 路由最清晰，排障简单。
- 几乎没有抢答和误触发。
- 权限隔离更直观，便于审计。

缺点：
- 机器人数量更多，维护成本略高。

适用：
- 销售、运营、财务等职责边界清晰的团队。
- 对稳定性和可追责要求高的生产环境。

#### 模式 B：一Bot多群

定义：一个机器人进入多个群，通过不同 `peerId` 路由到不同 agent。

优点：
- 机器人数量少，初期部署快。
- 适合 MVP/试点。

缺点：
- 规则复杂度更高，后期容易膨胀。
- 若误配兜底规则，容易串线。

适用：
- 团队小、场景简单、先快速验证价值。

#### 你的当前状态（真实）

你从日志中抓到：
- `oc_ffab0130d2cfb80f70c150918b4d4e87` -> `accountId=aoteman`
- `oc_da719e85a3f75d9a6050343924d9aa62` -> `accountId=xiaolongxia`
- `oc_1a3c32a99d6a8120f9ca7c4343263b24` -> `accountId=yiran_yibao`

这已经是“模式 A：一群一Bot”的结构，建议继续沿用。

#### 你当前场景的推荐路由（可直接套用）

```yaml
routes:
  - { peerKind: "group", peerId: "oc_ffab0130d2cfb80f70c150918b4d4e87", accountId: "aoteman",      agentId: "sales_agent" }
  - { peerKind: "group", peerId: "oc_da719e85a3f75d9a6050343924d9aa62", accountId: "xiaolongxia",  agentId: "ops_agent" }
  - { peerKind: "group", peerId: "oc_1a3c32a99d6a8120f9ca7c4343263b24", accountId: "yiran_yibao",  agentId: "finance_agent" }
```

#### 常用配置示例（真实可落地）

示例 1：标准企业（推荐）
- 销售群 -> `bot_sales` -> `sales_agent`
- 运营群 -> `bot_ops` -> `ops_agent`
- 财务群 -> `bot_finance` -> `finance_agent`

示例 2：轻量团队（低成本）
- `bot_main` 同时服务销售群 + 运营群
- `bot_finance` 独立服务财务群

示例 3：扩展到主管调度
- 在管理群增加 `bot_supervisor`
- 主管 Agent 通过 `agentToAgent` 分派给销售/运营/财务子 Agent

## 使用 Codex 的实战案例（安装到上线）

下面这套话术可直接复制给 Codex，后续新增 agent 或新增机器人只需按“扩展表”增加行。

### 1) 先安装 skill

```text
请使用 $skill-installer，
从 GitHub 安装这个 skill 到我的 Codex：
https://github.com/seaworld008/OpenClaw-Feishu-Multi-Agent/tree/main/skills/openclaw-feishu-multi-agent-deploy
安装成功后提醒我重启 Codex。
```

### 2) 重启后直接发这个标准任务（可扩展版）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，完成本次飞书多 Agent 配置。

交付边界：
- 现网为 brownfield，必须 incremental（仅做必要最小改动）。
- 配置目标 channel = feishu（官方插件）。
- 不改 `bindings` 与 `channels.feishu` 无关字段。

输入信息（请严格按下面结构读取/补齐，后续可扩展）：
- accountMappings:
  - accountId: "aoteman"
    role: "sales_bot"
    appId: "cli_a923c749bab6dcba"
    appSecret: "TWpD207Ri2g1Qqmw4R5YhfkPRhOokCGX"
    encryptKey: "..."
    verificationToken: "..."
  - accountId: "xiaolongxia"
    role: "ops_bot"
    appId: "cli_a9f1849b67f9dcc2"
    appSecret: "g7dTIRe6Tz8jYzASSKTT2eBV5LGzrKDr"
    encryptKey: "..."
    verificationToken: "..."
  - accountId: "yiran_yibao"
    role: "finance_bot"
    appId: "cli_a923c71498b8dcc9"
    appSecret: "swscrlPKYCwAehOyyoLrlesLTsuYY6nl"
    encryptKey: "..."
    verificationToken: "..."
- agents: ["sales_agent", "ops_agent", "finance_agent"]
- routes:
  - peerKind: "group"
    peerId: "oc_ffab0130d2cfb80f70c150918b4d4e87"
    accountId: "aoteman"
    agentId: "sales_agent"
  - peerKind: "group"
    peerId: "oc_da719e85a3f75d9a6050343924d9aa62"
    accountId: "xiaolongxia"
    agentId: "ops_agent"
  - peerKind: "group"
    peerId: "oc_1a3c32a99d6a8120f9ca7c4343263b24"
    accountId: "yiran_yibao"
    agentId: "finance_agent"

可选扩展示例：
- 如果新增一个业务群和机器人，只需再加一条 accountMappings 和对应 routes。
- 如果新增一个 Agent，只需再加一条 routes 的 agentId；agents 列表里新增该 id。

要求：
1) 先读取现有 ~/.openclaw/openclaw.json。
2) 输出 to_add / to_update / to_keep_unchanged。
3) 仅输出最小 patch，包含 channels.feishu、bindings、agents.list（必要新增）以及 tools.agentToAgent（按我明确开启才改）。
4) bindings 排序必须“精确规则优先（peer+account）→ account 精确→兜底”。
5) 输出完整命令：
   - 备份命令
   - openclaw config validate
   - openclaw gateway restart
   - openclaw agents list --bindings
   - canary 验收步骤
6) 输出回滚命令与验收证据模板。
```

3. 你只需要把占位值换成真实值
- `accountId`、`appId`、`appSecret`
- 群 ID（`oc_xxx`）和 Agent ID
- 是否免 @（若免 @，确认飞书已审批 `im:message.group_msg`）

### 占位值替换对照（重点）

你提到的这三行：

- `oc_ffab0130d2cfb80f70c150918b4d4e87 -> sales_agent（accountId=aoteman）`
- `oc_da719e85a3f75d9a6050343924d9aa62 -> ops_agent（accountId=xiaolongxia）`
- `oc_1a3c32a99d6a8120f9ca7c4343263b24 -> finance_agent（accountId=yiran_yibao）`

其中每一段都需要替换为你的真实值。按下面对照填：

| 示例占位 | 你要替换成什么 | 来源位置 | 常见错误 |
|---|---|---|---|
| `oc_ff...` / `oc_da...` / `oc_1a3...` | 飞书群真实 `chat_id`（通常以 `oc_` 开头） | 飞书事件 `im.message.receive_v1` 的 `chat_id`；或 OpenClaw 日志中收到消息时的会话 ID | 用了群名称而不是 `chat_id`；把多个群写成同一个 ID |
| `sales-agent` / `ops-agent` / `finance-agent` | OpenClaw 中已存在的 `agentId` | `openclaw agents list` | 写了 persona 名称但不是 `agentId`；拼写不一致 |
| `aoteman` / `xiaolongxia` / `yiran_yibao` | `channels.feishu.accounts` 里的账号键名（`accountId`） | 你的 `openclaw.json` 中 `channels.feishu.accounts.<key>` | `bindings.match.accountId` 和 accounts 键名不一致 |

### 一份可直接照抄的“替换后”示例

假设你的真实值是（你当前就是这组）：
- 销售群：`oc_ffab0130d2cfb80f70c150918b4d4e87`
- 运营群：`oc_da719e85a3f75d9a6050343924d9aa62`
- 财务群：`oc_1a3c32a99d6a8120f9ca7c4343263b24`
- Agent ID：`sales_agent`、`ops_agent`、`finance_agent`
- 账号：`aoteman`、`xiaolongxia`、`yiran_yibao`

那么路由就应写成：

```text
- oc_ffab0130d2cfb80f70c150918b4d4e87 -> sales_agent（accountId=aoteman）
- oc_da719e85a3f75d9a6050343924d9aa62 -> ops_agent（accountId=xiaolongxia）
- oc_1a3c32a99d6a8120f9ca7c4343263b24 -> finance_agent（accountId=yiran_yibao）
```

### 上线前 5 条强校验（避免配错）

1. `chat_id` 唯一：一个群只对应一条精确 binding。  
2. `agentId` 存在：`openclaw agents list` 能查到。  
3. `accountId` 对齐：`bindings.match.accountId` 必须等于 `channels.feishu.accounts` 的键名。  
4. 顺序正确：精确规则在前，兜底规则在后。  
5. 先验证再放量：先 canary 群验证通过，再全量。

4. 交付验收建议
- 先在 canary 群验证，再全量放量
- 每条 binding 至少做一次实测（群+私聊）
- 留存回滚命令和验证证据（日志/截图/命令输出）

## 主线版本与阅读顺序

仓库主线已经收敛为 3 条：

| 主线版本 | 定位 | 适合场景 | 核心入口 |
|---|---|---|---|
| `V3.1` | 跨群生产主线 | 主管群派单，销售/运营/财务分群执行并自动收口 | `references/codex-prompt-templates-v3.1.md` |
| `V4.3.1` | 单群生产主线 | 一个群内主管 + worker 长期稳定运行 | `references/codex-prompt-templates-v4.3.1-single-group-production.md` |
| `V5 Team Orchestrator` | 多群模板化主线 | 多个群并行、每群独立 team unit、可复制到 2/10 个团队 | `references/codex-prompt-templates-v5-team-orchestrator.md` |

选择建议：
1. 业务天然分群，且需要主管跨群调度，选 `V3.1`。
2. 业务集中在一个群内，且要求真实长期上线，选 `V4.3.1`。
3. 客户要多个团队群独立运行，并且后面还会持续扩群，直接上 `V5 Team Orchestrator`。

推荐阅读顺序：
1. `references/prerequisites-checklist.md`
2. `templates/deployment-inputs.example.yaml`
3. `references/codex-prompt-templates-v3.1.md` 或 `references/codex-prompt-templates-v4.3.1-single-group-production.md`
4. 如果目标是多群模板化，再读 `references/codex-prompt-templates-v5-team-orchestrator.md`
5. `templates/verification-checklist.md`
6. `references/rollout-and-upgrade-playbook.md`

当前保留的最佳实践来源：
- OpenClaw 官方文档与 Release 交叉验证：`references/source-cross-validation-2026-03-04.md`
- OpenClaw / 飞书平台能力复核：`references/source-cross-validation-2026-03-05.md`
- `V4.3.1` 单群生产稳定版交叉验证：`references/source-cross-validation-2026-03-07-v4-3-1.md`
- `V4.3.1` 跨平台交叉验证：`references/source-cross-validation-2026-03-07-platforms.md`

## 维护约定

- `references/generated/` 仅存放本地临时生成产物，不纳入版本控制
- 每次能力升级后同步更新：`VERSION` 与 `CHANGELOG.md`
