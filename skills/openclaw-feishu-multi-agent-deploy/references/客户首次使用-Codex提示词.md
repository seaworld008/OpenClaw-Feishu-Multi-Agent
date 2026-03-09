# 客户首次使用-Codex提示词

这份文档不是抽象模板，而是一组可以直接复制给 Codex 的操作型真实提示词。

统一原则：

- 优先让 Codex 读取输入文件，而不是把真实值散落在聊天里
- 主线 schema 统一使用 `accounts + roleCatalog + teams(profileId + override)`
- 必须先读取现网 `~/.openclaw/openclaw.json`
- 必须先备份，再生成最小 patch
- 每次都要输出 `v51 runtime manifest`

## 推荐输入文件

优先方式：

- 使用 `references/input-template-v51-fixed-role-multi-group.json`
- 或复制它生成客户自己的 `customer-v51-prod-input.json`

## 场景 1：第一次生产交付（推荐）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，基于我提供的输入文件完成本次飞书多 Agent 配置。

输入文件：
- <填写真实路径，例如 /home/user/customer-v51-prod-input.json>

要求：
1. 按 V5.1 Hardening 生成配置。
2. 主线 schema 必须按 accounts + roleCatalog + teams(profileId + override) 解析。
3. 一次配置 1 个群或多个群，均以 teams[] 为准。
4. 必须先读取现网 ~/.openclaw/openclaw.json，不要盲写。
5. 必须先备份，再生成最小 patch。
6. 输出：
   - to_add
   - to_update
   - to_keep_unchanged
   - openclaw patch
   - v51 runtime manifest
7. 若输入文件中多个群的角色组合不同，必须保持每个 team 独立，不得串线。
8. accountId 以输入文件 accounts[] 的键名为准，不得自行重命名。
9. roleCatalog 是角色默认定义入口；若 team 里需要特殊 supervisor / worker 提示词，允许覆盖，但不要把同一角色整块字段重复写进每个 team。
10. 变更完成后必须执行：
   - openclaw config validate
   - openclaw gateway restart
   - openclaw agents list --bindings
   - openclaw channels status --probe
11. 输出回滚命令、验收步骤和 canary 建议。
12. 若发现缺少信息，请先指出缺哪些字段，再继续。
```

## 场景 2：直接粘贴 JSON 输入（备选）

```text
请使用 openclaw-feishu-multi-agent-deploy skill，基于下面这份 JSON 输入完成配置。

要求：
1. 按 V5.1 Hardening 生成配置。
2. 主线 schema 必须按 accounts + roleCatalog + teams(profileId + override) 解析。
3. 必须先读取现网 ~/.openclaw/openclaw.json。
4. 必须先备份，再生成最小 patch。
5. 执行：
   - openclaw config validate
   - openclaw gateway restart
   - openclaw agents list --bindings
6. 输出：
   - openclaw patch
   - v51 runtime manifest
   - 回滚命令

<在这里粘贴真实 JSON>
```

## 场景 3：新增一个群

```text
请使用 openclaw-feishu-multi-agent-deploy skill，在现有 V5.1 Hardening 配置里新增一个群。

输入文件：
- <真实输入文件路径>

新增目标：
- 新 teamKey：<例如 marketing_main>
- 新群 peerId：<例如 oc_xxx>
- 入口 accountId：<例如 aoteman>
- 角色组合：<例如 supervisor + ops + finance>
- 是否复用现有 roleCatalog profile：<是/否>

要求：
1. 先读取现网 ~/.openclaw/openclaw.json 和输入文件。
2. 只新增这个 team 对应的配置，不要影响现有 internal_main / external_main。
3. 若新群 supervisor 只是在现有 prompt 基础上改少量上下文，优先复用已有 profileId 并做 team override。
4. 生成该群对应的 hidden main、SQLite、workspace、watchdog、launchd/systemd 命名。
5. 输出新增后的 teams[] 差异、openclaw patch、v51 runtime manifest、回滚命令。
```

## 场景 4：新增一个机器人账号

```text
请使用 openclaw-feishu-multi-agent-deploy skill，在现有 V5.1 Hardening 配置里新增一个机器人账号。

新增账号：
- accountId：<例如 legal_bot>
- appId：<真实值>
- appSecret：<真实值>
- encryptKey：<真实值>
- verificationToken：<真实值>
- 固定角色：<例如 legal>

要求：
1. 先读取现网 ~/.openclaw/openclaw.json 和输入文件。
2. 先判断该角色是否已经有 roleCatalog profile；如果没有，就新建 profile。
3. 不要让同一个 bot 在不同群承担不同角色。
4. 输出 accounts[]、roleCatalog、teams[] 的最小差异。
5. 输出 openclaw patch、v51 runtime manifest、验证命令、回滚命令。
```

## 场景 5：给现有群增加一个 worker

```text
请使用 openclaw-feishu-multi-agent-deploy skill，在现有 V5.1 Hardening 配置里给指定群增加一个 worker。

目标：
- teamKey：<例如 internal_main>
- 新 worker profileId：<例如 finance_default 或 legal_default>
- 新 worker agentId：<例如 finance_internal_main>
- 新 worker 在 workflow.stages 中的位置：<例如 ops 后、finance 前>

要求：
1. 先读取现网 ~/.openclaw/openclaw.json 和输入文件。
2. 先检查 profileId 是否已存在；若不存在，先补 roleCatalog。
3. 同步修改 teams[].workers[] 和 teams[].workflow.stages。
4. 若 worker 使用新的 accountId，同步检查 accounts[] 是否已存在。
5. 输出最小 patch、v51 runtime manifest、受影响 team 的差异、回滚命令。
```

## 场景 6：从现有群移除一个 worker

```text
请使用 openclaw-feishu-multi-agent-deploy skill，在现有 V5.1 Hardening 配置里从指定群移除一个 worker。

目标：
- teamKey：<例如 external_main>
- 待删除 agentId：<例如 finance_external_main>

要求：
1. 先读取现网 ~/.openclaw/openclaw.json 和输入文件。
2. 同步从 teams[].workers[] 和 teams[].workflow.stages 删除这个 worker。
3. 如果该 profileId 不再被任何群引用，请在输出里明确提示是否可继续清理 roleCatalog。
4. 输出最小 patch、v51 runtime manifest、回滚命令和验收步骤。
```

## 场景 7：下线一个群

```text
请使用 openclaw-feishu-multi-agent-deploy skill，在现有 V5.1 Hardening 配置里下线一个群。

目标：
- teamKey：<例如 external_main>

要求：
1. 先读取现网 ~/.openclaw/openclaw.json 和输入文件。
2. 从输入配置中删除该 team，并在输出里列出：
   - 需要清理的 runtime manifest 条目
   - 需要停掉的 watchdog service/timer 或 launchd label
   - 可归档的 SQLite / workspace / sessions 路径
3. 生成最小 patch、回滚命令和下线后验证步骤。
```

## Codex 执行时的预期产物

至少应产出：

- 新的或更新后的 `openclaw.json`
- `v51 runtime manifest`
- summary
- 验证命令
- 回滚命令

## 不推荐的用法

- 不要只把 `appId/appSecret` 和群名称口头告诉 Codex
- 不要只说“帮我配一下这几个群”
- 不要把一部分真实值放在文件里，另一部分散落在聊天里
- 不要在聊天里同时混用 canonical schema 和旧 inline `teams`

## 第一次使用时最稳的顺序

1. 先填写输入文件
2. 再看 `客户首次使用真实案例.md`
3. 再复制对应场景的提示词给 Codex
4. 再按输出的验证步骤逐条验收
