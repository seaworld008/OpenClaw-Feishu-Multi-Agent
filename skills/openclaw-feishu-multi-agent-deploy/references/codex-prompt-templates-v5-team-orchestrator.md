# V5 Team Orchestrator / V5.1 Hardening

当前生产推荐使用 `V5.1 Hardening`。

核心原则：
- `Deterministic Orchestrator`
- `LLM 负责内容，代码负责流程`
- 主管必须通过 `start-job-with-workflow`、`get-next-action`、`build-rollup-context` 驱动流程，而不是在 prompt 中自行猜测下一步

`V5` 不是把同一套全局 agent 复用到所有飞书群，而是把每个群封装成一个独立的 team unit。

核心约束：

- `One Team = 1 Supervisor + N Workers`
- `teams` 是唯一推荐的配置入口
- 当前生产推荐标准：`bot 复用，role 固定`
- 同一个 bot 可以跨很多群复用，但它在所有群里都保持同一个角色
- 每个群的角色组合可以不同，只需要在该 `team` 下启用需要的 `workers`
- `workflow.stages` 决定当前团队的调度顺序
- hidden main 必须按 supervisor 参数化，例如：`agent:supervisor_internal_main:main`
- 默认生产流程必须严格串行：主管接单 -> 运营进度 -> 运营结论 -> 财务进度 -> 财务结论 -> 主管最终收口

推荐固定映射：

- `aoteman -> supervisor`
- `xiaolongxia -> ops`
- `yiran_yibao -> finance`

推荐直接从这个模板起步：

- `references/input-template-v5-fixed-role-multi-group.json`
- 该模板已经示例化 `full_team_demo / ops_only_demo / finance_only_demo`

## 当前正式团队

当前仓库里需要先固化为 `V5` 正式示例的是这 2 个群：

- 内部团队群：`oc_f785e73d3c00954d4ccd5d49b63ef919`
- 外部团队群：`oc_7121d87961740dbd72bd8e50e48ba5e3`

三个机器人账号固定是：

- `aoteman` / `奥特曼`
- `xiaolongxia` / `小龙虾找妈妈`
- `yiran_yibao` / `易燃易爆`

真实飞书应用信息：

- `aoteman`
  - `appId`: `cli_a923c749bab6dcba`
  - `appSecret`: `TWpD207Ri2g1Qqmw4R5YhfkPRhOokCGX`
- `xiaolongxia`
  - `appId`: `cli_a9f1849b67f9dcc2`
  - `appSecret`: `g7dTIRe6Tz8jYzASSKTT2eBV5LGzrKDr`
- `yiran_yibao`
  - `appId`: `cli_a923c71498b8dcc9`
  - `appSecret`: `swscrlPKYCwAehOyyoLrlesLTsuYY6nl`

## 为什么要升级到 V5

`V4.3.1` 已经证明单群生产可行，但它默认只有一套：

- `supervisor_agent`
- `ops_agent`
- `finance_agent`
- `agent:supervisor_agent:main`

一旦扩展到多个群，就会遇到你已经在线上看到的问题：

- stale group session 污染多个群
- hidden main 共用导致延迟和串线风险
- memory / workspace / watchdog 边界不够硬
- 客户要第 2 个、第 10 个群时，配置复制成本高且容易漏字段

`V5` 的目标不是推翻 `V4.3.1`，而是把 `V4.3.1` 的生产协议参数化成可复制的 team unit：

- 每个群独立 `supervisor`
- 每个群独立 `workers`
- 每个群独立 `workspace / session / db / watchdog / hidden main`
- 通过 `teams[]` 快速复制出第 2 个、第 10 个团队
- `workflow.stages` 必须把当前 team 的每个 worker 恰好声明一次；主管只能在全部 worker 完成后收口
- 每个 agent 都可以单独定制 `name / description / identity / role / responsibility / systemPrompt`

## 推荐输入模型

当前正式双群输入建议直接采用下面这套：

```json
{
  "mode": "plugin",
  "defaultAccount": "aoteman",
  "accounts": [
    { "accountId": "aoteman", "appId": "cli_a923c749bab6dcba", "appSecret": "TWpD207Ri2g1Qqmw4R5YhfkPRhOokCGX" },
    { "accountId": "xiaolongxia", "appId": "cli_a9f1849b67f9dcc2", "appSecret": "g7dTIRe6Tz8jYzASSKTT2eBV5LGzrKDr" },
    { "accountId": "yiran_yibao", "appId": "cli_a923c71498b8dcc9", "appSecret": "swscrlPKYCwAehOyyoLrlesLTsuYY6nl" }
  ],
  "teams": [
    {
      "teamKey": "internal_main",
      "group": {
        "peerId": "oc_f785e73d3c00954d4ccd5d49b63ef919",
        "entryAccountId": "aoteman",
        "requireMention": true
      },
      "supervisor": {
        "agentId": "supervisor_internal_main",
        "roleKey": "supervisor",
        "name": "奥特曼",
        "description": "内部团队主管，负责任务受理、拆解、串行调度与统一收口。",
        "identity": {
          "name": "奥特曼总控",
          "theme": "steady orchestrator",
          "emoji": "🧭"
        },
        "systemPrompt": "..."
      },
      "workers": [
        {
          "agentId": "ops_internal_main",
          "roleKey": "ops",
          "accountId": "xiaolongxia",
          "name": "小龙虾找妈妈",
          "description": "内部团队运营专家，负责活动打法、节奏设计和执行推进。",
          "identity": {
            "theme": "growth operator",
            "emoji": "📈"
          },
          "role": "运营专家",
          "responsibility": "活动打法、节奏、执行动作",
          "visibility": "visible",
          "systemPrompt": "..."
        },
        {
          "agentId": "finance_internal_main",
          "roleKey": "finance",
          "accountId": "yiran_yibao",
          "name": "易燃易爆",
          "description": "内部团队财务专家，负责预算、毛利、ROI 与风险控制。",
          "identity": {
            "theme": "financial controller",
            "emoji": "💹"
          },
          "role": "财务专家",
          "responsibility": "预算、毛利、ROI 与风险",
          "visibility": "visible",
          "systemPrompt": "..."
        }
      ],
      "workflow": {
        "mode": "serial",
        "stages": [
          { "agentId": "ops_internal_main" },
          { "agentId": "finance_internal_main" }
        ]
      }
    },
    {
      "teamKey": "external_main",
      "group": {
        "peerId": "oc_7121d87961740dbd72bd8e50e48ba5e3",
        "entryAccountId": "aoteman",
        "requireMention": true
      },
      "supervisor": {
        "agentId": "supervisor_external_main",
        "roleKey": "supervisor",
        "name": "奥特曼",
        "description": "外部团队主管，负责任务受理、拆解、串行调度与统一收口。",
        "identity": {
          "name": "奥特曼总控",
          "theme": "client-facing orchestrator",
          "emoji": "🧭"
        },
        "systemPrompt": "..."
      },
      "workers": [
        {
          "agentId": "ops_external_main",
          "roleKey": "ops",
          "accountId": "xiaolongxia",
          "name": "小龙虾找妈妈",
          "description": "外部团队运营专家，负责活动打法、节奏设计和执行推进。",
          "identity": {
            "theme": "growth operator",
            "emoji": "📈"
          },
          "role": "运营专家",
          "responsibility": "活动打法、节奏、执行动作",
          "visibility": "visible",
          "systemPrompt": "..."
        },
        {
          "agentId": "finance_external_main",
          "roleKey": "finance",
          "accountId": "yiran_yibao",
          "name": "易燃易爆",
          "description": "外部团队财务专家，负责预算、毛利、ROI 与风险控制。",
          "identity": {
            "theme": "financial controller",
            "emoji": "💹"
          },
          "role": "财务专家",
          "responsibility": "预算、毛利、ROI 与风险",
          "visibility": "visible",
          "systemPrompt": "..."
        }
      ],
      "workflow": {
        "mode": "serial",
        "stages": [
          { "agentId": "ops_external_main" },
          { "agentId": "finance_external_main" }
        ]
      }
    }
  ]
}
```

## V5.1 Hardening 控制面

主管控制面固定使用下面 7 个 registry 命令，watchdog 侧固定使用 `v51_team_orchestrator_reconcile.py`：

```text
start-job-with-workflow
build-visible-ack
get-next-action
build-dispatch-payload
build-rollup-context
build-rollup-visible-message
record-visible-message
ready-to-rollup
resume-job
reconcile-dispatch
reconcile-rollup
```

推荐 supervisor 顺序：

```text
timer/watchdog -> v51_team_orchestrator_reconcile.py resume-job
-> 用户任务 -> start-job-with-workflow -> build-visible-ack -> message -> record-visible-message
-> get-next-action -> build-dispatch-payload -> dispatch 当前 worker
-> worker COMPLETE_PACKET -> get-next-action
-> 若 type=dispatch 则继续派单；若 type=rollup 则 build-rollup-context -> build-rollup-visible-message -> message -> record-visible-message -> close-job
```

## 生成产物

`V5` 生成器现在必须同时输出两类文件：

1. OpenClaw patch  
作用：真正写入 `openclaw.json` 的 `channels / bindings / agents / tools / session / messages`

2. `v5 runtime manifest`  
作用：把 `description / identity / workflow / responsibility / visibility / hidden main / db / watchdog / session keys` 全部显式化，供 Codex 和运维脚本落地

`v5 runtime manifest` 至少应包含：

- `teamKey`
- `displayName`
- `group.peerId`
- `supervisor.description`
- `supervisor.identity`
- `supervisor.hiddenMainSessionKey`
- `workers[].description`
- `workers[].identity`
- `workers[].groupSessionKey`
- `workflow.stages`
- `runtime.dbPath`
- `runtime.watchdog.systemdServiceName`
- `runtime.watchdog.systemdTimerName`
- `runtime.watchdog.launchdLabel`

## 命名规范

推荐按 `teamKey` 派生：

```text
supervisor_internal_main
ops_internal_main
finance_internal_main
supervisor_external_main
ops_external_main
finance_external_main
```

对应 hidden main：

```text
agent:supervisor_internal_main:main
agent:supervisor_external_main:main
```

对应 runtime：

```text
db: ~/.openclaw/teams/<teamKey>/state/team_jobs.db
systemd service: v5-team-<teamKey>.service
systemd timer: v5-team-<teamKey>.timer
launchd label: bot.molt.v5-team-<teamKey>
```

## Team Runtime 命令

team runtime 应统一走 `v51_team_orchestrator_runtime.py`：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py \
  --db ~/.openclaw/teams/internal_main/state/team_jobs.db \
  init-db
```

会话卫生建议按 team 执行，而不是继续清共享全局 main：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_hygiene.py \
  --home ~/.openclaw \
  --group-peer-id oc_f785e73d3c00954d4ccd5d49b63ef919 \
  --team-key internal_main \
  --supervisor-agent supervisor_internal_main \
  --worker-agents ops_internal_main,finance_internal_main \
  --include-workers \
  --delete-transcripts
```

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_hygiene.py \
  --home ~/.openclaw \
  --group-peer-id oc_7121d87961740dbd72bd8e50e48ba5e3 \
  --team-key external_main \
  --supervisor-agent supervisor_external_main \
  --worker-agents ops_external_main,finance_external_main \
  --include-workers \
  --delete-transcripts
```

canary 也应按 team 参数化：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_canary.py \
  --db ~/.openclaw/teams/internal_main/state/team_jobs.db \
  --job-ref TG-V5-001 \
  --session-root ~/.openclaw/agents \
  --team-key internal_main \
  --supervisor-agent supervisor_internal_main \
  --worker-agents ops_internal_main,finance_internal_main \
  --require-visible-messages \
  --require-supervisor-target-chat \
  --success-token V5_TEAM_CANARY_OK
```

交付侧统一走 `v51_team_orchestrator_deploy.py` 生成 patch + summary + runtime manifest：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_deploy.py \
  --input skills/openclaw-feishu-multi-agent-deploy/references/input-template-v5-team-orchestrator.json \
  --out skills/openclaw-feishu-multi-agent-deploy/references/generated
```

watchdog 模板固定使用：

- `templates/systemd/v5-team-watchdog.service`
- `templates/systemd/v5-team-watchdog.timer`
- `templates/launchd/v5-team-watchdog.plist`

## 当前最新生产 systemPrompt（V5 版）

下面这些不是概念性摘要，而是当前推荐直接落地的 `V5` 长版规则。

### supervisor 群级 systemPrompt

```text
你是 team supervisor，运行 V5 Team Orchestrator / V5.1 Hardening。

你所在 team 的约束：
- 你只服务当前 team 的 groupPeerId。
- 你只允许调度当前 team 的 worker agentIds。
- hidden main 固定为当前 supervisor 自己的 main session。
- 群里可见消息只允许两类：主管接单、主管最终统一收口。
- 中间状态推进都走隐藏控制会话，内部协议回合最后只允许输出 NO_REPLY。

强制流程：
1. begin-turn
2. 若无 active job：start-job；若已有 active job：append-note 或入队
3. 用 `build-visible-ack` 生成接单 payload，再用 `message` 往当前 team 群发【主管已接单｜<jobRef>】...
4. 接单消息成功后，必须执行 `record-visible-message(kind=ack)`
5. 建单必须使用 `start-job-with-workflow`，不能再用 prompt 自己推断当前阶段。
6. 每次派单前必须先调用 `build-dispatch-payload`，禁止 supervisor 手写弱化版 `TASK_DISPATCH|...`
6.1 控制面直派 worker 前必须重置当前 `agent:<worker>:main`，避免旧 transcript 把新任务拉回旧协议
7. 每次派单或收到 COMPLETE_PACKET 后，必须调用 `get-next-action`：
   - 若返回 `dispatch`，只允许派发指定 `agentId`
   - 若返回 `wait_worker`，本轮只允许 `NO_REPLY`
   - 若返回 `rollup`，必须先调 `build-rollup-context`
8. 只有 `get-next-action` 或 `ready-to-rollup` 明确返回 `rollup` 时，才允许最终收口
9. 最终收口必须先调 `build-rollup-visible-message`，再用 `message` 发群里，并执行 `record-visible-message(kind=rollup)`
10. close-job done

严禁：
- 同时双发多个 worker
- 复用其他 team 的 worker
- 把 COMPLETE_PACKET、ACK_READY、REPLY_SKIP、WORKFLOW_INCOMPLETE 暴露到群里
- 在群里发“已安排/处理中”这种中间播报
- 不带真实 toolCall 就先输出解释性文本
- 用 prompt 自己决定下一步而跳过 `get-next-action`
- 在主管群里把接单/收口直接写成普通 assistant 文本，而不走 `message + record-visible-message`
- supervisor group session 对真实用户消息裸 `NO_REPLY` 后仍继续复用旧会话

若主管群 session 对真实用户消息直接裸返回 `NO_REPLY`：
- 先执行 `v51_team_orchestrator_hygiene.py` 清理当前 team 的 supervisor group/main 与 worker group/main 会话
- 若仍然没建单，执行 `v51_team_orchestrator_reconcile.py --team-key <teamKey> resume-job`，让控制面从最新 transcript 补建单、补接单和补派发
- 若 hidden main transcript 已经有 `COMPLETE_PACKET` 但 DB 没推进，也执行 `resume-job`；当前最高标准实现会优先消费最近有效包，跳过 `pending / placeholder / sent / <pending...>` 这类占位包，并在只剩无效包时重派当前 worker
- 再重新 warm-up worker 或直接复测正式任务
- 不要要求用户连续重复发送同一条任务来“碰碰运气”
```

### ops / finance worker 群级 systemPrompt

```text
你是 team worker，运行 V5 Team Orchestrator。

收到 TASK_DISPATCH 后，必须严格按顺序执行：
1. 从 TASK_DISPATCH 读取显式 `channel/accountId/target`
2. 用这三个字段调用 message 发进度
3. 从 toolResult 读取真实 progressMessageId
4. 用同一组 `channel/accountId/target` 调用 message 发完整结论
5. 从 toolResult 读取真实 finalMessageId
6. sessions_send `COMPLETE_PACKET|status=completed|...` 到 callbackSessionKey
7. 最后只输出 NO_REPLY

若用户直接 @你 且消息包含 WARMUP、就绪、ready、状态检查：
- 只回复 READY_FOR_TEAM_GROUP|agentId=<当前agentId>

严禁：
- ACK
- 占位文本
- 伪造 messageId，或使用 `pending / sent / <pending...> / *_placeholder`
- 使用 [[reply_to_current]]
- 使用别的 team 的 callbackSessionKey
```

## Codex 真实交付模板

以下模板用于让 Codex 直接按当前双群 `V5` 生产模式完成交付。

```text
请使用 openclaw-feishu-multi-agent-deploy skill，按 V5 Team Orchestrator 生产版完成交付。

目标：
- 在同一套 OpenClaw 中同时支持 2 个飞书群：
  - 内部团队群：oc_f785e73d3c00954d4ccd5d49b63ef919
  - 外部团队群：oc_7121d87961740dbd72bd8e50e48ba5e3
- 每个群都是独立 team：
  - 1 个主管：奥特曼 / aoteman
  - 1 个运营：小龙虾找妈妈 / xiaolongxia
  - 1 个财务：易燃易爆 / yiran_yibao
- 两个群必须彻底独立：group session、hidden main、workspace、SQLite、watchdog、memory 都不能互相影响
- 默认执行顺序固定为：
  1. 用户发任务
  2. 主管接单并拆解
  3. 运营发进度和结论
  4. 财务发进度和结论
  5. 主管最终统一收口
- 任何群里都不允许泄漏 ACK_READY / REPLY_SKIP / COMPLETE_PACKET / WORKFLOW_INCOMPLETE

输入：
- accountMappings:
  - { accountId: "aoteman", appId: "cli_a923c749bab6dcba", appSecret: "TWpD207Ri2g1Qqmw4R5YhfkPRhOokCGX", encryptKey: "", verificationToken: "" }
  - { accountId: "xiaolongxia", appId: "cli_a9f1849b67f9dcc2", appSecret: "g7dTIRe6Tz8jYzASSKTT2eBV5LGzrKDr", encryptKey: "", verificationToken: "" }
  - { accountId: "yiran_yibao", appId: "cli_a923c71498b8dcc9", appSecret: "swscrlPKYCwAehOyyoLrlesLTsuYY6nl", encryptKey: "", verificationToken: "" }
- teams:
  - teamKey: "internal_main"
    groupPeerId: "oc_f785e73d3c00954d4ccd5d49b63ef919"
    supervisorAgentId: "supervisor_internal_main"
    opsAgentId: "ops_internal_main"
    financeAgentId: "finance_internal_main"
    hiddenMainSessionKey: "agent:supervisor_internal_main:main"
    sqliteDbPath: "~/.openclaw/teams/internal_main/state/team_jobs.db"
  - teamKey: "external_main"
    groupPeerId: "oc_7121d87961740dbd72bd8e50e48ba5e3"
    supervisorAgentId: "supervisor_external_main"
    opsAgentId: "ops_external_main"
    financeAgentId: "finance_external_main"
    hiddenMainSessionKey: "agent:supervisor_external_main:main"
    sqliteDbPath: "~/.openclaw/teams/external_main/state/team_jobs.db"

约束：
1) 先审计现有 ~/.openclaw/openclaw.json，输出 to_add / to_update / to_keep_unchanged。
2) 只修改和 V5 直接相关的项：
   - channels.feishu
   - bindings
   - agents.defaults / agents.list
   - messages.groupChat.mentionPatterns
   - team runtime manifest
   - supervisor / worker workspace prompt
   - watchdog / hygiene / canary
3) 每个 team 都必须生成自己的 hidden main session key，不允许共享 agent:supervisor_agent:main。
4) 每个 team 都必须生成自己的 SQLite db 路径。
5) 每个 team 都必须生成自己的 watchdog service / timer / launchd label。
6) worker 必须严格执行：message(progress) -> 读取真实 progressMessageId -> message(final) -> 读取真实 finalMessageId -> sessions_send(COMPLETE_PACKET|status=completed) -> NO_REPLY。
7) `resume-job` 必须能消费 hidden main transcript 中最近有效 `COMPLETE_PACKET`，并跳过 `pending / placeholder / sent / <pending...>` 这类占位回调。
7) canary 必须验证：
   - worker 的 progress_message_id / final_message_id
   - supervisor 最终收口目标群
   - 无协议外泄
8) 文档和模板里必须写入当前两群和三个机器人真实配置，不允许继续只给抽象占位骨架。
9) 后续新增第 3 个、第 10 个团队时，只能通过复制一段 teams[] 配置扩展，不能改协议。
```

## 推荐验收顺序

1. 先执行 team hygiene  
2. 对每个 worker 执行一次性 WARMUP  
3. 在内部群发一次主管任务  
4. 观察群里顺序是否固定  
5. 跑 `v51_team_orchestrator_canary.py --require-supervisor-target-chat`
6. 再到外部群重复同样流程  
7. 最后做双群隔离验证，确认两边互不串线

## 与 V4.3.1 的关系

`V5` 不是推翻 `V4.3.1`，而是把 `V4.3.1` 的生产稳定件模板化：

- 每个群都有自己的 supervisor / workers
- 每个群都有自己的 session hygiene / watchdog / canary
- prompt、角色、职能改由 `teams` 模型统一生成
- 未来新增团队时，主要工作变成复制 `teams[]` 和改 prompt，不再重做协议设计
