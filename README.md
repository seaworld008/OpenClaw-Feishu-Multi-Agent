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

## V1 使用 Codex 的实战案例（安装到上线）

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

## 版本地图与推荐选型

这一套仓库现在建议按 5 个版本理解，不要再把所有配置混在一起看。

### 版本总览

| 版本 | 模式 | 核心能力 | 适合场景 | 成本/复杂度 | 当前建议 |
|---|---|---|---|---|---|
| `V1` | 基础多群路由 | 一群一 Bot / 一群一 Agent，按群稳定分工 | 第一次上线、多群分工、先求稳 | 低 | 推荐作为起步版 |
| `V2` | 自动跨群收口 | 新增主管群，只做跨群汇总与收口 | 管理层汇总、经营复盘、低风险升级 | 低到中 | 推荐用于 brownfield 第一阶段升级 |
| `V3.1` | 主管派单 + 三群执行 + 自动收口 | 真派单、真执行、真收口，可审计验收 | 正式生产交付、客户 PoC、经营执行闭环 | 中到高 | 跨群生产最推荐 |
| `V4` | 单群团队模式 | 3 个机器人在同一群，主管主入口，执行角色协作 | 老板群、作战室、客户演示 | 中 | 单群演示推荐 |
| `V4.1` | 单群团队模式增强版 | 主管主导协商 + 执行角色有限互审 | 高级演示、单群指挥中心、未来团队模式 | 高 | 仍可用 |
| `V4.2` | 单群团队模式最佳实践版 | send-first probe + 展示层/控制面分离 + 主动 @ 展示协作 | 真实单群交付、高级演示、未来团队模式 | 高 | 单群当前最推荐 |

### 最推荐的配置怎么选

1. 如果你现在刚开始做客户交付，先上 `V1`。
2. 如果你已经有 3 个业务群，想先给老板一个“自动收口”的效果，上 `V2`。
3. 如果你要做真正能执行的跨群团队，直接上 `V3.1`。这是当前跨群生产最推荐版本。
4. 如果你要做“一个群里像一人公司一样协作”的效果，选 `V4`。
5. 如果你要做单群里的主管编排、执行角色有限互审、看起来更像未来团队 Agent 形态，选 `V4.1`。
6. 如果你还要兼顾“真实可交付”与“群里看起来像团队在协作”，直接选 `V4.2`。

一句话结论：
- 跨群正式交付：`V3.1` 最推荐
- 单群高级演示：`V4.2` 最推荐
- 最低风险起步：`V1`

## 各版本详细说明

### V1：基础多群多角色路由

`V1` 就是 README 里你前面已经在用的这套基础配置，正式定义为：

- 销售群 -> 销售 Bot -> `sales_agent`
- 运营群 -> 运营 Bot -> `ops_agent`
- 财务群 -> 财务 Bot -> `finance_agent`

作用：
- 让每个群只处理自己职责范围内的问题
- 每个 Agent 角色边界清晰
- 路由简单、稳定、最好排障

能力边界：
- 能分工
- 能稳定响应
- 不能自动跨群汇总
- 不能主管派单

最适合：
- 第一次上线
- 客户先验证“多角色分工”
- 对稳定性要求最高，不着急做复杂协同

你的当前真实 `V1` 路由就是：

```yaml
routes:
  - { peerKind: "group", peerId: "oc_ffab0130d2cfb80f70c150918b4d4e87", accountId: "aoteman",     agentId: "sales_agent" }
  - { peerKind: "group", peerId: "oc_da719e85a3f75d9a6050343924d9aa62", accountId: "xiaolongxia", agentId: "ops_agent" }
  - { peerKind: "group", peerId: "oc_1a3c32a99d6a8120f9ca7c4343263b24", accountId: "yiran_yibao", agentId: "finance_agent" }
```

### V2：主管群自动跨群收口

`V2` 是在 `V1` 基础上最自然的一次升级：

- 保留 3 个业务群不动
- 新增一个主管群
- 新增 `supervisor_agent`
- 主管群只做“跨群自动收口”

作用：
- 让管理层直接在主管群看到销售/运营/财务的统一结论
- 不打断业务群原有工作方式
- 非常适合 brownfield 最小增量升级

能力边界：
- 能自动汇总
- 能输出统一执行稿
- 还不是完整的“主管派单 -> 执行 -> 回收”闭环

最适合：
- 管理层看板
- 周报/日报汇总
- 客户先看“AI 团队收口能力”

文档入口：
- [飞书多 Agent 自动跨群收口交付蓝图（V2.1 Pro）](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates.md)

### V3.1：主管派单 + 三群执行 + 自动收口

`V3.1` 是当前跨群版本里最完整、最可交付的一版：

- 主管群接任务
- 主管 Agent 拆任务
- 派给销售 / 运营 / 财务三个业务群执行
- 再自动拉回结果统一收口

作用：
- 从“自动汇总”升级为“真实执行闭环”
- 更像一个真正能干活的跨群 Agent 团队

能力：
- 真派单
- 真执行
- 真收口
- 有 `dispatchEvidence`
- 有 canary 门禁
- 有回滚与验收流程

最适合：
- 正式客户交付
- 经营任务闭环
- 需要可审计、可回滚、可复盘

文档入口：
- [飞书多 Agent 主管派单与自动跨群收口交付蓝图（V3.1）](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v3.1.md)

### V4：单群高级 Agent 团队模式

`V4` 把协作方式从“跨群”切换成“单群”：

- 3 个机器人都在同一个群
- 用户默认只 `@主管机器人`
- 主管拆任务并派给同群执行角色
- 最终统一收口

作用：
- 对外看起来像一个群里的 AI 小团队
- 更适合演示、作战室、老板群

能力边界：
- 有主管
- 有执行角色
- 有派单和收口
- 不强调执行角色之间的互审协商

最适合：
- 客户演示
- 内部老板群
- 单群作战室

文档入口：
- [飞书单群高级 Agent 团队交付蓝图（V4）](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4-single-group-team.md)

### V4.1：单群团队模式增强版

`V4.1` 是 `V4` 的增强版，适合你需要“主管主导协商 + 执行角色有限互审”的单群模式：

- 主管仍是唯一主入口
- 执行角色仍按边界执行
- 在必要时允许有限互审
- 互审最多 1 轮，最终必须回主管

作用：
- 让单群模式更接近真实管理团队的决策流
- 更像未来团队 Agent 的编排模式

能力：
- 主管主导协商
- 执行角色有限互审
- 单群统一收口
- 更强的状态机门控和验收证据

最适合：
- 高级客户演示
- 单群指挥中心
- 想突出“未来团队 Agent”卖点

文档入口：
- [飞书单群高级 Agent 团队交付蓝图（V4.1）](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.1-single-group-team.md)

### V4.2：单群团队最佳实践版

`V4.2` 是在 `V4.1` 基础上继续收敛后的单群最佳实践版本：

- 控制面默认采用 send-first probe
- `sessions_list` 不再作为唯一存在性判断
- `sessions_spawn` 只做兜底，并显式承认 Feishu 下可能不可用
- ACK 阶段建议短超时，详细执行阶段建议 `timeoutSeconds=0` fire-and-forget
- 二次收口优先看 `sessions_history` 与 worker session jsonl
- 主管触发建议同时配置 `messages.groupChat.mentionPatterns` 与 `agents.list[].groupChat.mentionPatterns`
- 公开群里的主动 @ 与机器人讨论只作为展示层
- 正确性仍然只依赖 `dispatchEvidence` / `reviewEvidence`

作用：
- 既保留“群里像团队在讨论”的观感
- 又不牺牲真实派单、真实执行、真实验收

最适合：
- 真实单群交付
- 高级客户演示
- 想兼顾“能跑”和“好看”的最佳案例

文档入口：
- [飞书单群高级 Agent 团队交付蓝图（V4.2）](skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.2-single-group-team.md)

## 推荐阅读顺序

1. 先读：`references/prerequisites-checklist.md`
2. 再做：`templates/deployment-inputs.example.yaml`
3. 如果要最低风险上线，先按 `V1`
4. 如果要管理层自动汇总，读 `V2`
5. 如果要正式跨群交付，直接读 `V3.1`
6. 如果要单群高级演示，读 `V4`、`V4.1` 或直接 `V4.2`
7. 上线前看：`templates/brownfield-change-plan.example.md`
8. 上线后看：`templates/verification-checklist.md`
9. 升级回归看：`references/rollout-and-upgrade-playbook.md`

## 最佳实践来源

- OpenClaw 官方文档与 Release（已在 `references/source-cross-validation-2026-03-05.md` 记录）
- V4.2 单群团队补充交叉验证（见 `references/source-cross-validation-2026-03-06.md`）
- 飞书开放平台官方文档（事件订阅、消息事件、鉴权）

## 交叉验证更新（2026-03-05）

本仓库步骤和提示词已按官方来源再次核对，关键结论如下：

1. OpenClaw 主仓库最新主分支提交时间为 `2026-03-05`，最新 release 仍为 `v2026.3.2`（`2026-03-03` 发布）。  
2. 飞书推荐路线仍是官方插件 `@openclaw/feishu`，并使用 `match.channel = "feishu"`。  
3. 群 ID 获取仍以 `openclaw logs --follow` 读取入站 `chat_id / peer.id` 为最稳妥方案。  
4. 路由匹配继续遵循“更具体优先 + 第一个命中生效”原则，`bindings` 顺序必须严格控制。  
5. 多账号场景需显式维护 `channels.feishu.defaultAccount`，避免出站账号漂移。  
6. 免 `@` 场景依然需要配套飞书权限 `im:message.group_msg`，默认建议保持 `requireMention=true`。

### V2 Agent 系统提示词最佳实践（自动跨群收口起步版）

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

### V1 真实部署任务提示词（基础多群路由，推荐长期复用）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，按官方最新规范完成飞书多 Agent 部署。

目标：
- 在现网（brownfield）中做 incremental 最小变更。
- 使用官方 feishu 插件（match.channel=feishu）。
- 支持后续新增机器人/新增 agent/新增群时可直接扩展。

输入：
- accountMappings:
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

## 样板测试案例（客户演示版）

目标：在 15 分钟内演示“销售-运营-财务”多 Agent 团队协作能力，而不是单点聊天回复能力。

### 演示前准备（5 分钟）

1. 三个群都发一条“准备就绪”消息，确认机器人在线。  
2. 打开日志窗口：`openclaw logs --follow`，用于展示路由命中证据。  
3. 确认 3 条精确路由都已生效：`openclaw agents list --bindings`。  

### 演示主场景（48 小时促销协同）

场景统一背景：
`客户A计划48小时内上线促销活动，目标新增付费客户80个，预算上限20万。`

1) 在销售群发：

```text
客户A计划4月做促销，目标新增付费客户80个，预算上限20万。
请给出：
1. 客户分层与主推方案
2. 预计转化路径（线索->商机->签约）
3. 对运营和财务的协同需求清单
```

2) 在运营群发：

```text
基于销售群给的需求，请输出48小时可执行的运营排期：
1. Day1/Day2任务清单
2. 每项任务负责人建议
3. 依赖关系和风险预警
4. 资源不足时的优先级取舍方案
```

3) 在财务群发：

```text
基于销售目标和运营计划，做一个简版财务测算：
1. 成本拆分（固定/可变）
2. 收益与毛利率测算
3. 回款周期风险
4. 可执行的预算红线（哪些不能超）
```

4) 在任一群发收口指令（建议财务群或管理群）：

```text
请基于销售、运营、财务三方结论，输出最终执行版方案：
1. 一页总结
2. 决策建议（Go / No-Go）
3. 明日必须执行的3件事
4. 风险与应对
```

### 演示评分表（给客户看“比单机器人更强”）

每项 0-2 分，总分 10 分：

1. 路由准确：消息命中正确群对应 agent。  
2. 角色稳定：销售/运营/财务各司其职，不串角色。  
3. 输出可执行：有清单、时间、负责人建议、指标。  
4. 协同质量：三方结论可合并为统一执行方案。  
5. 风险意识：主动提示预算、资源、回款、合规风险。  

参考标准：
- `8-10` 分：可作为客户正式 PoC 演示结果。  
- `6-7` 分：可用，但需优化 systemPrompt 或路由。  
- `<=5` 分：建议先修复后再演示。  

### 常见演示失败点

1. 没开日志，无法证明“多路由命中”。  
2. 三个群提问内容差异太小，看不出角色边界。  
3. 只演示“能回复”，没有“可执行结果与收口”。  
4. 未限制免 @ 触发，导致群内噪音干扰演示。  
5. V3 缺少 `tools.allow=group:sessions`，主管只会“写派单卡”不会真实派发。  
6. V3 未放行 `tools.sessions.visibility` 或 `session.sendPolicy`，会话派发被拦截。  
7. V4/V4.1/V4.2 首轮未先 warm-up worker，会出现 `DISPATCH_INCOMPLETE + warmup_required`。
8. 只看网关日志不看 `session jsonl`，容易误判单群派单是否真的发生。
9. V4/V4.1/V4.2 若返回 `tool_call_required`，说明本轮没有任何真实工具调用，应先查 supervisor prompt 和配置是否已生效。
10. V4/V4.1/V4.2 若日志出现 `thread=true` / `subagent_spawning hooks`，说明当前 Feishu 不支持这条 `sessions_spawn` 自动补会话路径，应改为人工 warm-up。
11. V4/V4.1/V4.2 不应把公开群里的 `@其他机器人` 作为控制面正确性依赖，最佳实践是 `sessions_send` 做控制面、公开 @ 做展示层。
12. V4.2 若出现 `SEND_PATH_AVAILABLE_BUT_LIST_MISS`，说明真实 send 路径已可用，但 `sessions_list` 不能再作为唯一会话存在性判断。
13. V4.2 若出现 `TIMEOUT_BUT_WORKER_DELIVERED`，说明 worker 已执行但 supervisor 还没完成二次收口，应优先做 timeout 二次判定或 ACK 派单。
14. V4.2 若出现 `TRIGGER_MISS_ON_MENTION_OR_FORMAT_WRAP`，说明被 `@` 后仍没进工具链，应同时补 `messages.groupChat.mentionPatterns`、`agents.list[].groupChat.mentionPatterns`，并兼容 `PLAIN_TEXT` / 代码块包裹文本。
15. V4.2 若 ACK 能成功但详细任务常超时，优先改为“ACK `timeoutSeconds=15` + 详细任务 `timeoutSeconds=0` + `sessions_history` 追收正文结果”。

V3 建议加一道自动门禁（2 分钟窗口）：
```bash
LOG="/tmp/openclaw/openclaw-$(date +%F).log"
START_LINE=$(wc -l < "$LOG")
# 在主管群发送 V3 测试指令
sleep 120
bash skills/openclaw-feishu-multi-agent-deploy/scripts/check_v3_dispatch_canary.sh \
  --log "$LOG" \
  --start-line "$START_LINE" \
  --task-id "demo-v3-001" \
  --agents "sales_agent,ops_agent,finance_agent"
```

返回码说明：
- `0`：派单证据完整
- `2`：缺少目标会话轨迹
- `3`：有会话轨迹但证据不足，需继续查 `sessions_send` 原始日志

V4/V4.1 单群团队建议改用专用门禁：
```bash
LOG="/tmp/openclaw/openclaw-$(date +%F).log"
START_LINE=$(wc -l < "$LOG")
# 先在团队群 warm-up worker，再发送 V4 / V4.1 测试指令
sleep 120
bash skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_1_team_canary.sh \
  --task-id "team-v4-1-001" \
  --session-root "${HOME}/.openclaw/agents" \
  --log "$LOG" \
  --start-line "$START_LINE" \
  --required-agents "ops_agent,finance_agent" \
  --optional-agents "sales_agent"
```

V4.2 单群最佳实践建议改用新门禁：
```bash
LOG="/tmp/openclaw/openclaw-$(date +%F).log"
START_LINE=$(wc -l < "$LOG")
# 先在团队群 warm-up worker，再发送 V4.2 测试指令
sleep 120
bash skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_2_team_canary.sh \
  --task-id "team-v4-2-001" \
  --session-root "${HOME}/.openclaw/agents" \
  --log "$LOG" \
  --start-line "$START_LINE" \
  --required-agents "ops_agent,finance_agent" \
  --optional-agents "sales_agent"
```

V4/V4.1/V4.2 验收补充：
- 先看 `~/.openclaw/agents/*/sessions/*.jsonl`
- 再看 gateway log
- 若主管返回 `warmup_required`，先补 worker warm-up 再复测
- 若主管返回 `tool_call_required`，先检查 supervisor prompt、gateway restart、工具调用轨迹
- 若日志出现 `thread=true` / `subagent_spawning hooks`，不要继续重试 `sessions_spawn`
- V4/V4.1/V4.2 默认应采用 send-first probe，不要只依赖 `sessions_list`
- 若返回 `SEND_PATH_AVAILABLE_BUT_LIST_MISS`，优先检查 `dispatchEvidence`、固定 sessionKey 的 `sendStatus=ok`、worker session jsonl
- 若返回 `TIMEOUT_BUT_WORKER_DELIVERED`，优先检查 worker session jsonl、二次收口逻辑，以及是否应采用 ACK -> 正文 的双阶段派单
- 若返回 `TRIGGER_MISS_ON_MENTION_OR_FORMAT_WRAP`，优先检查 `messages.groupChat.mentionPatterns`、supervisor `groupChat.mentionPatterns` 与输入包裹兼容
- 单群生产推荐把详细执行任务改为 `timeoutSeconds=0`，再用 `sessions_history` / worker session jsonl 做二次收口

## 维护约定

- `references/generated/` 仅存放本地临时生成产物，不纳入版本控制
- 每次能力升级后同步更新：`VERSION` 与 `CHANGELOG.md`
