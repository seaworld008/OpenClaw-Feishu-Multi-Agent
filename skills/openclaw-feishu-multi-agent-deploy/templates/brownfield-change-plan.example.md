# Brownfield 变更计划（示例）

## 1. 基线信息
- 客户环境：`prod`
- 当前 OpenClaw 版本：`v2026.x`
- 当前配置文件：`~/.openclaw/openclaw.json`
- 变更策略：`incremental`
- 灰度策略：`canary_then_full`

## 2. 变更范围
仅允许改动：
- `channels.feishu`
- `bindings`
- （可选）`agents.list` 新增条目
- （可选）`tools.agentToAgent`

禁止改动：
- 与本次飞书路由无关的 provider、tools、sandbox、gateway 全局参数

## 3. to_add
- 新增 `channels.feishu.accounts.<accountId>`
- 新增/补齐 `channels.feishu.defaultAccount`
- 新增指定群/私聊的 `bindings`

## 4. to_update
- `channels.feishu.requireMention`（按策略调整）
- `channels.feishu.groups.<chatId>.requireMention`（按群覆盖）
- `channels.feishu.groupPolicy` / `dmPolicy`

## 5. to_keep_unchanged
- 既有非飞书渠道配置
- 既有模型与密钥配置
- 既有运行时安全策略

## 6. 执行步骤
1. 备份原配置
2. 生成最小 patch
3. `openclaw config validate`
4. 重启网关
5. canary 群验证
6. 全量放开

## 7. 回滚命令（示例）
```bash
cp ~/.openclaw/openclaw.json.bak.$TS ~/.openclaw/openclaw.json
openclaw gateway restart
```

## 8. 验收标准
- canary 群命中正确 agent
- 无重复回复、无串路由
- 免@策略符合预期
- 日志中 accountId/peer.id/agentId 三元命中正确
