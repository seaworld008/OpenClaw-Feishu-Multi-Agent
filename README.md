# OpenClaw-Feishu-Multi-Agent

面向交付团队的通用 Skill 仓库：用于基于 OpenClaw 搭建飞书多机器人多角色多 Agent 协作体系，支持客户环境快速落地、增量上线、可回滚与可升级。

## 当前版本

- `v1.6.3`（2026-03-11）
- 默认技术路线：官方插件 `@openclaw/feishu`
- 当前公开主线版本：`V5.1 Hardening`
- 当前最新稳定版：`V5.1 Hardening`

## 如果只看一个文件

如果你当前要交付多群、多角色、多机器人协作，且希望以后继续扩群、增减角色、替换提示词都不乱，先看这一个文件：

- [V5.1 Hardening 交付模板 / 产品手册](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md)

它已经覆盖：

- 你将得到什么效果
- `accounts + roleCatalog + teams(profileId + override)` 统一入口
- runtime manifest / hidden main / SQLite / watchdog 的实现原理
- 当前正式双群、三个正式机器人和真实 `appId/appSecret`
- 真实 supervisor / worker 提示词
- 新增一个群、新增一个机器人账号、给现有群增加一个 worker、从现有群移除一个 worker、下线一个群

推荐阅读顺序：

1. 产品手册：[codex-prompt-templates-v51-team-orchestrator.md](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md)
2. 字段手册：[v51-unified-entry-field-guide.md](skills/openclaw-feishu-multi-agent-deploy/references/v51-unified-entry-field-guide.md)
3. 支持边界摘要：[v51-supported-boundaries-summary.md](skills/openclaw-feishu-multi-agent-deploy/references/v51-supported-boundaries-summary.md)
4. 收集清单：[客户首次使用信息清单.md](skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用信息清单.md)
5. 真实案例：[客户首次使用真实案例.md](skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md)
6. 操作型提示词：[客户首次使用-Codex提示词.md](skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用-Codex提示词.md)
7. 新机器上线：[V5.1-新机器快速启动-SOP.md](skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md)
8. 外部群并行恢复复盘：[2026-03-12-external-parallel-recovery-validation.md](docs/plans/2026-03-12-external-parallel-recovery-validation.md)

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

- 统一入口配置：`accounts + roleCatalog + teams`，由 builder 自动派生 `channels.feishu`、`bindings` 和 `v51 runtime manifest`
- Brownfield 增量改造（incremental）与灰度放量（canary）
- 配置生成脚本（从输入 JSON 生成 patch + 验证摘要）
- 前置条件、验收清单、回滚流程、升级回归手册
- `Team Orchestrator`：多个飞书群，每群 `1` 个主管 + `N` 个 worker，可模板化扩展角色、职能与提示词
- `V5.1 Hardening`：把 Team Orchestrator 的流程推进下沉到确定性控制面，`LLM 负责内容，代码负责流程`
- 并行 stage：worker 可并行分析，但群里消息仍由控制面按 `publishOrder` 顺序发布
- 直接给 Codex 使用的完整交付模板、真实双群示例和 `v51 runtime manifest`

当前主线路径统一按下面 4 条理解：

- 正常路径：ingress -> controller -> outbox -> sender -> structured worker response
- ingress transcript 扫描仅用于建单 repair；callback 不再走 hidden main / transcript recovery
- `teamKey` 是唯一内部隔离主键；`group peerId` 只是入口地址
- 插件与 OpenClaw 之间只依赖窄 adapter

## 平台兼容矩阵

| 平台 | 交付建议 | service 管理 | 当前建议 |
|---|---|---|---|
| `Linux` | 正式推荐 | `systemd --user` | 生产首选 |
| `macOS` | 正式推荐 | `launchd` / `LaunchAgent` | 生产可用 |
| `Windows + WSL2` | 正式推荐 | 复用 Linux 路线（建议启用 `systemd`） | Windows 客户首选 |
| `Windows 原生` | 不作为默认生产路径 | 需单独评估 | 不默认承诺 |

核心原则：
1. 平台差异只体现在 service manager、watchdog 模板和运维 SOP。
2. Windows 客户默认按 `WSL2` 交付，不把 Windows 原生 service 当成标准路线。
3. `V5.1 Hardening` 的 `SQLite + hidden main session + runtime manifest` 运行模型，在 Linux / macOS / WSL2 上保持一致。

## 快速使用

1. 进入 Skill 目录

```bash
cd skills/openclaw-feishu-multi-agent-deploy
```

2. 填写输入模板

当前 `V5.1 Hardening` 的统一入口优先使用：

- `references/input-template-v51-fixed-role-multi-group.json`（正式推荐，适合客户交付）
- `references/input-template-v51-team-orchestrator.json`（真实双群生产基线）

3. 生成 patch

```bash
python3 scripts/core_feishu_config_builder.py \
  --input references/input-template-v51-fixed-role-multi-group.json \
  --out references/generated
```

4. 在 OpenClaw 环境执行验证

```bash
openclaw config validate
openclaw gateway restart
openclaw agents list --bindings
```

如果你需要的是产品化交付而不是单次试配，不要只看这 4 步。继续看：

- [V5.1 Hardening 交付模板](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md)
- [客户首次使用真实案例](skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md)
- [客户首次使用-Codex提示词](skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用-Codex提示词.md)

## V5.1 Hardening 快速入口

如果你的目标是“多个飞书群，每个群内都是多个 agent，且每个群都能自定义角色、职能与提示词”，优先按 `V5.1 Hardening` 建模：

当前生产推荐直接采用 `V5.1 Hardening`：
- 不再让 supervisor prompt 自己判断下一步
- 正式主路径固定为 `ingress -> controller -> outbox -> sender -> structured worker response`
- worker 只提交结构化 callback，不再直接决定群里可见消息的发布时间
- worker 现在提交的是 `progressDraft / finalDraft / summary / details / risks / actionItems`，可见消息只允许由 `controller -> outbox -> sender` 发出
- `workflow.stages` 支持 `serial` 和 `parallel` stage group
- `parallel` stage 允许多个 worker 同时分析，但群里仍按 `publishOrder` 顺序发布 `progress/final`
- timer 必须运行 `v51_team_orchestrator_reconcile.py resume-job`
- 不把 `WARMUP` 当成常规运行依赖
- 若主管群 session 对真实用户消息没有直接进入控制面，而是先发生 `read/exec/sessions_spawn` 自由漂移，`resume-job` 必须从 supervisor group transcript 抢占最近未消费的真实用户消息补建单；它不再要求“最后一轮 assistant 必须刚好是 `NO_REPLY`”，并会在建单后清理这条消息之后 supervisor 漂移出来的 subagent session
- 若当前 stage 长时间停在 `wait_worker` 且没有新的结构化 callback，先检查 worker 是否真的提交了 draft callback，再决定是否走 repair；不要再把 worker 的 `NO_REPLY` 当作正常完成信号

1. 输入模板：
- [V5.1 Hardening 输入模板](skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-team-orchestrator.json)
- [V5.1 固定角色多群模板](skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-fixed-role-multi-group.json)
- [统一入口字段手册](skills/openclaw-feishu-multi-agent-deploy/references/v51-unified-entry-field-guide.md)

2. 交付文档：
- [V5.1 Hardening 交付模板](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md)
- [V5.1 新机器快速启动 SOP](skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md)
- [客户首次使用信息清单](skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用信息清单.md)
- [客户首次使用-Codex提示词](skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用-Codex提示词.md)
- [客户首次使用真实案例](skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md)

3. 去敏配置快照：
- [V5.1 Hardening JSONC 参考快照](skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v51-team-orchestrator.example.jsonc)

4. runtime 模板：
- `templates/systemd/v51-team-watchdog.service`
- `templates/systemd/v51-team-watchdog.timer`
- `templates/launchd/v51-team-watchdog.plist`
- `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py`

5. 生成器额外产物：
- `openclaw-feishu-plugin-v51-runtime-<timestamp>.json`
- `openclaw-feishu-plugin-v51-runtime-latest.json`
- `v51_team_orchestrator_deploy.py` 在保留时间戳产物的同时，会刷新 `latest` 别名；若额外传入 `--openclaw-home ~/.openclaw`，会同时完成三件事：写入 active `~/.openclaw/v51-runtime-manifest.json`、渲染 `v51-team-*.service/.timer` 或 launchd plist、以及把每个 team workspace 硬化成 role-specific 契约文件（`AGENTS.md / SOUL.md / USER.md / IDENTITY.md / TOOLS.md / HEARTBEAT.md`），并清掉默认 `BOOTSTRAP.md`
- `~/.openclaw/v51-runtime-manifest.json` 才是现网 reconcile / watchdog / canary 应直接消费的 active manifest

当前正式双群基线：
- 内部团队群：`oc_f785e73d3c00954d4ccd5d49b63ef919`
- 外部团队群：`oc_7121d87961740dbd72bd8e50e48ba5e3`
- 三个正式机器人：`aoteman` / `xiaolongxia` / `yiran_yibao`
- 当前正式 teamKey：`internal_main` / `external_main`

设计原则：
- 每个群都是一个独立 `team unit`
- `One Team = 1 Supervisor + N Workers`
- `roleCatalog` 是 `V5.1` 主线的角色真源，统一维护 `name / role / visibleLabel / description / responsibility / identity / mentionPatterns / systemPrompt`
- `teams[].supervisor` 与 `teams[].workers[]` 主线推荐写法是 `profileId + agentId + override`；旧 inline 写法继续兼容，但不再作为主线规范
- `visibleLabel` 是显示层单一来源；runtime 建单后会把 supervisor / worker 的展示名快照持久化到 `jobs.supervisor_visible_label` 与 `job_participants.visible_label`
- 当前生产推荐标准：`bot 复用，role 固定`
- 同一个 bot 可以跨很多群复用，但它在所有群里都保持同一个角色
- 每个群的角色组合可以不同，只需要在该 `team` 下启用需要的 `workers`
- supervisor 的“决策型终稿”不是为某一组角色写死的，而是按当前 `team` 的 worker 组合动态综合
- 常见可复用组合示例：
  - `运营 + 财务`
  - `法务 + 财务 + 交付`
  - `技术 + 产品 + 运维`
  - 任意 `3` 个 worker 的组合
  - 任意 `4` 个 worker 的组合
- 实践建议：
  - `2~4` 个 worker 是主管终稿最稳定、最易读的范围
  - 超过 `4` 个 worker 依然支持，但建议每个角色只保留“核心判断 + 关键约束”
- `teamKey` 驱动 agentId / workspace / memory / watchdog 命名
- deploy 落地后的 workspace 不是通用聊天空间，而是控制面/worker 的协议工作区；默认 bootstrap 人格文件不能继续留在现网 team workspace 中
- hidden main 是一次性 mailbox；控制面每次成功消费 worker callback 后，都会自动轮转 supervisor hidden main 与该 worker 的 main session，避免旧点评/旧上下文跨 job 残留
- `workflow.stages` 必须把当前 team 的每个 worker 恰好声明一次；主管最终收口前必须等所有已登记 worker 完成
- `parallel` stage 必须显式声明 `stageKey / agents / publishOrder`
- `publishOrder` 必须完整覆盖该 stage 的全部 worker，且顺序唯一
- 每个 agent 都允许单独定制 `name / description / identity / role / responsibility / systemPrompt`
- 不再推荐多个群共享同一套全局 `supervisor_agent / ops_agent / finance_agent`
- `V5.1 Hardening` 采用 `Deterministic Orchestrator`：`watchdog-tick -> v51_team_orchestrator_reconcile.py resume-job -> ingress claim -> TeamController.start_job -> outbox ack -> dispatch_stage -> structured worker response -> ordered publish -> rollup -> close-job`
- worker 的群内可见消息必须使用控制面下发的固定标题合同：`progressTitle=【角色进度｜TG-xxxx】`、`finalTitle=【角色结论｜TG-xxxx】`，不得省略 `jobRef`
- worker 不再直接 `message(progress/final)`；正式协议是提交 `progressDraft / finalDraft`，由 controller/outbox 顺序发布
- `build-dispatch-payload` 现在会显式下发 `scopeLabel / forbiddenRoleLabels / forbiddenSectionKeywords / finalScopeRule`；worker 的 `finalVisibleText` 只能停留在当前角色边界内，不能提前写 sibling 角色章节或主管统一收口
- supervisor 最终统一收口必须是结构化完整方案，至少包含：`任务主题`、各角色结论、`联合风险与红线`、`明日三件事`
- supervisor 最终统一收口必须优先引用各 worker 的完整 `finalVisibleText` 终案正文，并整理成可直接执行的终案方案；禁止把 worker 的完整结论压缩成两三行摘要后收口
- 当前推荐 supervisor 最终统一收口使用“决策型终稿”结构：
  - `最终结论`
  - `决策依据`
  - `最终方案`
  - `执行路线`
  - `风险红线`
  - `明日三件事`
- 这套主管终稿适用于不同角色组合；主管只负责统一拍板，不依赖固定的 `运营 / 财务 / 法务 / 技术` 顺序
- 同一 `jobRef` 的 `【主管最终统一收口｜TG-xxxx】` 只允许出现一次；若 `rollupVisibleSent=true` 但 job 尚未关闭，只允许补 `close-job`，禁止再次发群消息
- `resume-job` 只消费 `inbound_events / stage_callbacks / outbound_messages` 这三类正式控制面状态；不再消费 hidden main / plaintext / worker transcript 文本回调
- worker 完成回调的正式协议是：最后一条 assistant 响应直接输出单个结构化 JSON，对象中提交 `progressDraft / finalDraft / finalVisibleText / summary / details / risks / actionItems`；若附带 `progressMessageId / finalMessageId`，必须是真实 messageId，禁止使用 `pending / placeholder / sent / <pending...>` 等占位值
- 若 gateway 重启后出现历史 `delivery-recovery` 噪音：优先清理 `~/.openclaw/delivery-queue/` 中遗留的旧坏消息，再重启 gateway
- worker 结构化响应若缺少真实 messageId、越权输出跨角色内容、或仍保留 job scoped subagent 行为，控制面只允许拒绝并重派当前 worker，不再从任意自由文本猜测推进状态
- `resume-job` 在当前 stage 还未完成时，必须忽略已消费旧 stage 的 hidden main 包；旧包不能在下一 stage 被重新当成 invalid packet 触发误重派
- 若 waiting worker 的当前 `jobRef` 期间出现 `sessions_spawn` 派生的 subagent session，或 `finalVisibleText` 越权写出其他角色标题/章节、统一收口/总方案章节，`resume-job` 必须拒绝该回调、清理 job scoped subagent/main session 并重派当前 worker
- `resume-job / reconcile-dispatch / reconcile-rollup` 必须按 `teamKey` 持有独占锁；同一 team 不允许同时存在 timer 自动恢复和手工恢复两份控制面实例，否则会放大重复派发风险
- 一句话原则：`LLM 负责内容，代码负责流程`

推荐固定映射：
- `aoteman -> supervisor`
- `xiaolongxia -> ops`
- `yiran_yibao -> finance`

canonical schema 最小示意：

```json
{
  "accounts": [
    {
      "accountId": "aoteman",
      "appId": "cli_a923c749bab6dcba",
      "appSecret": "TWpD207Ri2g1Qqmw4R5YhfkPRhOokCGX"
    },
    {
      "accountId": "xiaolongxia",
      "appId": "cli_a9f1849b67f9dcc2",
      "appSecret": "g7dTIRe6Tz8jYzASSKTT2eBV5LGzrKDr"
    }
  ],
  "roleCatalog": {
    "supervisor_default": {
      "kind": "supervisor",
      "accountId": "aoteman",
      "visibleLabel": "主管",
      "systemPrompt": "..."
    },
    "ops_default": {
      "kind": "worker",
      "accountId": "xiaolongxia",
      "visibleLabel": "运营",
      "systemPrompt": "..."
    }
  },
  "teams": [
    {
      "teamKey": "internal_main",
      "supervisor": {
        "profileId": "supervisor_default",
        "agentId": "supervisor_internal_main"
      },
      "workers": [
        {
          "profileId": "ops_default",
          "agentId": "ops_internal_main"
        }
      ],
      "workflow": {
        "stages": [
          {
            "stageKey": "analysis",
            "mode": "serial",
            "agents": [
              { "agentId": "ops_internal_main" }
            ],
            "publishOrder": ["ops_internal_main"]
          }
        ]
      }
    }
  ]
}
```

并行 stage 示例：

```json
{
  "workflow": {
    "stages": [
      {
        "stageKey": "analysis",
        "mode": "parallel",
        "agents": [
          { "agentId": "ops_internal_main" },
          { "agentId": "finance_internal_main" },
          { "agentId": "legal_internal_main" }
        ],
        "publishOrder": [
          "ops_internal_main",
          "finance_internal_main",
          "legal_internal_main"
        ]
      }
    ]
  }
}
```

语义：
- worker 可以并行分析、并行回调
- 群里只按 `publishOrder` 依次放出 `【角色进度】` / `【角色结论】`
- 所有 worker 发布完成后，主管才进入最终统一收口

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
- systemd：`v51-team-<teamKey>.service` / `v51-team-<teamKey>.timer`
- launchd：`bot.molt.v51-team-<teamKey>`

当前双群对应 hidden main：
- `agent:supervisor_internal_main:main`
- `agent:supervisor_external_main:main`

Codex 交付入口：
- [V5.1 Hardening 交付模板](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md)
- 这份文档已经写入当前 2 个正式群、3 个正式机器人、可直接复制给 Codex 的长版提示词和运行命令
- 其中 `V5.1 Hardening` 的正式主路径必须明确出现：`ingress -> controller -> outbox -> sender -> structured worker response`，以及 `v51_team_orchestrator_reconcile.py` 的 `resume-job / reconcile-dispatch / reconcile-rollup`

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

### 三、按当前正式双群写一版可直接落地的 team 编排

当前正式主线不是“3 个群各配 1 个 agent”，而是“2 个团队群，每个群 1 个 supervisor + N 个 worker，共复用 3 个正式机器人账号”。

你当前正式双群基线：

- `internal_main -> oc_f785e73d3c00954d4ccd5d49b63ef919`
- `external_main -> oc_7121d87961740dbd72bd8e50e48ba5e3`
- `aoteman -> supervisor`
- `xiaolongxia -> ops`
- `yiran_yibao -> finance`

统一入口最小结构应写成：

```text
accounts[]
roleCatalog[]
teams[]
```

其中当前正式双群的最小建模是：

```text
- internal_main
  - supervisor: supervisor_internal_main（profileId=supervisor_internal_default, accountId=aoteman）
  - workers:
    - ops_internal_main（profileId=ops_default, accountId=xiaolongxia）
    - finance_internal_main（profileId=finance_default, accountId=yiran_yibao）
- external_main
  - supervisor: supervisor_external_main（profileId=supervisor_external_default, accountId=aoteman）
  - workers:
    - ops_external_main（profileId=ops_default, accountId=xiaolongxia）
    - finance_external_main（profileId=finance_default, accountId=yiran_yibao）
```

### 四、统一入口配置原则（不要手写 routes）
- 主线输入只维护 `accounts + roleCatalog + teams`。
- `channels.feishu`、`bindings`、必要的 `agents.list` 和 `v51 runtime manifest` 都由 builder 派生。
- `bindings` 是 builder 派生结果，不是主线手工输入；你要人工核对排序和命中结果，但不要再把 `routes` 当成统一入口。
- 群级策略默认写在 `teams[].group`：如 `peerId`、`entryAccountId`、`requireMention`。
- 角色默认定义写在 `roleCatalog`；同一角色如果只是某个群上下文不同，优先在对应 `team` 里做 override，不要复制整块 prompt。
- 角色级运行时配置现在也可以统一写在 `roleCatalog.*.runtime`，并在 `teams[].supervisor/teams[].workers[].overrides.runtime` 做 team 级覆盖；builder 会把它们下沉到生成后的 `agents.list`。
- 当前正式支持写入 `agents.list` 的 runtime override 只包括：`model`、`sandbox`。`workspace / agentDir` 仍通过 agent 显式字段覆盖；`maxConcurrent / subagents` 继续保留在顶层 `agents.defaults`，不要下沉到单个 agent。
- 同一个 bot 可以跨多个群复用，但它在所有群里都保持同一个角色；不要让同一个 `accountId` 在一个群当 supervisor、另一个群又当 finance。

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
| Agent ID（`agentId`） | `supervisor_internal_main` | `openclaw agents list` | 是（`binding.agentId`） |

### 七、一步一步配置流程（照着做可落地）

1. 飞书后台准备
- 为正式 supervisor / worker 准备对应应用和机器人账号。
- 开启机器人能力。
- 在权限管理里完成“基础权限 + 按需权限（文档/多维表格）”。
- 订阅事件至少包含：`im.message.receive_v1`。

2. OpenClaw 账号配置
- 在统一入口 `accounts[]` 维护实际 `accountId` 及凭据。
- `channels.feishu.accounts` 由 builder 写入 patch，不要手抄多份。
- `defaultAccount` 保持指向当前默认入口账号，一般为 supervisor 对应的 `accountId`。

3. 收集团队群与 agent
- 在每个目标群分别发测试消息。
- 执行 `openclaw logs --follow`，记录每个团队群的真实 `peerId`。
- 执行 `openclaw agents list`，确认 supervisor / worker 对应的 `agentId` 已存在。

4. 填统一入口输入
- 在 `roleCatalog` 里定义 supervisor / worker 默认资料。
- 在 `teams[]` 里声明每个群的 `teamKey`、`group`、`supervisor`、`workers`、`workflow.stages`。
- 若某个角色在所有群都使用相同模型或 sandbox 策略，优先写在 `roleCatalog.*.runtime`。
- 若只有某个 team 的某个 agent 需要特殊模型或 sandbox，再写在 `teams[].supervisor.overrides.runtime` 或 `teams[].workers[].overrides.runtime`。
- 若只是复用现有角色，不要重复写新的整块 prompt。

5. 生成并核对 patch
- 先备份配置。
- 优先运行 `v51_team_orchestrator_deploy.py` 生成最小 patch、`latest` 别名和 active `~/.openclaw/v51-runtime-manifest.json`。
- Linux / WSL2 部署时，直接让它同时渲染 `~/.config/systemd/user/v51-team-*.service/.timer`。
- 当前控制面在成功消费 worker callback 后，会自动轮转 supervisor hidden main 与已完成 worker 的 main session；若你在运行机上看到这些 session 被清掉，这是预期行为，不是异常。
- 人工核对 `bindings` 排序：精确规则优先（peer+account）→ account 精确 → 兜底。

6. 变更上线
- 运行 `openclaw config validate`。
- 重启 `openclaw gateway`。
- 执行 `openclaw agents list --bindings` 检查结果。
- 先 canary 群验证，再全量。

### 八、统一入口扩展动作（新增 / 删减都从这里改）

- 新增一个群：
  - 新增一个 `teams[]` 条目。
  - 若角色复用现有 profile，只填新的 `teamKey / group / agentId / workflow.stages`。
- 新增一个机器人账号：
  - 新增一条 `accounts[]`。
  - 让对应 `roleCatalog.<profileId>.accountId` 指向它。
- 给现有群增加一个 worker：
  - 同步修改该 `team` 的 `workers[]` 和 `workflow.stages[]`。
- 从现有群移除一个 worker：
  - 同步删除该 `team` 的 `workers[]` 和 `workflow.stages[]`。
  - 若该 profile 不再被任何 team 使用，再决定是否清理 `roleCatalog`。
- 下线一个群：
  - 删除对应 `teams[]` 条目。
  - 同时停掉该 `teamKey` 对应的 watchdog / launchd / SQLite / workspace。

## 使用 Codex 的实战案例（安装到上线）

下面这套话术面向当前正式主线 `V5.1 Hardening`。

注意：
- 这里不是“3 个群各配 1 个 agent”的旧 `routes` 口径。
- 这里是“2 个团队群，每个群 1 个 supervisor + N 个 worker，共复用 3 个正式机器人账号”的 `Team Orchestrator` 口径。
- 前面的 `routes` 示例只适合解释基础 binding 原理；真正交付 `V5.1` 时，统一入口必须按 `accounts + roleCatalog + teams(profileId + override)` 组织。

### 1) 先安装 skill

```text
请使用 $skill-installer，
从 GitHub 安装这个 skill 到我的 Codex：
- repo: `seaworld008/OpenClaw-Feishu-Multi-Agent`
- path: `skills/openclaw-feishu-multi-agent-deploy`
安装成功后提醒我重启 Codex。
```

### 2) 重启后直接发这个标准任务（V5.1 群内多 Agent 可扩展版）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，完成本次飞书群内多 Agent Team Orchestrator 配置。

交付边界：
- 现网为 brownfield，必须 incremental（仅做必要最小改动）。
- 配置目标 channel = feishu（官方插件）。
- 不改 `bindings` 与 `channels.feishu` 无关字段。
- 当前主线必须按 V5.1 Hardening 处理，不要退回旧 `accountMappings + routes` 模型。

输入信息（请严格按下面结构读取/补齐，后续可扩展）：
- accounts:
  - accountId: "aoteman"
    appId: "cli_a923c749bab6dcba"
    appSecret: "TWpD207Ri2g1Qqmw4R5YhfkPRhOokCGX"
    encryptKey: "..."
    verificationToken: "..."
  - accountId: "xiaolongxia"
    appId: "cli_a9f1849b67f9dcc2"
    appSecret: "g7dTIRe6Tz8jYzASSKTT2eBV5LGzrKDr"
    encryptKey: "..."
    verificationToken: "..."
  - accountId: "yiran_yibao"
    appId: "cli_a923c71498b8dcc9"
    appSecret: "swscrlPKYCwAehOyyoLrlesLTsuYY6nl"
    encryptKey: "..."
    verificationToken: "..."
- roleCatalog:
  - supervisor_internal_default:
      kind: "supervisor"
      accountId: "aoteman"
      visibleLabel: "主管"
      role: "主管总控"
      profileScope: "internal_main"
      systemPrompt: "沿用当前正式内部团队主管 prompt；若客户有团队上下文差异，再按 team override 覆盖。"
  - supervisor_external_default:
      kind: "supervisor"
      accountId: "aoteman"
      visibleLabel: "主管"
      role: "主管总控"
      profileScope: "external_main"
      systemPrompt: "沿用当前正式外部团队主管 prompt；若客户有团队上下文差异，再按 team override 覆盖。"
  - ops_default:
      kind: "worker"
      accountId: "xiaolongxia"
      visibleLabel: "运营"
      role: "运营专家"
      systemPrompt: "沿用当前正式运营专家 prompt。"
  - finance_default:
      kind: "worker"
      accountId: "yiran_yibao"
      visibleLabel: "财务"
      role: "财务专家"
      systemPrompt: "沿用当前正式财务专家 prompt。"
- teams:
  - teamKey: "internal_main"
    displayName: "内部生产团队群"
    group:
      peerId: "oc_f785e73d3c00954d4ccd5d49b63ef919"
      entryAccountId: "aoteman"
      requireMention: true
    supervisor:
      profileId: "supervisor_internal_default"
      agentId: "supervisor_internal_main"
    workers:
      - profileId: "ops_default"
        agentId: "ops_internal_main"
      - profileId: "finance_default"
        agentId: "finance_internal_main"
    workflow:
      mode: "serial"
      stages:
        - agentId: "ops_internal_main"
        - agentId: "finance_internal_main"
  - teamKey: "external_main"
    displayName: "外部生产团队群"
    group:
      peerId: "oc_7121d87961740dbd72bd8e50e48ba5e3"
      entryAccountId: "aoteman"
      requireMention: true
    supervisor:
      profileId: "supervisor_external_default"
      agentId: "supervisor_external_main"
    workers:
      - profileId: "ops_default"
        agentId: "ops_external_main"
      - profileId: "finance_default"
        agentId: "finance_external_main"
    workflow:
      mode: "serial"
      stages:
        - agentId: "ops_external_main"
        - agentId: "finance_external_main"

可选扩展示例：
- 如果新增一个业务群，只需新增一个 `teams[]` 条目；若主管/worker 只是复用现有角色，不必重复整块 prompt。
- 如果新增一个机器人账号，只需新增一条 `accounts[]`，并让对应 `roleCatalog.<profileId>.accountId` 指向它。
- 如果给现有群增加一个 worker，只需同步修改该 `team` 的 `workers[]` 和 `workflow.stages[]`。
- 如果从现有群移除一个 worker，只需同步删除该 `team` 的 `workers[]` 和 `workflow.stages[]`；若 profile 不再被任何 team 使用，再判断是否清理 `roleCatalog`。
- 如果下线一个群，只需删除对应 `teams[]` 条目，并输出需要停掉的 watchdog / state / workspace 清单。

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
6) 输出 `v51 runtime manifest`。
7) 输出回滚命令与验收证据模板。
8) 若发现输入信息仍是旧 `accountMappings + routes` 结构，先显式指出这不是当前主线，再帮我转换成 `accounts + roleCatalog + teams` 后继续。
```

3. 你只需要把占位值换成真实值
- `accounts[]` 里的 `appId` / `appSecret` / `encryptKey` / `verificationToken`
- `teams[].group.peerId`
- `teams[].supervisor.agentId` 与 `teams[].workers[].agentId`
- `roleCatalog.*.systemPrompt` 中客户自己的行业上下文、话术边界和交付要求
- 是否开启 `tools.agentToAgent`

### 占位值替换对照（重点）

当前正式双群基线不是“3 个群各配 1 个 agent”，而是下面这组：

- `internal_main -> oc_f785e73d3c00954d4ccd5d49b63ef919`
- `external_main -> oc_7121d87961740dbd72bd8e50e48ba5e3`
- `aoteman -> supervisor`
- `xiaolongxia -> ops`
- `yiran_yibao -> finance`

其中每一段都需要替换为客户自己的真实值。按下面对照填：

| 示例占位 | 你要替换成什么 | 来源位置 | 常见错误 |
|---|---|---|---|
| `internal_main` / `external_main` | 客户自己的 `teamKey` | 你定义的团队命名规则 | 用群名称临时替代，后续 workspace/watchdog 命名混乱 |
| `oc_f785...` / `oc_7121...` | 飞书群真实 `chat_id`（通常以 `oc_` 开头） | 飞书事件 `im.message.receive_v1` 的 `chat_id`；或 OpenClaw 日志中收到消息时的会话 ID | 用了群名称而不是 `chat_id`；把多个群写成同一个 ID |
| `supervisor_internal_main` / `ops_internal_main` / `finance_internal_main` | OpenClaw 中真实存在或准备新建的 `agentId` | `openclaw agents list` | 把 role 名称当 agentId；内部群和外部群复用同一个 agentId 导致串线 |
| `aoteman` / `xiaolongxia` / `yiran_yibao` | `channels.feishu.accounts` 里的账号键名（`accountId`） | 你的 `openclaw.json` 中 `channels.feishu.accounts.<key>` | `roleCatalog.accountId`、`group.entryAccountId` 与 accounts 键名不一致 |
| `supervisor_internal_default` / `ops_default` / `finance_default` | 当前角色目录里的 profileId | 输入文件 `roleCatalog` | 在每个 team 重复写一整块角色定义，后面扩群越来越乱 |

### 一份可直接照抄的“替换后”示例

假设你的真实值是当前正式双群基线：
- 内部团队群：`internal_main -> oc_f785e73d3c00954d4ccd5d49b63ef919`
- 外部团队群：`external_main -> oc_7121d87961740dbd72bd8e50e48ba5e3`
- supervisor 机器人：`aoteman`
- ops 机器人：`xiaolongxia`
- finance 机器人：`yiran_yibao`

那么 `teams[]` 至少应写成：

```text
- internal_main:
  - supervisor: supervisor_internal_main（profileId=supervisor_internal_default, accountId=aoteman）
  - workers:
    - ops_internal_main（profileId=ops_default, accountId=xiaolongxia）
    - finance_internal_main（profileId=finance_default, accountId=yiran_yibao）
- external_main:
  - supervisor: supervisor_external_main（profileId=supervisor_external_default, accountId=aoteman）
  - workers:
    - ops_external_main（profileId=ops_default, accountId=xiaolongxia）
    - finance_external_main（profileId=finance_default, accountId=yiran_yibao）
```

### 上线前 6 条强校验（避免配错）

1. `teamKey` 唯一：一个群只对应一个独立 team unit。
2. `workflow.stages` 完整：每个 team 当前启用的 worker 必须在 `workflow.stages` 中恰好声明一次。
3. `parallel` stage 合法：并行 stage 必须配置 `stageKey + agents + publishOrder`，且 `publishOrder` 覆盖全部 worker 且顺序唯一。
4. `agentId` 存在：`openclaw agents list` 能查到 supervisor / worker 对应的 agent。
5. `accountId` 对齐：`roleCatalog.accountId`、`teams[].group.entryAccountId`、`bindings.match.accountId` 必须都等于 `channels.feishu.accounts` 的键名。
6. 先验证再放量：先 canary 群验证通过，再全量。

4. 交付验收建议
- 先在 canary 群验证，再全量放量
- 每条 binding 至少做一次实测（群+私聊）
- 留存回滚命令和验证证据（日志/截图/命令输出）

## 主线版本与阅读顺序

仓库公开主线已经收敛为 1 条：

| 主线版本 | 定位 | 适合场景 | 核心入口 |
|---|---|---|---|
| `V5.1 Hardening` | 多群模板化主线 | 多个群并行、每群独立 team unit、群内 worker 可并行分析且顺序发布 | [codex-prompt-templates-v51-team-orchestrator.md](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md) |

选择建议：
1. 当前生产交付默认直接上 `V5.1 Hardening`。
2. 如果客户后面还会持续扩群、增减机器人、替换角色提示词，仍然只用 `V5.1 Hardening`。

推荐阅读顺序：
1. [prerequisites-checklist.md](skills/openclaw-feishu-multi-agent-deploy/references/prerequisites-checklist.md)
2. [deployment-inputs.example.yaml](skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml)
3. [codex-prompt-templates-v51-team-orchestrator.md](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md)
4. [verification-checklist.md](skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md)
5. [rollout-and-upgrade-playbook.md](skills/openclaw-feishu-multi-agent-deploy/references/rollout-and-upgrade-playbook.md)

历史交叉验证归档（非主线规范）：
- OpenClaw 官方文档与 Release 交叉验证：[source-cross-validation-2026-03-04.md](skills/openclaw-feishu-multi-agent-deploy/references/source-cross-validation-2026-03-04.md)
- OpenClaw / 飞书平台能力复核：[source-cross-validation-2026-03-05.md](skills/openclaw-feishu-multi-agent-deploy/references/source-cross-validation-2026-03-05.md)

## 维护约定

- `references/generated/` 仅存放本地临时生成产物，不纳入版本控制
- 每次能力升级后同步更新：`VERSION` 与 `CHANGELOG.md`
