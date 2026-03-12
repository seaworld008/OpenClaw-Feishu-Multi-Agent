# V5.1 Unified Entry Field Guide

这份手册只回答一件事：

**新机器部署时，统一入口的每个字段应该放在哪一层，哪些是正式支持能力，哪些不要配。**

适用范围：
- `V5.1 Hardening`
- `accounts + roleCatalog + teams(profileId + override)`
- `parallel stage + publishOrder`

不适用范围：
- 旧 `routes`
- `start-job-with-workflow` 直控 supervisor 流程
- worker 直接 `message(progress/final)` 的旧协议

## 1. 主线结构

统一入口固定按这 3 层组织：

```text
accounts
roleCatalog
teams
```

含义：
- `accounts`：账号与凭据真源
- `roleCatalog`：角色默认定义真源
- `teams`：群、角色启用关系、流程编排真源

builder 会自动派生：
- `channels.feishu`
- `bindings`
- `agents.list`
- `v51 runtime manifest`

不要手工维护：
- `routes`
- `bindings`
- `channels.feishu.accounts.<group>.systemPrompt`

## 2. accounts 层放什么

放账号和凭据：
- `accountId`
- `appId`
- `appSecret`
- `encryptKey`
- `verificationToken`
- `overrides`（仅账号级平台字段）

建议：
- `accountId` 一旦确定，不要在不同环境随意改名
- `accountId` 必须与 `roleCatalog.*.accountId`、`teams[].group.entryAccountId` 对齐

## 3. roleCatalog 层放什么

放角色默认定义：
- `kind`
- `roleKey`
- `accountId`
- `name`
- `role`
- `visibleLabel`
- `description`
- `responsibility`
- `identity`
- `mentionPatterns`
- `visibility`
- `systemPrompt`
- `runtime`

适合放在 `roleCatalog` 的信息：
- 所有群通用的角色职责
- 所有群通用的角色提示词
- 所有群通用的显示名
- 所有群通用的 per-agent runtime 默认值

### roleCatalog.runtime 正式支持什么

当前正式支持写入单个 agent 的字段只有：
- `model`
- `sandbox`

示例：

```json
{
  "ops_default": {
    "kind": "worker",
    "accountId": "xiaolongxia",
    "role": "运营专家",
    "visibleLabel": "运营",
    "visibility": "visible",
    "runtime": {
      "model": {
        "primary": "sub2api/gpt-5.3-codex"
      },
      "sandbox": {
        "sessionToolsVisibility": "all"
      }
    },
    "systemPrompt": "<draft-only worker prompt>"
  }
}
```

### roleCatalog.runtime 当前不要写什么

不要写到单个 agent：
- `maxConcurrent`
- `subagents`

原因：
- OpenClaw 当前会把这些当作 `agents.list` 非法字段
- 它们应该继续放在顶层 `agents.defaults`

## 4. teams 层放什么

`teams[]` 定义每个群的真实运行关系：
- `teamKey`
- `displayName`
- `group`
- `supervisor`
- `workers`
- `workflow`

### teams[].group

放群级入口信息：
- `peerId`
- `entryAccountId`
- `requireMention`

### teams[].supervisor / teams[].workers[]

主线推荐写法：

```json
{
  "profileId": "ops_default",
  "agentId": "ops_internal_main",
  "overrides": {}
}
```

适合放在 `overrides` 的内容：
- 某个群专属 `systemPrompt`
- 某个群专属 `description`
- 某个群专属 `identity`
- 某个群专属 `visibleLabel`
- 某个群专属 `runtime`

### teams[].*.overrides.runtime 正式支持什么

与 `roleCatalog.runtime` 一致，只支持：
- `model`
- `sandbox`

它的作用是：
- 在保留角色默认值的前提下，对某个 team 的某个 agent 做覆盖

示例：

```json
{
  "profileId": "ops_default",
  "agentId": "ops_external_main",
  "overrides": {
    "runtime": {
      "model": {
        "primary": "sub2api/gpt-5.4-codex"
      }
    }
  }
}
```

builder 会按下面规则合并：
- 先取 `roleCatalog.runtime`
- 再用 `overrides.runtime` 覆盖同名键

## 5. workflow 层放什么

`workflow.stages` 是唯一正式流程定义。

### 串行 stage

```json
{
  "mode": "serial",
  "stages": [
    { "agentId": "ops_internal_main" },
    { "agentId": "finance_internal_main" }
  ]
}
```

### 并行 stage

```json
{
  "mode": "parallel",
  "stages": [
    {
      "stageKey": "analysis",
      "mode": "parallel",
      "agents": [
        { "agentId": "ops_internal_main" },
        { "agentId": "finance_internal_main" }
      ],
      "publishOrder": [
        "ops_internal_main",
        "finance_internal_main"
      ]
    }
  ]
}
```

规则：
- `parallel` stage 必须写 `stageKey`
- `parallel` stage 必须写 `agents`
- `parallel` stage 必须写 `publishOrder`
- `publishOrder` 必须完整覆盖该 stage 的全部 worker，且顺序唯一

## 6. agents.defaults 放什么

这层放所有 agent 共用的运行时默认值。

适合放：
- `model`
- `workspace`
- `maxConcurrent`
- `subagents`
- `sandbox`

如果你想改：
- 全部 agent 的并发
- 全部 agent 的默认 workspace
- 全部 agent 的子代理并发

请改 `agents.defaults`，不要写到 `roleCatalog.runtime` 或 `overrides.runtime`。

## 7. worker 协议必须怎么写

worker `systemPrompt` 必须符合当前正式主线：
- 不再直接 `message(progress/final)`
- 只提交：
  - `progressDraft`
  - `finalDraft`
  - `summary`
  - `details`
  - `risks`
  - `actionItems`
- 最后一条 assistant 响应直接输出单个结构化 JSON

不要再写旧协议：
- `message(progress) -> message(final) -> callback -> NO_REPLY`

## 8. supervisor 协议必须怎么写

supervisor 群会话必须保持：
- `ingress-only`
- 首轮真实用户消息直接 `NO_REPLY`
- 不直接建单
- 不直接发接单
- 不直接发最终收口
- 不直接 `sessions_spawn`

真正流程只能是：

```text
ingress -> controller -> outbox -> sender -> callback sink
```

## 9. 新机器填写顺序

推荐顺序：
1. 先填 `accounts`
2. 再填 `roleCatalog`
3. 再填 `teams[].group`
4. 再填 `teams[].supervisor/workers`
5. 再填 `workflow.stages`
6. 最后才填 `runtime`

这样最稳，因为：
- 账号没对齐，后面的角色和 team 都会漂
- roleCatalog 没收好，后续每个群都会重复写 prompt
- workflow 没定义完整，controller 无法稳定运行

## 10. 一句话原则

**全局默认放 `agents.defaults`，角色默认放 `roleCatalog`，单群特化放 `teams[].overrides`，流程编排只放 `workflow.stages`。**
