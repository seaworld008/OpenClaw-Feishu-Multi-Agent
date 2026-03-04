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
目标：多个 accountId 对应多个业务角色 Agent。
要求：
- match.channel 使用 feishu
- 每条绑定显式 accountId + peer
- 先精确后兜底排序
- 默认 requireMention=true，仅指定群例外
输出最终可粘贴配置和验证清单。
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
