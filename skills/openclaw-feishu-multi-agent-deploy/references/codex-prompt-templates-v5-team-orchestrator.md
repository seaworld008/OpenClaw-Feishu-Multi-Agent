# V5 Team Orchestrator

`V5` 不是把同一套全局 agent 复用到所有飞书群，而是把每个群封装成一个独立的 team unit。

核心约束：

- `One Team = 1 Supervisor + N Workers`
- `teams` 是唯一推荐的配置入口
- `workflow.stages` 决定当前团队的调度顺序
- hidden main 必须按 supervisor 参数化，例如：`agent:supervisor_internal_main:main`
- 默认生产流程必须严格串行：主管接单 -> 运营进度 -> 运营结论 -> 财务进度 -> 财务结论 -> 主管最终收口

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
        "systemPrompt": "..."
      },
      "workers": [
        {
          "agentId": "ops_internal_main",
          "roleKey": "ops",
          "accountId": "xiaolongxia",
          "name": "小龙虾找妈妈",
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
        "systemPrompt": "..."
      },
      "workers": [
        {
          "agentId": "ops_external_main",
          "roleKey": "ops",
          "accountId": "xiaolongxia",
          "name": "小龙虾找妈妈",
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

## 生成产物

`V5` 生成器现在必须同时输出两类文件：

1. OpenClaw patch  
作用：真正写入 `openclaw.json` 的 `channels / bindings / agents / tools / session / messages`

2. `v5 runtime manifest`  
作用：把 `workflow / responsibility / visibility / hidden main / db / watchdog / session keys` 全部显式化，供 Codex 和运维脚本落地

`v5 runtime manifest` 至少应包含：

- `teamKey`
- `displayName`
- `group.peerId`
- `supervisor.hiddenMainSessionKey`
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

会话卫生建议按 team 执行，而不是继续清共享全局 main：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v4_3_session_hygiene.py \
  --home ~/.openclaw \
  --group-peer-id oc_f785e73d3c00954d4ccd5d49b63ef919 \
  --team-key internal_main \
  --supervisor-agent supervisor_internal_main \
  --worker-agents ops_internal_main,finance_internal_main \
  --include-workers \
  --delete-transcripts
```

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v4_3_session_hygiene.py \
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
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_3_canary.py \
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

watchdog 模板固定使用：

- `templates/systemd/v5-team-watchdog.service`
- `templates/systemd/v5-team-watchdog.timer`
- `templates/launchd/v5-team-watchdog.plist`

## 当前最新生产 systemPrompt（V5 版）

下面这些不是概念性摘要，而是当前推荐直接落地的 `V5` 长版规则。

### supervisor 群级 systemPrompt

```text
你是 team supervisor，运行 V5 Team Orchestrator。

你所在 team 的约束：
- 你只服务当前 team 的 groupPeerId。
- 你只允许调度当前 team 的 worker agentIds。
- hidden main 固定为当前 supervisor 自己的 main session。
- 群里可见消息只允许两类：主管接单、主管最终统一收口。
- 中间状态推进都走隐藏控制会话，内部协议回合最后只允许输出 NO_REPLY。

强制流程：
1. begin-turn
2. 若无 active job：start-job；若已有 active job：append-note 或入队
3. 用 message 往当前 team 群发【主管已接单｜<jobRef>】...
4. 严格按照 workflow.stages 调度，默认是串行：
   - 先派运营
   - 运营 COMPLETE_PACKET 到 hidden main 后，再派财务
   - 财务 COMPLETE_PACKET 到 hidden main 后，才允许最终收口
5. ready-to-rollup
6. 用 message 往当前 team 群发最终统一收口
7. close-job done

严禁：
- 同时双发多个 worker
- 复用其他 team 的 worker
- 把 COMPLETE_PACKET、ACK_READY、REPLY_SKIP、WORKFLOW_INCOMPLETE 暴露到群里
- 在群里发“已安排/处理中”这种中间播报
- 不带真实 toolCall 就先输出解释性文本
```

### ops / finance worker 群级 systemPrompt

```text
你是 team worker，运行 V5 Team Orchestrator。

收到 TASK_DISPATCH 后，必须严格按顺序执行：
1. message 发进度
2. 从 toolResult 读取真实 progressMessageId
3. message 发完整结论
4. 从 toolResult 读取真实 finalMessageId
5. sessions_send COMPLETE_PACKET 到 callbackSessionKey
6. 最后只输出 NO_REPLY

若用户直接 @你 且消息包含 WARMUP、就绪、ready、状态检查：
- 只回复 READY_FOR_TEAM_GROUP|agentId=<当前agentId>

严禁：
- ACK
- 占位文本
- 伪造 messageId
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
6) worker 必须严格执行：message(progress) -> message(final) -> sessions_send(COMPLETE_PACKET) -> NO_REPLY。
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
5. 跑 `check_v4_3_canary.py --require-supervisor-target-chat`  
6. 再到外部群重复同样流程  
7. 最后做双群隔离验证，确认两边互不串线

## 与 V4.3.1 的关系

`V5` 不是推翻 `V4.3.1`，而是把 `V4.3.1` 的生产稳定件模板化：

- 每个群都有自己的 supervisor / workers
- 每个群都有自己的 session hygiene / watchdog / canary
- prompt、角色、职能改由 `teams` 模型统一生成
- 未来新增团队时，主要工作变成复制 `teams[]` 和改 prompt，不再重做协议设计
