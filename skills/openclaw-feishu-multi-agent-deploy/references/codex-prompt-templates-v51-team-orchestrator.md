# V5.1 Hardening

当前生产推荐使用 `V5.1 Hardening`。

这份文档是 `V5.1` 主线的产品手册、真实配置说明和 Codex 交付模板汇总。用户只看这一份，就应该知道：

- 上线后会得到什么效果
- 为什么 `V5.1 Hardening` 比旧方案稳
- 统一入口配置怎么写
- 当前正式双群、三个正式机器人和真实 `appId/appSecret`
- runtime manifest / hidden main / SQLite / watchdog 怎么工作
- 真实 supervisor / worker 提示词怎么写
- 怎么新增一个群、新增一个机器人账号、给现有群增加一个 worker、从现有群移除一个 worker、下线一个群

## 你将得到什么效果

`V5.1 Hardening` 最终交付的效果不是“多放几个 bot 进群”，而是一套可复制、可扩展、可回滚的 team unit 运行模型。

上线后你会得到：

1. 每个飞书群都是一个独立的 `team unit`，群与群不会共用 hidden main、SQLite、watchdog 和 workspace。
2. 每个群固定 `1` 个 supervisor，外加 `N` 个 worker。
3. 用户在群里只会看到结构化且可追踪的消息：
   - `【{visibleLabel}已接单｜TG-xxxx】`
   - `【{visibleLabel}进度｜TG-xxxx】`
   - `【{visibleLabel}结论｜TG-xxxx】`
   - `【{visibleLabel}最终统一收口｜TG-xxxx】`
4. runtime 会额外产出 `v51 runtime manifest`，把 team 的角色快照、session key、db、watchdog 名称全部显式化，供 Codex、watchdog 和运维脚本消费。
5. 后续新增第 `2` 个、第 `10` 个团队时，只改统一入口配置，不改协议。

## 核心架构

一句话原则：

- `Deterministic Orchestrator`
- `LLM 负责内容，代码负责流程`

基础约束：

- `One Team = 1 Supervisor + N Workers`
- `teams` 是唯一推荐的配置入口
- `roleCatalog` 是 `V5.1` 主线 canonical schema，统一维护角色默认的 `name / role / visibleLabel / description / responsibility / identity / mentionPatterns / systemPrompt`
- `teams[].supervisor` 与 `teams[].workers[]` 推荐写法是 `profileId + agentId + override`
- `visibleLabel` 是显示层单一来源；`【{visibleLabel}进度｜TG-xxxx】` / `【{visibleLabel}结论｜TG-xxxx】` / `【{visibleLabel}最终统一收口｜TG-xxxx】` 都从快照派生
- 当前生产推荐标准：`bot 复用，role 固定`
- 同一个 bot 可以跨很多群复用，但它在所有群里都保持同一个角色
- 每个群的角色组合可以不同，只需要在该 `team` 下启用需要的 `workers`
- `workflow.stages` 决定当前团队的调度顺序
- hidden main 必须按 supervisor 参数化，例如：`agent:supervisor_internal_main:main`
- 默认生产流程必须严格串行：主管接单 -> 运营进度 -> 运营结论 -> 财务进度 -> 财务结论 -> 主管最终收口

## 为什么要用统一入口

旧的写法把角色信息散在多个地方：

- runtime 靠 `role` 猜中文标题
- 每个 team 里重复写一遍角色的 `systemPrompt / description / responsibility`
- 文档、示例、SOP 和测试再各复制一遍

`V5.1 Hardening` 的统一入口把这三层拆开：

1. `roleCatalog` 维护角色默认定义  
这层是“角色目录”，适合统一维护 supervisor / ops / finance 这类长期稳定角色。

2. `teams[]` 维护 team 运行编排  
这层只决定谁上场、在哪个群、叫什么 `agentId`、按什么顺序执行。

3. runtime manifest 维护运行时快照  
这层把 teamKey、hidden main、db、watchdog、session key、visibleLabel 快照显式写出来。

## 实现原理

### 控制面主流程

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

### 运行时为什么稳

`V5.1 Hardening` 稳定性的关键来自 4 个边界：

1. 每个 team 独立 hidden main
2. 每个 team 独立 SQLite
3. 每个 team 独立 watchdog
4. 每个 worker / supervisor 的显示标题都固化为快照，而不是 runtime 猜测

### 标题和收口为什么不再乱

worker 回调必须携带：

- `progressTitle/finalTitle/callbackMustInclude`
- `summary=...|details=...|risks=...|actionItems=...`

supervisor 最终统一收口必须满足：

- 至少包含 `任务主题`
- 至少包含各角色结论
- 至少包含 `联合风险与红线`
- 至少包含 `明日三件事`
- 同一 `jobRef` 的最终统一收口 `只允许出现一次`
- 必须优先整理各 worker 的完整 `finalVisibleText` 终案正文，不允许只压缩成两三行摘要

## 统一入口配置

### canonical schema

```json
{
  "roleCatalog": {
    "supervisor_default": {
      "kind": "supervisor",
      "accountId": "aoteman",
      "visibleLabel": "主管",
      "description": "负责任务受理、拆解、调度与统一收口。",
      "identity": {
        "name": "奥特曼总控",
        "theme": "steady orchestrator",
        "emoji": "🧭"
      },
      "systemPrompt": "..."
    },
    "ops_default": {
      "kind": "worker",
      "accountId": "xiaolongxia",
      "visibleLabel": "运营",
      "description": "负责活动打法、节奏设计和执行推进。",
      "identity": {
        "theme": "growth operator",
        "emoji": "📈"
      },
      "systemPrompt": "..."
    }
  },
  "teams": [
    {
      "teamKey": "internal_main",
      "displayName": "内部生产团队群",
      "group": {
        "peerId": "oc_f785e73d3c00954d4ccd5d49b63ef919",
        "entryAccountId": "aoteman",
        "requireMention": true
      },
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
        "mode": "serial",
        "stages": [
          { "agentId": "ops_internal_main" }
        ]
      }
    }
  ]
}
```

### 字段分工

- `roleCatalog`：默认角色目录
- `teams[]`：team 级调度和群绑定
- `description`：给交付和运维看的角色说明
- `identity`：运行时 persona 识别信息
- `visibleLabel`：群里标题和 runtime manifest 的显示名
- `workflow.stages`：当前 team 实际派单顺序

### 当前正式生产基线

正式双群：

- 内部团队群：`oc_f785e73d3c00954d4ccd5d49b63ef919`
- 外部团队群：`oc_7121d87961740dbd72bd8e50e48ba5e3`

正式机器人：

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

正式 profile 约定：

- `supervisor_internal_default`
- `supervisor_external_default`
- `ops_default`
- `finance_default`

正式 team 约定：

- `internal_main`
- `external_main`

## 真实运行时命名

hidden main：

```text
agent:supervisor_internal_main:main
agent:supervisor_external_main:main
```

对应 runtime：

```text
db: ~/.openclaw/teams/<teamKey>/state/team_jobs.db
systemd service: v51-team-<teamKey>.service
systemd timer: v51-team-<teamKey>.timer
launchd label: bot.molt.v51-team-<teamKey>
```

`v51 runtime manifest` 至少应包含：

- `teamKey`
- `displayName`
- `group.peerId`
- `supervisor.description`
- `supervisor.identity`
- `supervisor.visibleLabel`
- `supervisor.hiddenMainSessionKey`
- `workers[].description`
- `workers[].identity`
- `workers[].visibleLabel`
- `workers[].groupSessionKey`
- `workflow.stages`
- `runtime.dbPath`
- `runtime.watchdog.systemdServiceName`
- `runtime.watchdog.systemdTimerName`
- `runtime.watchdog.launchdLabel`

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

reconcile 按 team 参数化：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py \
  --manifest ~/.openclaw/generated/openclaw-feishu-plugin-v51-runtime-latest.json \
  --team-key internal_main \
  resume-job
```

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py \
  --manifest ~/.openclaw/generated/openclaw-feishu-plugin-v51-runtime-latest.json \
  --team-key external_main \
  reconcile-dispatch
```

canary 也应按 team 参数化：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_canary.py \
  --db ~/.openclaw/teams/internal_main/state/team_jobs.db \
  --job-ref TG-V51-001 \
  --session-root ~/.openclaw/agents \
  --team-key internal_main \
  --supervisor-agent supervisor_internal_main \
  --worker-agents ops_internal_main,finance_internal_main \
  --require-visible-messages \
  --require-supervisor-target-chat \
  --success-token V51_TEAM_CANARY_OK
```

交付侧统一走 `v51_team_orchestrator_deploy.py` 生成 patch + summary + runtime manifest：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_deploy.py \
  --input skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-team-orchestrator.json \
  --out skills/openclaw-feishu-multi-agent-deploy/references/generated
```

watchdog 模板固定使用：

- `templates/systemd/v51-team-watchdog.service`
- `templates/systemd/v51-team-watchdog.timer`
- `templates/launchd/v51-team-watchdog.plist`

## 真实角色提示词

下面这些不是概念性摘要，而是当前推荐直接落地的 `V5.1 Hardening` 规则。

### supervisor 内部团队 systemPrompt

```text
你是内部团队主管 Agent，运行 V5.1 Hardening。群里只允许两类可见消息：主管接单、主管最终统一收口。被 @ 且不是 WARMUP/闲聊时，第一条 assistant 消息必须包含真实 toolCall。固定流程：begin-turn -> start-job-with-workflow -> build-visible-ack -> 用 message 工具发送【{visibleLabel}已接单｜<jobRef>】 -> record-visible-message(kind=ack) -> get-next-action -> build-dispatch-payload -> 只派发当前 stage 指定 worker -> hidden main 收 COMPLETE_PACKET -> 再次 get-next-action -> 若返回 rollup 则先 build-rollup-context，再 build-rollup-visible-message，用 message 工具发送【{visibleLabel}最终统一收口｜<jobRef>】并 record-visible-message(kind=rollup) -> close-job done。workflow.stages 必须覆盖当前 team 全部 worker。hidden main 固定为 agent:supervisor_internal_main:main。核心原则：LLM 负责内容，代码负责流程。最终统一收口必须是结构化完整方案，至少包含任务主题、各角色结论、联合风险与红线、明日三件事；同一 jobRef 的最终统一收口只允许出现一次；必须优先引用各 worker 的完整 finalVisibleText 终案正文，而不是只复述两三行摘要。若主管群 session 对真实用户消息裸 NO_REPLY，先执行 v51_team_orchestrator_hygiene.py；若仍未建单或卡在 dispatch/rollup，timer 会调用 v51_team_orchestrator_reconcile.py resume-job 从 transcript 补建单、补接单、补派单、补收口。内部协议回合最后只允许输出 NO_REPLY。
```

### supervisor 外部团队 systemPrompt

```text
你是外部团队主管 Agent，运行 V5.1 Hardening。群里只允许两类可见消息：主管接单、主管最终统一收口。被 @ 且不是 WARMUP/闲聊时，第一条 assistant 消息必须包含真实 toolCall。固定流程：begin-turn -> start-job-with-workflow -> build-visible-ack -> 用 message 工具发送【{visibleLabel}已接单｜<jobRef>】 -> record-visible-message(kind=ack) -> get-next-action -> build-dispatch-payload -> 只派发当前 stage 指定 worker -> hidden main 收 COMPLETE_PACKET -> 再次 get-next-action -> 若返回 rollup 则先 build-rollup-context，再 build-rollup-visible-message，用 message 工具发送【{visibleLabel}最终统一收口｜<jobRef>】并 record-visible-message(kind=rollup) -> close-job done。workflow.stages 必须覆盖当前 team 全部 worker。hidden main 固定为 agent:supervisor_external_main:main。核心原则：LLM 负责内容，代码负责流程。最终统一收口必须是结构化完整方案，至少包含任务主题、各角色结论、联合风险与红线、明日三件事；同一 jobRef 的最终统一收口只允许出现一次；必须优先引用各 worker 的完整 finalVisibleText 终案正文，而不是只复述两三行摘要。若主管群 session 对真实用户消息裸 NO_REPLY，先执行 v51_team_orchestrator_hygiene.py；若仍未建单或卡在 dispatch/rollup，timer 会调用 v51_team_orchestrator_reconcile.py resume-job 从 transcript 补建单、补接单、补派单、补收口。内部协议回合最后只允许输出 NO_REPLY。
```

### ops worker systemPrompt

```text
你是团队运营专家。必须先从 TASK_DISPATCH 读取 channel/accountId/target 与 progressTitle/finalTitle/callbackMustInclude，再显式 message(progress) -> 读取真实 progressMessageId -> message(final) -> 读取真实 finalMessageId -> sessions_send(COMPLETE_PACKET|status=completed|summary=...|details=...|risks=...|actionItems=...) -> NO_REPLY。两条群内可见消息的第一行必须原样使用 progressTitle/finalTitle，例如【{visibleLabel}进度｜TG-xxxx】和【{visibleLabel}结论｜TG-xxxx】；final 不得压成一句话，必须给出完整判断、执行建议、风险与下一步。禁止使用 pending/sent/<pending...>/*_placeholder 这类占位 messageId。
```

### finance worker systemPrompt

```text
你是团队财务专家。必须先从 TASK_DISPATCH 读取 channel/accountId/target 与 progressTitle/finalTitle/callbackMustInclude，再显式 message(progress) -> 读取真实 progressMessageId -> message(final) -> 读取真实 finalMessageId -> sessions_send(COMPLETE_PACKET|status=completed|summary=...|details=...|risks=...|actionItems=...) -> NO_REPLY。两条群内可见消息的第一行必须原样使用 progressTitle/finalTitle，例如【{visibleLabel}进度｜TG-xxxx】和【{visibleLabel}结论｜TG-xxxx】；final 不得压成一句话，必须给出完整判断、红线、风险与下一步。禁止使用 pending/sent/<pending...>/*_placeholder 这类占位 messageId。
```

## Codex 真实交付模板

以下模板用于让 Codex 直接按当前双群 `V5.1 Hardening` 生产模式完成交付。

```text
请使用 openclaw-feishu-multi-agent-deploy skill，按 V5.1 Hardening 生产版完成交付。

目标：
- 在同一套 OpenClaw 中同时支持 2 个飞书群：
  - 内部团队群：oc_f785e73d3c00954d4ccd5d49b63ef919
  - 外部团队群：oc_7121d87961740dbd72bd8e50e48ba5e3
- 每个群都是独立 team：
  - 1 个主管：奥特曼 / aoteman
  - 1 个运营：小龙虾找妈妈 / xiaolongxia
  - 1 个财务：易燃易爆 / yiran_yibao
- 两个群必须彻底独立：group session、hidden main、workspace、SQLite、watchdog、memory 都不能互相影响
- 主线 schema 必须使用 roleCatalog + teams(profileId + override)
- 默认执行顺序固定为：
  1. 用户发任务
  2. 主管接单并拆解
  3. 运营发进度和结论
  4. 财务发进度和结论
  5. 主管最终统一收口
- 任何群里都不允许泄漏 ACK_READY / REPLY_SKIP / COMPLETE_PACKET / WORKFLOW_INCOMPLETE

输入文件：
- <例如 /home/user/customer-v51-prod-input.json>

已知正式账号：
- aoteman / cli_a923c749bab6dcba / TWpD207Ri2g1Qqmw4R5YhfkPRhOokCGX
- xiaolongxia / cli_a9f1849b67f9dcc2 / g7dTIRe6Tz8jYzASSKTT2eBV5LGzrKDr
- yiran_yibao / cli_a923c71498b8dcc9 / swscrlPKYCwAehOyyoLrlesLTsuYY6nl

约束：
1) 先审计现有 ~/.openclaw/openclaw.json，输出 to_add / to_update / to_keep_unchanged。
2) 只修改和 V5.1 Hardening 直接相关的项：
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
7) resume-job 必须能消费 hidden main transcript 中最近有效 COMPLETE_PACKET，并跳过 pending / placeholder / sent / <pending...> 这类占位回调。
8) 文档和模板里必须写入当前两群和三个机器人真实配置，不允许继续只给抽象占位骨架。
9) 输出 openclaw patch、v51 runtime manifest、验证命令、回滚命令和 canary 步骤。
```

## 扩容与裁剪操作手册

### 新增一个群

你要做的不是复制一坨旧 inline JSON，而是：

1. 确认新群 `teamKey / peerId / displayName`
2. 决定 supervisor 是复用现有 profile 还是新建 profile
3. 在 `teams[]` 新增一个 team
4. 按这个群实际 worker 组合填写 `workers[]`
5. 按实际顺序写全 `workflow.stages`

如果新群需要独立 supervisor persona，优先新增新的 `supervisor_<team>_default`，不要把原有 profile 直接改坏。

### 新增一个机器人账号

要同步改 3 层：

1. `accounts[]`
2. `roleCatalog.<profileId>.accountId`
3. 相关 `teams[]`

不要让同一个 bot 在一个群里承担多个可见角色。

### 给现有群增加一个 worker

最少同步修改：

1. `roleCatalog`  
如果是新角色，先新增 profile；如果只是复用已有角色，直接引用已有 `profileId`。

2. `teams[].workers[]`  
为该群新增一个 `agentId + profileId`。

3. `teams[].workflow.stages`  
把这个 worker 放到正确顺序里。

### 从现有群移除一个 worker

最少同步修改：

1. 从 `teams[].workers[]` 删除
2. 从 `teams[].workflow.stages` 删除

如果这个角色以后还要在别的群用，保留 `roleCatalog`；如果任何 team 都不用了，再决定是否清理 profile。

### 下线一个群

要做两层工作：

1. 输入配置层  
从 `teams[]` 删除对应 `teamKey`

2. 运行机层  
停掉该 team 对应的 watchdog，归档或清理该 team 的 SQLite、workspace、manifest 条目和 session

## 文件与产物清单

### 输入与模板

- `references/input-template-v51-fixed-role-multi-group.json`
- `references/input-template-v51-team-orchestrator.json`
- `templates/openclaw-v51-team-orchestrator.example.jsonc`

### 用户文档

- `references/客户首次使用信息清单.md`
- `references/客户首次使用真实案例.md`
- `references/客户首次使用-Codex提示词.md`
- `references/V5.1-新机器快速启动-SOP.md`

### 运行时与运维

- `scripts/v51_team_orchestrator_reconcile.py`
- `scripts/v51_team_orchestrator_hygiene.py`
- `scripts/v51_team_orchestrator_canary.py`
- `scripts/v51_team_orchestrator_deploy.py`
- `templates/systemd/v51-team-watchdog.service`
- `templates/systemd/v51-team-watchdog.timer`
- `templates/launchd/v51-team-watchdog.plist`

### 交付产物

- OpenClaw patch
- summary
- `v51 runtime manifest`
- 验证命令
- 回滚命令

## 推荐阅读顺序

1. 先看这份产品手册
2. 再看 `客户首次使用信息清单.md`
3. 再看 `客户首次使用真实案例.md`
4. 再看 `客户首次使用-Codex提示词.md`
5. 如果是新机器从 0 到上线，再看 `V5.1-新机器快速启动-SOP.md`
