# 飞书多 Agent 自动跨群收口交付蓝图（V2.1 Pro）

## 对客户的价值承诺

这份蓝图的目标不是“多加一个机器人”，而是把企业协同升级为“可执行的 AI 团队作业流”：

1. 自动跨群收口
- 销售、运营、财务在各自群正常协作，主管 Agent 自动汇总三方结论。

2. 管理层可直接决策
- 输出统一执行稿，固定包含：核心结论、冲突点、优先级、明日三件事、风险预案。

3. 最小改造、低风险上线
- 保留现有业务群路由，仅新增 manager 群 + supervisor_agent + agentToAgent。

4. 可交付、可审计、可回滚
- 提供完整的变更计划、上线命令、验收标准与回滚步骤。

## 适用范围

- 已有飞书多群、多机器人、多角色 Agent 的企业环境
- 需要“跨部门自动收口”的经营管理场景
- 需要在 brownfield 现网做增量改造而不是重建

## 你的当前真实环境基线

```yaml
project:
  channel: "feishu"
  mode: "brownfield-incremental"

accounts:
  - accountId: "aoteman"
    botName: "奥特曼"
    appId: "cli_a923c749bab6dcba"
    appSecret: "TWpD207Ri2g1Qqmw4R5YhfkPRhOokCGX"
    encryptKey: "<从飞书控制台-事件与回调获取>"
    verificationToken: "<从飞书控制台-事件与回调获取>"

  - accountId: "xiaolongxia"
    botName: "小龙虾找妈妈"
    appId: "cli_a9f1849b67f9dcc2"
    appSecret: "g7dTIRe6Tz8jYzASSKTT2eBV5LGzrKDr"
    encryptKey: "<从飞书控制台-事件与回调获取>"
    verificationToken: "<从飞书控制台-事件与回调获取>"

  - accountId: "yiran_yibao"
    botName: "易燃易爆"
    appId: "cli_a923c71498b8dcc9"
    appSecret: "swscrlPKYCwAehOyyoLrlesLTsuYY6nl"
    encryptKey: "<从飞书控制台-事件与回调获取>"
    verificationToken: "<从飞书控制台-事件与回调获取>"

existingRoutes:
  - { peerKind: "group", peerId: "oc_ffab0130d2cfb80f70c150918b4d4e87", accountId: "aoteman", agentId: "sales_agent" }
  - { peerKind: "group", peerId: "oc_da719e85a3f75d9a6050343924d9aa62", accountId: "xiaolongxia", agentId: "ops_agent" }
  - { peerKind: "group", peerId: "oc_1a3c32a99d6a8120f9ca7c4343263b24", accountId: "yiran_yibao", agentId: "finance_agent" }

managerGroup:
  peerKind: "group"
  peerId: "oc_84677faa225ba8a380d3721c654f17a1"
  accountId: "aoteman"
  currentDetectedAgentId: "main"
  targetAgentId: "supervisor_agent"

agents:
  - { id: "sales_agent", role: "销售咨询" }
  - { id: "ops_agent", role: "运营执行" }
  - { id: "finance_agent", role: "财务分析" }
  - { id: "supervisor_agent", role: "自动跨群收口" }
```

## 一次性交付主提示词（直接发给 Codex）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，按生产标准完成“自动跨群收口（主管模式）”交付。

# 1) 交付目标
- 在现网 brownfield 上做 incremental 最小改动。
- 保留现有 3 条业务群路由不变。
- 新增 manager 群 -> supervisor_agent。
- 让 supervisor_agent 可调用 sales_agent / ops_agent / finance_agent 自动收口。

# 2) 固定输入（按原值使用）
accounts:
- { accountId: "aoteman", botName: "奥特曼", appId: "cli_a923c749bab6dcba", appSecret: "TWpD207Ri2g1Qqmw4R5YhfkPRhOokCGX", encryptKey: "<真实值>", verificationToken: "<真实值>" }
- { accountId: "xiaolongxia", botName: "小龙虾找妈妈", appId: "cli_a9f1849b67f9dcc2", appSecret: "g7dTIRe6Tz8jYzASSKTT2eBV5LGzrKDr", encryptKey: "<真实值>", verificationToken: "<真实值>" }
- { accountId: "yiran_yibao", botName: "易燃易爆", appId: "cli_a923c71498b8dcc9", appSecret: "swscrlPKYCwAehOyyoLrlesLTsuYY6nl", encryptKey: "<真实值>", verificationToken: "<真实值>" }

existingRoutes:
- { peerKind: "group", peerId: "oc_ffab0130d2cfb80f70c150918b4d4e87", accountId: "aoteman", agentId: "sales_agent" }
- { peerKind: "group", peerId: "oc_da719e85a3f75d9a6050343924d9aa62", accountId: "xiaolongxia", agentId: "ops_agent" }
- { peerKind: "group", peerId: "oc_1a3c32a99d6a8120f9ca7c4343263b24", accountId: "yiran_yibao", agentId: "finance_agent" }

managerRoute:
- { peerKind: "group", peerId: "oc_84677faa225ba8a380d3721c654f17a1", accountId: "aoteman", agentId: "supervisor_agent" }

agents:
- { id: "sales_agent", role: "销售咨询", systemPrompt: "你是销售 Agent。输出需求摘要、推荐方案、前提约束和下一步动作；信息不足先问3个澄清问题；不得承诺未确认折扣和交付。" }
- { id: "ops_agent", role: "运营执行", systemPrompt: "你是运营 Agent。把目标拆成任务清单并给负责人建议、时间节点、依赖和风险；默认给周计划与当日待办；跨部门事项先列待确认项。" }
- { id: "finance_agent", role: "财务分析", systemPrompt: "你是财务 Agent。输出关键指标表（当前值/目标值/差异/建议）；标注口径与周期；税务合规问题必须提示人工复核。" }
- { id: "supervisor_agent", role: "跨群收口", systemPrompt: "你是主管收口 Agent。必须先调用 sales/ops/finance 三个 Agent 获取结构化摘要，再输出统一执行方案、冲突点、明日三件事、风险预案；信息不足时列待补数据，不得臆测。" }

# 3) 执行约束
1. 先读取并审计 ~/.openclaw/openclaw.json。
2. 输出 to_add / to_update / to_keep_unchanged。
3. 仅允许修改：channels.feishu、agents.list、bindings、tools.agentToAgent。
4. bindings 顺序必须：peer+accountId 精确 > accountId > 渠道兜底。
5. 保持 existingRoutes 不变，只新增 managerRoute。
6. tools.agentToAgent 必须 enabled=true，allow 至少包含 supervisor_agent、sales_agent、ops_agent、finance_agent。
7. 默认 requireMention=true，allowMentionlessInMultiBotGroup=false。
8. 每个 accountId、peerId、agentId 必须真实存在，不得猜测。

# 4) 输出要求
1. 最小 patch（可直接粘贴）。
2. 命令清单：
   - 备份
   - openclaw config validate
   - openclaw gateway restart
   - openclaw agents list --bindings
   - canary 验证
   - 回滚
3. manager 群演示脚本：
   - “请做一次跨群自动收口：输出三方摘要、冲突点、统一执行计划、明日三件事、风险预案。”
4. 验收报告模板：路由命中、角色边界、收口质量、风险提示、日志证据。
```

## 从前到后执行步骤（人工操作）

1. 在 manager 群确认机器人 `aoteman` 已在群内。  
2. 确认 manager 群 ID 已固定为 `oc_84677faa225ba8a380d3721c654f17a1`。  
3. 确认三条业务路由保持不变。  
4. 将主提示词发给 Codex，产出最小 patch。  
5. 先备份配置，再应用 patch。  
6. 执行 `openclaw config validate`。  
7. 重启网关并执行 `openclaw agents list --bindings`。  
8. 在 manager 群发送收口测试指令并验收。  
9. 记录日志证据与回滚命令归档。  

## 演示与验收脚本（manager 群）

```text
请做一次跨群自动收口：
主题：4月促销活动
输出：销售/运营/财务三方摘要、冲突点、统一执行方案、明日三件事、风险预案。
```

验收通过标准：
1. manager 群命中 `supervisor_agent`。  
2. 回复包含三方结论，不是单团队视角。  
3. 有统一计划、优先级、风险与依赖。  
4. 输出可直接用于管理层决策。  

## 增量扩展模板（不重构现网）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，在现有自动跨群收口架构上做增量扩展。

扩展项：
- 新增群：{ peerKind: "group", peerId: "oc_new_xxx", accountId: "<现有账号或新账号>", agentId: "<新或现有agent>" }
- 如新增账号，同时新增 accountMappings 凭据。
- 如新增 agent，同时更新 tools.agentToAgent.allow，确保 supervisor_agent 可调用。

约束：
1) 不改动已稳定的路由与账号。
2) 仅输出最小 patch。
3) 给出扩展前后对比（to_add / to_update / to_keep_unchanged）。
4) 给出 canary 验证与回滚步骤。
```

## 常见问题（交付现场）

1. manager 群仍命中 `main`
- 将 manager 群路由改为 `agentId=supervisor_agent`。

2. supervisor 没有跨群信息
- 检查 `tools.agentToAgent.enabled=true`。
- 检查 `allow` 是否包含四个 agent。

3. 输出像“聊天”，不是“决策稿”
- 强化 supervisor 的 systemPrompt：必须按固定结构输出。

4. 担心影响现网
- 本蓝图是增量改造；保留原业务路由；可回滚。
