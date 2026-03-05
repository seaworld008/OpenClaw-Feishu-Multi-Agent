# OpenClaw-Feishu-Multi-Agent

面向交付团队的通用 Skill 仓库：用于基于 OpenClaw 搭建飞书多机器人多角色多 Agent 协作体系，支持客户环境快速落地、增量上线、可回滚与可升级。

## 当前版本

- `v1.0.0`（2026-03-04）
- 默认技术路线：官方插件 `@openclaw/feishu`
- 兼容路线：legacy `chat-feishu`

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

## 快速使用

1. 进入 Skill 目录

```bash
cd skills/openclaw-feishu-multi-agent-deploy
```

2. 填写输入模板（任选其一）

- `references/input-template.json`（默认 plugin）
- `references/input-template-plugin.json`（plugin 完整示例）
- `references/input-template-legacy-chat-feishu.json`（legacy 兼容）

3. 生成 patch

```bash
python3 scripts/build_openclaw_feishu_snippets.py \
  --input references/input-template.json \
  --out references/generated
```

4. 在 OpenClaw 环境执行验证

```bash
openclaw config validate
openclaw gateway restart
openclaw agents list --bindings
```

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
    appId: "..."
    appSecret: "..."
    encryptKey: "..."
    verificationToken: "..."
  - accountId: "xiaolongxia"
    role: "ops_bot"
    appId: "..."
    appSecret: "..."
    encryptKey: "..."
    verificationToken: "..."
  - accountId: "yiran_yibao"
    role: "finance_bot"
    appId: "..."
    appSecret: "..."
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

## 交付建议流程

- 先读：`references/prerequisites-checklist.md`
- 再做：`templates/deployment-inputs.example.yaml`
- 上线前：`templates/brownfield-change-plan.example.md`
- 上线后：`templates/verification-checklist.md`
- 升级回归：`references/rollout-and-upgrade-playbook.md`

## 最佳实践来源

- OpenClaw 官方文档与 Release（已在 `references/source-cross-validation-2026-03-05.md` 记录）
- 飞书开放平台官方文档（事件订阅、消息事件、鉴权）

## 交叉验证更新（2026-03-05）

本仓库步骤和提示词已按官方来源再次核对，关键结论如下：

1. OpenClaw 主仓库最新主分支提交时间为 `2026-03-05`，最新 release 仍为 `v2026.3.2`（`2026-03-03` 发布）。  
2. 飞书推荐路线仍是官方插件 `@openclaw/feishu`，并使用 `match.channel = "feishu"`。  
3. 群 ID 获取仍以 `openclaw logs --follow` 读取入站 `chat_id / peer.id` 为最稳妥方案。  
4. 路由匹配继续遵循“更具体优先 + 第一个命中生效”原则，`bindings` 顺序必须严格控制。  
5. 多账号场景需显式维护 `channels.feishu.defaultAccount`，避免出站账号漂移。  
6. 免 `@` 场景依然需要配套飞书权限 `im:message.group_msg`，默认建议保持 `requireMention=true`。

### Agent 系统提示词最佳实践（V2.1）

建议每个 Agent 都有“角色边界 + 输出格式 + 风险约束”，避免跨职责回答和风格漂移。

```yaml
agents:
  - id: "sales_agent"
    role: "销售咨询"
    systemPrompt: >
      你是销售 Agent。目标是识别客户需求并给出可执行方案。
      回答必须包含：需求摘要、推荐方案、报价/资源前提、下一步动作。
      未确认的信息不得承诺（折扣、交付周期、定制开发）。
      信息不足时先提出最多 3 个澄清问题。
  - id: "ops_agent"
    role: "运营执行"
    systemPrompt: >
      你是运营 Agent。目标是把业务目标拆解为可执行任务。
      回答必须包含：任务清单、负责人建议、截止时间、依赖项、风险项。
      默认给出周计划和当日待办。
      涉及跨部门协同时先给待确认清单，不擅自下结论。
  - id: "finance_agent"
    role: "财务分析"
    systemPrompt: >
      你是财务 Agent。目标是预算、成本、回款、利润分析与预警。
      回答必须包含：关键指标表（当前值/目标值/差异/建议）。
      金额相关需标注口径与时间范围。
      涉及税务或合规争议时明确“需人工复核”，不输出最终法律结论。
```

### 真实部署任务提示词（V2.1，推荐长期复用）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，按官方最新规范完成飞书多 Agent 部署。

目标：
- 在现网（brownfield）中做 incremental 最小变更。
- 使用官方 feishu 插件（match.channel=feishu）。
- 支持后续新增机器人/新增 agent/新增群时可直接扩展。

输入：
- accountMappings:
  - accountId: "aoteman"
    appId: "..."
    appSecret: "..."
    encryptKey: "..."
    verificationToken: "..."
  - accountId: "xiaolongxia"
    appId: "..."
    appSecret: "..."
    encryptKey: "..."
    verificationToken: "..."
  - accountId: "yiran_yibao"
    appId: "..."
    appSecret: "..."
    encryptKey: "..."
    verificationToken: "..."
- agents:
  - { id: "sales_agent", role: "销售咨询", systemPrompt: "你是销售 Agent。输出需求摘要、推荐方案、前提约束和下一步动作；信息不足先问3个澄清问题；不得承诺未确认折扣和交付。" }
  - { id: "ops_agent", role: "运营执行", systemPrompt: "你是运营 Agent。把目标拆成任务清单并给负责人建议、时间节点、依赖和风险；默认给周计划与当日待办；跨部门事项先列待确认项。" }
  - { id: "finance_agent", role: "财务分析", systemPrompt: "你是财务 Agent。输出关键指标表（当前值/目标值/差异/建议）；标注口径与周期；税务合规问题必须提示人工复核。" }
- routes:
  - { peerKind: "group", peerId: "oc_ffab0130d2cfb80f70c150918b4d4e87", accountId: "aoteman", agentId: "sales_agent" }
  - { peerKind: "group", peerId: "oc_da719e85a3f75d9a6050343924d9aa62", accountId: "xiaolongxia", agentId: "ops_agent" }
  - { peerKind: "group", peerId: "oc_1a3c32a99d6a8120f9ca7c4343263b24", accountId: "yiran_yibao", agentId: "finance_agent" }

约束：
1) 先读取并审计 ~/.openclaw/openclaw.json。
2) 输出 to_add / to_update / to_keep_unchanged。
3) 只修改 channels.feishu、bindings、agents.list（必要新增）和 tools.agentToAgent（仅我要求时启用）。
4) 按“peer+accountId 精确 > accountId > channel兜底”排序 bindings。
5) 校验每个 peerId、accountId、agentId 必须真实存在，不得猜测。
6) 输出完整操作命令：
   - 备份
   - openclaw config validate
   - openclaw gateway restart
   - openclaw agents list --bindings
   - canary 验证
   - 回滚
7) 输出验收报告模板（群路由正确性、角色行为一致性、误触发检查、日志证据）。
8) 若 `systemPrompt` 为空，按上述角色模板自动补齐后再生成 patch。
```

## 维护约定

- `references/generated/` 仅存放本地临时生成产物，不纳入版本控制
- 每次能力升级后同步更新：`VERSION` 与 `CHANGELOG.md`
