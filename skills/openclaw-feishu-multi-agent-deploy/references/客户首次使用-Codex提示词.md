# 客户首次使用-Codex提示词

这份提示词面向第一次交付时直接复制给 Codex 使用。

## 推荐方式

推荐把真实值先写进一个输入文件，再让 Codex 读取该文件。

优先方式：

- 使用 `references/input-template-v5-fixed-role-multi-group.json`
- 或复制它生成客户自己的 `customer-prod-input.json`

## 文件模式提示词（推荐）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，基于我提供的输入文件完成本次飞书多 Agent 配置。

输入文件：
- <填写真实路径，例如 /home/user/customer-prod-input.json>

要求：
1. 按 V5 Team Orchestrator / V5.1 Hardening 生成配置。
2. 一次配置 1 个群或多个群，均以 teams[] 为准。
3. 必须先读取现网 ~/.openclaw/openclaw.json，不要盲写。
4. 必须先备份，再生成最小 patch。
5. 输出：
   - to_add
   - to_update
   - to_keep_unchanged
   - openclaw patch
   - v5 runtime manifest
6. 若输入文件中多个群的角色组合不同，必须保持每个 team 独立，不得串线。
7. accountId 以输入文件 accounts[] 的键名为准，不得自行重命名。
8. 变更完成后必须执行：
   - openclaw config validate
   - openclaw gateway restart
   - openclaw agents list --bindings
   - openclaw channels status --probe
9. 输出回滚命令与验收步骤。

如果发现缺少信息，请先指出缺哪些字段，再继续。
```

## 直接粘贴 JSON 的提示词（备选）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，基于下面这份 JSON 输入完成配置。

要求：
1. 按 V5 Team Orchestrator / V5.1 Hardening 生成配置。
2. 一次配置 1 个群或多个群，均以 teams[] 为准。
3. 必须先备份，再生成最小 patch。
4. 执行 openclaw config validate。
5. 执行 openclaw gateway restart。
6. 执行 openclaw agents list --bindings。
7. 输出回滚命令。

<在这里粘贴真实 JSON>
```

## Codex 执行时的预期产物

至少应产出：

- 新的或更新后的 `openclaw.json`
- `v5 runtime manifest`
- summary
- 验证命令
- 回滚命令

## 不推荐的用法

- 不要只把 `appId/appSecret` 和群名称口头告诉 Codex
- 不要只说“帮我配一下这几个群”
- 不要把一部分真实值放在文件里，另一部分散落在聊天里

第一次使用时，最稳的方式仍然是：

1. 先填写输入文件  
2. 再复制这份提示词给 Codex  
3. 再按输出的验证步骤逐条验收
