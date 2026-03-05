# Codex / 其他 AI 调用模板

## 1) 新部署（单机器人）
```text
请使用 openclaw-feishu-multi-agent-deploy skill。
读取 templates/deployment-inputs.example.yaml 的真实值，
按 incremental 模式生成 openclaw.json patch（只改 channels.feishu + bindings + agents.list 必要新增），
并输出：1) patch 内容；2)执行命令；3)验收结果模板；4)回滚命令。
```

## 2) 新部署（多机器人多角色）
```text
请使用 openclaw-feishu-multi-agent-deploy skill。
目标：多个 accountId 对应多个业务角色 Agent（支持后续直接扩展，按官方最新路由规则）。

请按以下结构读取并执行，最后给出可直接粘贴 patch + 验证与回滚命令：

- mode: "multi-bot"
- channel: "feishu"
- accountMappings:
  - accountId: "bot_main"
    role: "销售/运营"
    appId: "..."
    appSecret: "..."
    encryptKey: "..."
    verificationToken: "..."
  - accountId: "bot_finance"
    role: "财务"
    appId: "..."
    appSecret: "..."
    encryptKey: "..."
    verificationToken: "..."
- agents: ["sales_agent", "ops_agent", "finance_agent"]
- routes:
  - peerKind: "group"
    peerId: "oc_9f31a..."
    accountId: "bot_main"
    agentId: "sales_agent"
  - peerKind: "group"
    peerId: "oc_7b22d..."
    accountId: "bot_main"
    agentId: "ops_agent"
  - peerKind: "group"
    peerId: "oc_3c88e..."
    accountId: "bot_finance"
    agentId: "finance_agent"

规则：
1) 先读取现有 ~/.openclaw/openclaw.json。
2) 先做权限自检并输出缺口：消息基础权限、群免@权限、文档权限、多维表格权限（若本次需要读写 Bitable/Base）。
3) 输出 to_add / to_update / to_keep_unchanged。
4) 只改 channels.feishu、bindings、agents.list（必要新增）以及 tools.agentToAgent（按业务开启）。
5) binding 排序按精确规则优先：peer + accountId -> accountId -> 全局兜底（第一个匹配即生效）。
6) 每个输入值都必须真实存在（agentId、accountId、peer.id），不得猜测。
7) 输出：备份命令、validate、重启、`openclaw agents list --bindings`、canary 验证、回滚。
8) 若需免 @，默认只对指定群开启并提示需要飞书权限 `im:message.group_msg`。

可扩展指令：
- 新增 bot：加一条 accountMappings，并补对应 routes。
- 新增 agent：加一条 agents 和 routes。
- 新增群：加一条 routes，默认保持 requireMention=true。
```

### 多角色路由占位替换速查

- `oc_sales_group` / `oc_ops_group` / `oc_fin_group`：替换为飞书群真实 `chat_id`（`oc_...`）。
- `sales-agent` / `ops-agent` / `finance-agent`：替换为 OpenClaw 已存在的 `agentId`。
- `bot-main` / `bot-finance`：替换为 `channels.feishu.accounts` 里的账号键名（`accountId`）。

示例（替换后）：

```text
- oc_9f31a... -> sales_agent（accountId=bot_main）
- oc_7b22d... -> ops_agent（accountId=bot_main）
- oc_3c88e... -> finance_agent（accountId=bot_finance）
```

## 3) 已上线环境增量改造
```text
请使用 openclaw-feishu-multi-agent-deploy skill，按 brownfield 增量方式改造。
先读取现有 ~/.openclaw/openclaw.json，
输出 to_add / to_update / to_keep_unchanged，
不改与本次无关字段。
变更前先生成备份命令，变更后运行 config validate，并给出 canary 验收步骤。
```

## 4) 升级后兼容检查
```text
请使用 openclaw-feishu-multi-agent-deploy skill。
我刚升级 OpenClaw/feishu 插件，请检查当前配置是否兼容最新版本，
重点检查 defaultAccount、bindings 顺序、requireMention 与群覆盖、多账号出站路由。
输出修复建议与最小补丁。
```

## 5) 你当前场景可直接用的“真实部署任务”模板
```text
请使用 openclaw-feishu-multi-agent-deploy skill。
请按官方 feishu 插件路线在 brownfield 环境做增量改造，并先做权限与 ID 核验。

输入：
- accountMappings:
  - { accountId: "bot_main", appId: "...", appSecret: "...", encryptKey: "...", verificationToken: "..." }
  - { accountId: "bot_finance", appId: "...", appSecret: "...", encryptKey: "...", verificationToken: "..." }
- agents:
  - { id: "sales_agent", role: "销售咨询", systemPrompt: "你是销售 Agent。输出需求摘要、推荐方案、前提约束和下一步动作；信息不足先问3个澄清问题；不得承诺未确认折扣和交付。" }
  - { id: "ops_agent", role: "运营执行", systemPrompt: "你是运营 Agent。把目标拆成任务清单并给负责人建议、时间节点、依赖和风险；默认给周计划与当日待办；跨部门事项先列待确认项。" }
  - { id: "finance_agent", role: "财务分析", systemPrompt: "你是财务 Agent。输出关键指标表（当前值/目标值/差异/建议）；标注口径与周期；税务合规问题必须提示人工复核。" }
- routes:
  - { peerKind: "group", peerId: "oc_9f31a...", accountId: "bot_main", agentId: "sales_agent" }
  - { peerKind: "group", peerId: "oc_7b22d...", accountId: "bot_main", agentId: "ops_agent" }
  - { peerKind: "group", peerId: "oc_3c88e...", accountId: "bot_finance", agentId: "finance_agent" }
- needBitableAccess: true

输出要求：
1) 权限核验清单：必需权限、缺失权限、补齐路径。
2) 变更计划：to_add / to_update / to_keep_unchanged。
3) 最小 patch：仅 channels.feishu、bindings、agents.list、可选 tools.agentToAgent。
4) 命令清单：备份、validate、重启、bindings 检查、canary、回滚。
5) 验收模板：路由正确率、角色行为一致性、误触发率、日志证据。
6) 若 systemPrompt 为空，先按角色最佳实践补齐再输出 patch。
```

## 6) 自动跨群收口（主管模式）专用模板（快速版）
```text
请使用 openclaw-feishu-multi-agent-deploy skill。
在我当前 3群3bot3agent 的现网基础上，做最小增量改造，实现“自动跨群收口”。

当前基线（已存在）：
- routes:
  - { peerKind: "group", peerId: "oc_ffab0130d2cfb80f70c150918b4d4e87", accountId: "aoteman", agentId: "sales_agent" }
  - { peerKind: "group", peerId: "oc_da719e85a3f75d9a6050343924d9aa62", accountId: "xiaolongxia", agentId: "ops_agent" }
  - { peerKind: "group", peerId: "oc_1a3c32a99d6a8120f9ca7c4343263b24", accountId: "yiran_yibao", agentId: "finance_agent" }

目标：
- 新增 manager 群路由到 supervisor_agent
- supervisor_agent 可调用 sales/ops/finance 三个 agent 汇总输出

输入：
- managerRoute:
  - { peerKind: "group", peerId: "oc_manager_xxx", accountId: "aoteman", agentId: "supervisor_agent" }
- supervisor:
  - { id: "supervisor_agent", role: "跨群收口", systemPrompt: "先调用 sales/ops/finance 获取摘要，再输出统一执行方案、冲突点、明日三件事、风险预案。" }

要求：
1) 先读取 ~/.openclaw/openclaw.json，并输出 to_add/to_update/to_keep_unchanged。
2) 仅修改必要字段：agents.list、bindings、tools.agentToAgent。
3) tools.agentToAgent:
   - enabled: true
   - allow 至少包含 supervisor_agent、sales_agent、ops_agent、finance_agent。
4) 保持原 3 条业务路由不变，只新增 manager 路由。
5) 输出完整命令：备份、validate、重启、bindings检查、canary、回滚。
6) 输出 manager 群演示脚本：
   - “请做一次跨群自动收口：输出三方摘要、冲突点、统一执行计划、明日三件事、风险预案。”
```

## 7) 自动跨群收口最小配置手册（完整版）

### 目标

在你现有的 `3群3bot3agent` 架构上，增加一个“主管收口能力”：
- 销售群由 `sales_agent` 服务
- 运营群由 `ops_agent` 服务
- 财务群由 `finance_agent` 服务
- 管理群由 `supervisor_agent` 服务
- `supervisor_agent` 自动向三个业务 Agent 拉取结论并汇总成统一执行方案

这套方案不破坏现有业务群隔离，属于最小增量改造。

### 当前基线（你已具备）

- 销售群：`oc_ffab0130d2cfb80f70c150918b4d4e87` -> `aoteman` -> `sales_agent`
- 运营群：`oc_da719e85a3f75d9a6050343924d9aa62` -> `xiaolongxia` -> `ops_agent`
- 财务群：`oc_1a3c32a99d6a8120f9ca7c4343263b24` -> `yiran_yibao` -> `finance_agent`

### 最小改造策略

1. 新增一个管理群（manager 群）
2. 选一个 bot 进入管理群（最小化方案可复用 `aoteman`）
3. 新增 `supervisor_agent`
4. 新增一条 manager 群 route，绑定到 `supervisor_agent`
5. 启用 `tools.agentToAgent` 并允许 `supervisor_agent` 调用三个业务 Agent

### 架构图（逻辑）

- `sales_group` -> `sales_agent`
- `ops_group` -> `ops_agent`
- `finance_group` -> `finance_agent`
- `manager_group` -> `supervisor_agent`
- `supervisor_agent` --(agentToAgent)--> `sales_agent` / `ops_agent` / `finance_agent`

### 配置片段（可直接套用）

#### 1) agents.list 增加主管 Agent

```jsonc
{
  "agents": {
    "list": [
      { "id": "sales_agent" },
      { "id": "ops_agent" },
      { "id": "finance_agent" },
      {
        "id": "supervisor_agent",
        "identity": {
          "name": "Supervisor",
          "description": "跨群汇总与决策收口"
        }
      }
    ]
  }
}
```

#### 2) bindings 增加 manager 群路由

`oc_manager_xxx` 请替换成你管理群真实 `peer.id`。

```jsonc
{
  "bindings": [
    {
      "agentId": "sales_agent",
      "match": {
        "channel": "feishu",
        "accountId": "aoteman",
        "peer": { "kind": "group", "id": "oc_ffab0130d2cfb80f70c150918b4d4e87" }
      }
    },
    {
      "agentId": "ops_agent",
      "match": {
        "channel": "feishu",
        "accountId": "xiaolongxia",
        "peer": { "kind": "group", "id": "oc_da719e85a3f75d9a6050343924d9aa62" }
      }
    },
    {
      "agentId": "finance_agent",
      "match": {
        "channel": "feishu",
        "accountId": "yiran_yibao",
        "peer": { "kind": "group", "id": "oc_1a3c32a99d6a8120f9ca7c4343263b24" }
      }
    },
    {
      "agentId": "supervisor_agent",
      "match": {
        "channel": "feishu",
        "accountId": "aoteman",
        "peer": { "kind": "group", "id": "oc_manager_xxx" }
      }
    }
  ]
}
```

#### 3) 启用 agentToAgent

```jsonc
{
  "tools": {
    "agentToAgent": {
      "enabled": true,
      "allow": [
        "supervisor_agent",
        "sales_agent",
        "ops_agent",
        "finance_agent"
      ]
    }
  }
}
```

### 推荐 systemPrompt

#### supervisor_agent

```text
你是主管收口 Agent。你的职责是跨团队汇总并形成决策稿。
工作流程固定：
1) 先向 sales_agent、ops_agent、finance_agent 各发起一次摘要请求；
2) 收集后输出统一报告，必须包含：目标、现状、分团队结论、冲突点、统一计划、明日三件事、风险与预案；
3) 信息不足时列出“待补数据清单”，不得臆测。
输出格式必须分节，便于管理层直接决策。
```

#### 三个业务 Agent（建议补充一条）

```text
当收到 supervisor_agent 的协作请求时，请用结构化摘要返回：
- 本团队目标
- 当前进展
- 风险
- 对其他团队的依赖
- 24小时内建议动作
```

### 飞书侧操作步骤

1. 新建管理群（建议命名：`经营决策-收口群`）
2. 把用于主管路由的机器人拉入该群（最小化可复用 `aoteman`）
3. 在管理群发一条测试消息
4. 在 OpenClaw 日志中获取管理群 `peer.id`（`oc_manager_xxx`）
5. 回填到 bindings

### OpenClaw 上线步骤

1. 备份配置
2. 应用最小 patch（agents + bindings + tools.agentToAgent）
3. `openclaw config validate`
4. `openclaw gateway restart`
5. `openclaw agents list --bindings`
6. manager 群做 canary 测试

### 演示与验收脚本（管理群）

在 manager 群发送：

```text
请做一次跨群自动收口：
主题：4月促销活动
输出：销售/运营/财务三方摘要、冲突点、统一执行方案、明日三件事、风险预案。
```

验收标准：
1. 主管回复中出现三方结论，不是单一团队视角。
2. 输出有统一计划与优先级，不是简单拼接。
3. 明确风险与依赖项。
4. 路由日志显示 manager 群命中 `supervisor_agent`。

### 常见问题

1. 主管只输出自己观点，没有三方信息
- 检查 `tools.agentToAgent.enabled` 与 `allow` 是否包含四个 Agent
- 强化 `supervisor_agent` systemPrompt 的“先调用再汇总”约束

2. 主管群消息跑到 sales_agent
- 检查 manager 群 `peer.id` 是否写错
- 检查 bindings 顺序，manager 的精确绑定必须在兜底规则前

3. 三方摘要质量不稳定
- 给业务 Agent 增加“响应 supervisor 时使用固定结构”的 systemPrompt
- 统一输出模板，减少自由发挥

### 推荐上线策略

- 生产业务群继续保持 `3群3bot` 隔离
- manager 群作为“跨群收口层”新增，不替代业务群
- 先 canary 使用，稳定后纳入常规运营流程
