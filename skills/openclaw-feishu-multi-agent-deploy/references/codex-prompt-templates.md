# Codex 真实交付模板（唯一目标：自动跨群收口 / 主管模式）

## 客户价值说明（可直接转发）

这套配置不是“多加一个机器人”，而是把企业协作从“单点问答”升级为“多角色团队协同”：

1. 从分散沟通到统一决策  
- 销售、运营、财务各自在自己的群里工作，主管 Agent 自动跨群收口，产出一份统一执行方案。

2. 从聊天回复到可执行结果  
- 输出不再是泛泛建议，而是“结论 + 冲突点 + 优先级 + 明日三件事 + 风险预案”的管理可执行稿。

3. 从人肉汇总到自动汇总  
- 不需要运营负责人每天手工搬运三方结论，主管 Agent 自动拉取并整合，显著减少协同成本。

4. 从试验性 AI 到可交付体系  
- 保留现有 3 群 3 bot 业务隔离，仅做最小增量改造（新增 manager 群 + supervisor_agent + agentToAgent），风险可控、可回滚、可验收。

适用场景：
- 经营例会周报收口
- 活动上线跨部门决策
- 销售-交付-财务联动审批
- 管理层要“一页看全局”的日常经营场景

## 本文件唯一目标

只用于一件事：
- 在你当前 `3群3bot3agent` 的飞书 OpenClaw 现网上，真实交付或扩展“自动跨群收口（主管模式）”。

不讨论其他模式，不给多套分支方案，直接面向可落地交付。

## 固定参数（你当前真实环境）

> 说明：以下为你当前确认过的真实账号、群 ID 与 Agent 基线。

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

agents:
  - id: "sales_agent"
    role: "销售咨询"
  - id: "ops_agent"
    role: "运营执行"
  - id: "finance_agent"
    role: "财务分析"
  - id: "supervisor_agent"
    role: "自动跨群收口"

managerGroup:
  peerKind: "group"
  peerId: "oc_84677faa225ba8a380d3721c654f17a1"
  accountId: "aoteman"
  currentDetectedAgentId: "main"
  targetAgentId: "supervisor_agent"
```

## 一次性交付主提示词（直接发给 Codex）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，按真实生产标准完成“自动跨群收口（主管模式）”部署。

# 0) 交付目标
- 在现网 brownfield 上做 incremental 最小改动。
- 保留现有 3 条业务群路由不变。
- 新增 manager 群 -> supervisor_agent。
- 让 supervisor_agent 能调用 sales_agent、ops_agent、finance_agent 自动收口。

# 1) 固定输入（必须按原值使用）
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

# 2) 执行约束
1. 先读取并审计 ~/.openclaw/openclaw.json。
2. 输出 to_add / to_update / to_keep_unchanged。
3. 仅允许修改：channels.feishu、agents.list、bindings、tools.agentToAgent。
4. 绑定顺序必须：peer+accountId 精确 > accountId > 渠道兜底。
5. 保持三条 existingRoutes 不变，只新增 managerRoute。
6. tools.agentToAgent 必须 enabled=true，allow 至少包含 supervisor_agent、sales_agent、ops_agent、finance_agent。
7. 默认 requireMention=true；allowMentionlessInMultiBotGroup=false。
8. 每个 accountId、peerId、agentId 必须真实存在，不得猜测。

# 3) 输出要求
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
4. 验收报告模板（路由命中、角色边界、收口质量、风险提示、日志证据）。
```

## 扩展模板（只做增量扩展，不重构）

> 用于“已经跑通主管模式后”，新增一个业务群或新增一个业务 Agent。

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

## 从前到后实操步骤（人工执行顺序）

1. 在飞书新建 manager 群，并拉入 `aoteman` 对应机器人。  
2. 你当前 manager 群已确认：`oc_84677faa225ba8a380d3721c654f17a1`（`accountId=aoteman`）。  
3. 若当前路由仍是 `agentId=main`，先改为 `agentId=supervisor_agent` 再做收口演示。  
4. 把“主提示词”原样发给 Codex 执行。  
5. 应用 Codex 产出的最小 patch。  
6. 执行 validate + restart + bindings 检查。  
7. 在 manager 群发送收口测试指令。  
8. 检查输出是否包含三方摘要、冲突点、统一计划、明日三件事、风险预案。  
9. 保存验收记录与回滚命令。  

## 验收标准（必须全部通过）

1. manager 群路由命中 `supervisor_agent`。  
2. supervisor 输出中包含 sales/ops/finance 三方信息，不是单点回答。  
3. 输出有统一执行计划和优先级，而非简单拼接。  
4. 有风险项和依赖项。  
5. 回滚命令可用且已留档。  
