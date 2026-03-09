# V5.1 Role Catalog Canonicalization Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把 `V5.1 Hardening` 里分散在 `teams` 内联字段、runtime 标题派生、长版 prompt、示例 JSONC、SOP 与测试中的“角色定义”收敛成单一入口。新增 `roleCatalog + teams(profileId + override)` 的 canonical schema，并让 runtime 的可见标题、职责快照和 worker/supervisor 文案全部从标准化后的角色快照派生。

**Architecture:** 根输入新增机器可读的 `roleCatalog`，负责维护角色默认的 `kind / accountId / name / role / visibleLabel / description / responsibility / identity / mentionPatterns / visibility / systemPrompt`。`teams[]` 不再要求重复整块角色定义，而是支持 `profileId` 引用 catalog，并允许对 `accountId / visibleLabel / responsibility / identity / mentionPatterns / systemPrompt` 等字段做 team 级覆盖。构建器内部先把“旧 inline teams”和“新 profile 引用”统一归一成标准化 `RoleSpec`，再生成 patch 和 runtime manifest；runtime 在建单时持久化 supervisor / participant 的 `visibleLabel` 快照，后续所有 `【主管已接单】/【角色进度】/【角色结论】/【主管最终统一收口】` 均从快照派生，不再做 role 猜测。

**Tech Stack:** Python 3、`sqlite3`、JSON/JSONC 模板、Markdown 文档、`unittest`

---

## 问题陈述

当前仓库已经把一半角色信息收敛到 `references/input-template-v51-team-orchestrator.json` 的 `teams[].supervisor/workers[]`，但另一半仍散落在：

- `scripts/core_job_registry.py` 的运行时标题派生与 supervisor 可见文案
- `references/codex-prompt-templates-v51-team-orchestrator.md`
- `templates/openclaw-v51-team-orchestrator.example.jsonc`
- `references/客户首次使用真实案例.md`
- `references/V5.1-新机器快速启动-SOP.md`
- `tests/test_openclaw_feishu_multi_agent_skill.py`

这会导致两个问题：

1. 角色扩展越多，`role / responsibility / systemPrompt / visible title` 的副本越多。
2. runtime 标题不是配置驱动，而是靠 `role` / `agentId` 猜测“运营/财务/主管”，无法成为统一真源。

## 方案对比

### 方案 A：继续以内联 `teams` 为唯一入口，只补 `visibleLabel`

优点：
- 落地最快
- 改动面最小

缺点：
- 角色定义仍然分散在每个 team 内
- 同一个角色在不同 team 里仍要重复维护 `role / responsibility / systemPrompt`

结论：只能缓解显示标题问题，不能解决“角色目录”缺失。

### 方案 B：新增全局 `roleCatalog`，`teams` 只负责引用和覆盖

优点：
- 角色定义真正单点化
- 支持“统一默认 + team 覆盖”
- runtime、模板、文档和测试都能围绕同一个 schema 对齐

缺点：
- 构建器和 runtime 需要做一次兼容升级

结论：这是推荐方案。

### 方案 C：上升为 prompt/message DSL

优点：
- 灵活度最高

缺点：
- 对当前仓库属于过度设计
- 会让交付与调试链路变重

结论：当前阶段不做。

## Canonical Schema

根对象新增 `roleCatalog`：

```json
{
  "roleCatalog": {
    "supervisor_default": {
      "kind": "supervisor",
      "accountId": "aoteman",
      "name": "奥特曼",
      "role": "主管总控",
      "visibleLabel": "主管",
      "description": "负责任务受理、拆解、调度与统一收口。",
      "responsibility": "接单、拆解、调度、统一收口",
      "identity": {
        "name": "奥特曼总控",
        "theme": "steady orchestrator",
        "emoji": "🧭"
      },
      "mentionPatterns": ["@奥特曼", "奥特曼", "主管机器人"],
      "systemPrompt": "..."
    },
    "ops_default": {
      "kind": "worker",
      "accountId": "xiaolongxia",
      "name": "小龙虾找妈妈",
      "role": "运营专家",
      "visibleLabel": "运营",
      "description": "负责活动打法、节奏设计和执行推进。",
      "responsibility": "活动打法、节奏、执行动作",
      "visibility": "visible",
      "systemPrompt": "..."
    }
  }
}
```

`teams[]` 支持两种输入：

1. 旧格式：直接内联 `agentId / role / systemPrompt / ...`
2. 新格式：`profileId + agentId + overrides`

推荐新格式：

```json
{
  "teamKey": "internal_main",
  "group": {
    "peerId": "oc_xxx",
    "entryAccountId": "aoteman",
    "requireMention": true
  },
  "supervisor": {
    "profileId": "supervisor_default",
    "agentId": "supervisor_internal_main"
  },
  "workers": [
    {
      "profileId": "ops_default",
      "agentId": "ops_internal_main"
    }
  ]
}
```

team 特化时允许直接覆盖字段，或写到 `overrides`：

```json
{
  "profileId": "ops_default",
  "agentId": "ops_external_main",
  "visibleLabel": "运营",
  "systemPrompt": "...",
  "overrides": {
    "identity": {
      "theme": "client-facing operator"
    }
  }
}
```

## 标准化规则

构建器内部统一产出 `NormalizedTeamSpec`：

- `kind`
- `profileId`
- `agentId`
- `accountId`
- `roleKey`
- `name`
- `role`
- `visibleLabel`
- `description`
- `responsibility`
- `identity`
- `mentionPatterns`
- `visibility`
- `systemPrompt`
- `workspace`
- `agentDir`

规则：

1. `profileId` 存在时，先读取 catalog profile，再应用 team override。
2. `agentId` 必须在 team 侧显式给出，避免 catalog 污染运行时命名。
3. `visibleLabel` 缺失时允许兼容推导，但推导只作为 fallback，不再作为主线来源。
4. `supervisor.accountId` 默认取 `profile.accountId`，若仍缺失则回退 `group.entryAccountId`。
5. `worker.accountId` 必须来自 `profile.accountId` 或 team override，不允许空值。

## Runtime 规范化

runtime 不再硬编码“主管/运营/财务”，而是在建单时持久化展示快照：

- `jobs.supervisor_visible_label`
- `job_participants.visible_label`

构建/调度链路：

1. builder 输出 runtime manifest 时，把 `supervisor.visibleLabel` 和 `workers[].visibleLabel` 一并落盘。
2. `v51_team_orchestrator_reconcile.py` 在 `start-job-with-workflow` 时把这些值带入 registry。
3. `core_job_registry.py` 建单时保存快照。
4. `build-visible-ack`、`build-dispatch-payload`、`build-rollup-visible-message` 只读快照，不再猜测角色中文标签。

可见文案规则：

- `【{supervisorVisibleLabel}已接单｜<jobRef>】`
- `【{workerVisibleLabel}进度｜<jobRef>】`
- `【{workerVisibleLabel}结论｜<jobRef>】`
- `【{supervisorVisibleLabel}最终统一收口｜<jobRef>】`

## 构建器与 Manifest 变更

`core_feishu_config_builder.py` 需要：

1. 解析 `roleCatalog`
2. 把 `teams` 归一成标准化角色快照
3. patch 继续只输出 OpenClaw 需要的字段
4. runtime manifest 额外输出：
   - `profileId`
   - `kind`
   - `visibleLabel`
   - `source` 是否来自 catalog

manifest 中的 `supervisor` / `workers[]` 都必须包含标准化后的展示快照，供 runtime 直接消费。

## 文档与模板标准化

V5.1 主线文档全部改为 catalog 驱动表达：

- `references/input-template-v51-team-orchestrator.json`
- `references/input-template-v51-fixed-role-multi-group.json`
- `templates/openclaw-v51-team-orchestrator.example.jsonc`
- `references/codex-prompt-templates-v51-team-orchestrator.md`
- `references/客户首次使用真实案例.md`
- `references/V5.1-新机器快速启动-SOP.md`
- `references/客户首次使用信息清单.md`
- `README.md`
- `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`

文案原则：

- 不再把“运营/财务/主管”写成唯一真值
- 示例标题统一改成 `【{visibleLabel}进度｜TG-xxxx】` / `【{visibleLabel}结论｜TG-xxxx】`
- 文档既给 canonical schema，也保留 inline legacy 兼容说明

## 测试策略

至少覆盖：

1. builder 支持 `roleCatalog + profileId`
2. team override 能覆盖 `visibleLabel / systemPrompt / identity`
3. manifest 输出标准化 `visibleLabel`
4. registry 能持久化 `supervisor_visible_label / visible_label`
5. `build-dispatch-payload` 使用快照 `visibleLabel`
6. `build-visible-ack` / `build-rollup-visible-message` 使用快照 `visibleLabel`
7. V5.1 文档与模板都提到 `roleCatalog / profileId / visibleLabel`

## 兼容策略

- `teams[].supervisor/workers[]` 旧 inline 格式继续支持
- `V4 / V4.3.1` 资料保持历史归档，不当作主线 schema
- `V5.1` 文档明确：`roleCatalog + profileId` 是主线推荐输入

## 非目标

- 不为 `V4 / V4.3.1` 回填 `roleCatalog`
- 不引入新的 DSL
- 不改变当前 `V5.1 Hardening` 控制面状态机
