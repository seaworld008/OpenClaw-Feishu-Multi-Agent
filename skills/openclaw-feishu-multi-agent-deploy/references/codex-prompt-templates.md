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
2) 输出 to_add / to_update / to_keep_unchanged。
3) 只改 channels.feishu、bindings、agents.list（必要新增）以及 tools.agentToAgent（按业务开启）。
4) binding 排序按精确规则优先：peer + accountId -> accountId -> 全局兜底（第一个匹配即生效）。
5) 每个输入值都必须真实存在（agentId、accountId、peer.id），不得猜测。
6) 输出：备份命令、validate、重启、`openclaw agents list --bindings`、canary 验证、回滚。
7) 若需免 @，默认只对指定群开启并提示需要飞书权限 `im:message.group_msg`。

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
