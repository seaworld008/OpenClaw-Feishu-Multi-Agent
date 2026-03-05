# 自动跨群收口最小配置手册（Supervisor + Manager 群 + agentToAgent）

## 目标

在你现有的 `3群3bot3agent` 架构上，增加一个“主管收口能力”：
- 销售群由 `sales_agent` 服务
- 运营群由 `ops_agent` 服务
- 财务群由 `finance_agent` 服务
- 管理群由 `supervisor_agent` 服务
- `supervisor_agent` 自动向三个业务 Agent 拉取结论并汇总成统一执行方案

这套方案不破坏现有业务群隔离，属于最小增量改造。

## 当前基线（你已具备）

- 销售群：`oc_ffab0130d2cfb80f70c150918b4d4e87` -> `aoteman` -> `sales_agent`
- 运营群：`oc_da719e85a3f75d9a6050343924d9aa62` -> `xiaolongxia` -> `ops_agent`
- 财务群：`oc_1a3c32a99d6a8120f9ca7c4343263b24` -> `yiran_yibao` -> `finance_agent`

## 最小改造策略

1. 新增一个管理群（manager 群）
2. 选一个 bot 进入管理群（最小化方案可复用 `aoteman`）
3. 新增 `supervisor_agent`
4. 新增一条 manager 群 route，绑定到 `supervisor_agent`
5. 启用 `tools.agentToAgent` 并允许 `supervisor_agent` 调用三个业务 Agent

## 架构图（逻辑）

- `sales_group` -> `sales_agent`
- `ops_group` -> `ops_agent`
- `finance_group` -> `finance_agent`
- `manager_group` -> `supervisor_agent`
- `supervisor_agent` --(agentToAgent)--> `sales_agent` / `ops_agent` / `finance_agent`

## 配置片段（可直接套用）

### 1) agents.list 增加主管 Agent

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

### 2) bindings 增加 manager 群路由

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

### 3) 启用 agentToAgent

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

## 推荐 systemPrompt

### supervisor_agent

```text
你是主管收口 Agent。你的职责是跨团队汇总并形成决策稿。
工作流程固定：
1) 先向 sales_agent、ops_agent、finance_agent 各发起一次摘要请求；
2) 收集后输出统一报告，必须包含：目标、现状、分团队结论、冲突点、统一计划、明日三件事、风险与预案；
3) 信息不足时列出“待补数据清单”，不得臆测。
输出格式必须分节，便于管理层直接决策。
```

### 三个业务 Agent（建议补充一条）

```text
当收到 supervisor_agent 的协作请求时，请用结构化摘要返回：
- 本团队目标
- 当前进展
- 风险
- 对其他团队的依赖
- 24小时内建议动作
```

## 飞书侧操作步骤

1. 新建管理群（建议命名：`经营决策-收口群`）
2. 把用于主管路由的机器人拉入该群（最小化可复用 `aoteman`）
3. 在管理群发一条测试消息
4. 在 OpenClaw 日志中获取管理群 `peer.id`（`oc_manager_xxx`）
5. 回填到 bindings

## OpenClaw 上线步骤

1. 备份配置
2. 应用最小 patch（agents + bindings + tools.agentToAgent）
3. `openclaw config validate`
4. `openclaw gateway restart`
5. `openclaw agents list --bindings`
6. manager 群做 canary 测试

## 演示与验收脚本（管理群）

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

## 常见问题

1. 主管只输出自己观点，没有三方信息
- 检查 `tools.agentToAgent.enabled` 与 `allow` 是否包含四个 Agent
- 强化 `supervisor_agent` systemPrompt 的“先调用再汇总”约束

2. 主管群消息跑到 sales_agent
- 检查 manager 群 `peer.id` 是否写错
- 检查 bindings 顺序，manager 的精确绑定必须在兜底规则前

3. 三方摘要质量不稳定
- 给业务 Agent 增加“响应 supervisor 时使用固定结构”的 systemPrompt
- 统一输出模板，减少自由发挥

## 推荐上线策略

- 生产业务群继续保持 `3群3bot` 隔离
- manager 群作为“跨群收口层”新增，不替代业务群
- 先 canary 使用，稳定后纳入常规运营流程
