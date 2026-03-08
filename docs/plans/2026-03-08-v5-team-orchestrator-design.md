# V5 Team Orchestrator Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `V4.3.1` 单群生产能力的基础上，设计一版可模板化扩展的 `V5`：支持 1 个、2 个、10 个飞书群并行运行，每个群内都是 1 个主管 + N 个可配置 worker agents，且会话、持久记忆、状态层和运维隔离互不影响；同时提供可直接交付给 Codex 的完整配置、真实账号映射和长版提示词模板。

**Architecture:** `V5` 不再把“多群”理解为共享三只全局 agent 的多路复用，而是把每个群封装成一个可复制的 team unit。每个 team unit 拥有独立的 supervisor/worker agent IDs、workspace、session namespace、SQLite 状态文件和 watchdog；根配置只负责声明账号、团队规格和生成规则。运行时继续采用 orchestrator-worker 模式，但 worker 数量、角色、职责、提示词、可见性和执行顺序均由团队模板定义。生成器除 OpenClaw patch 外，还要输出 team runtime manifest，供 Codex 按 team 自动落地 workspace prompt、watchdog、hygiene、canary 和回滚步骤。

**Tech Stack:** OpenClaw `@openclaw/feishu`、Feishu 群聊、Python `json`/`pathlib`、仓库内配置生成脚本与 Markdown 交付模板

---

## 背景约束

`V4.3.1` 已验证单群长期运行，但它把 hidden main 固定为共享的 `agent:supervisor_agent:main`，并假设 supervisor / ops / finance 三个 agent 会被多个任务反复复用。这一做法在单群内成立，但扩展到多群时有两个结构性问题：

1. 会话隔离不够硬。群 session 虽然天然按 `agent:<agentId>:feishu:group:<peerId>` 区分，但 hidden main 与 workspace 仍然是共享面。
2. 记忆隔离不够硬。OpenClaw 的 `session-memory` hook、`memoryFlush` 和 daily memory 都是按 agent workspace 组织；若同一 agent 服务多个群，未来一旦写入 durable memory，就可能出现跨群污染。

因此 `V5` 的设计目标不是把 `V4.3.1` 简单复制成“多群共享 3 agent”，而是把 `V4.3.1` 封装成“可复制的团队单元”。

## 设计选择

### 方案 A：共享 3 个全局 agent，多群只靠 `groupPeerId` 隔离

优点：
- 配置最少
- 迁移成本低

缺点：
- hidden main 和 workspace 仍是共享面
- 与 `session-memory`、`memoryFlush`、daily memory 的边界冲突
- 新增群越多，历史污染和升级回归越难排查

结论：不作为 `V5` 推荐方案。

### 方案 B：每群一套独立 team unit，统一由模板生成

优点：
- session、workspace、memory、SQLite、watchdog 都天然独立
- 完整继承 `V4.3.1` 的生产思路，只是把共享实例改成模板化实例
- 对 OpenClaw 未来升级更稳，影响面主要收敛到生成器和回归脚本

缺点：
- agent 数量会线性增长
- 配置生成器需要升级

结论：这是 `V5` 推荐方案。

### 方案 C：每群一个 Gateway

优点：
- 基础设施隔离最强

缺点：
- 运维复杂度过高
- 不符合“一个模板快速复制多个团队”的交付目标

结论：仅保留为极端隔离场景，不作为默认路线。

## 最终架构

`V5` 固定采用 `Team Orchestrator` 模式：

- 每个群必须且只允许 1 个 orchestrator / supervisor agent
- 每个群可以有 1 到 N 个 worker agents
- 所有 worker 的调度权归 supervisor 所有
- worker 是否群内可见、执行顺序、角色定义、职责边界、systemPrompt 长文案均来自团队模板

每个 team unit 至少包含以下运行时对象：

- 1 个飞书群 `groupPeerId`
- 1 个 supervisor agent
- N 个 worker agents
- 1 个独立 `team_jobs.db`
- 1 个独立 watchdog 命名空间
- 1 套独立 workspace / memory / session store

命名规则采用 team key 派生，避免复用旧的全局 agent：

```text
teamKey = market_sz
supervisor agentId = supervisor_market_sz
worker agentId = ops_market_sz / finance_market_sz / copy_market_sz
workspace = ~/.openclaw/teams/market_sz/workspaces/<role>
agentDir = ~/.openclaw/teams/market_sz/agents/<role>/agent
hidden main = agent:supervisor_market_sz:main
db = ~/.openclaw/teams/market_sz/state/team_jobs.db
watchdog = v5-team-market_sz.timer
```

## 当前生产基线

当前需要先固化为 `V5` 正式示例的，是这两套真实团队：

- 老群 / 内部团队群：`oc_f785e73d3c00954d4ccd5d49b63ef919`
- 新群 / 外部团队群：`oc_7121d87961740dbd72bd8e50e48ba5e3`
- 三个机器人账号：
  - `aoteman` / `奥特曼`
  - `xiaolongxia` / `小龙虾找妈妈`
  - `yiran_yibao` / `易燃易爆`

`V5` 文档和模板必须包含这两套群信息与三机器人真实映射，不能只保留抽象骨架。后续第 3 个、第 10 个群继续通过复制 `teams[]` 单元扩展，而不是改协议。

## 配置模型

`V5` 输入不再只是一维 `agents + routes`，而是显式声明 `teams`：

```json
{
  "mode": "plugin",
  "accounts": [],
  "teams": [
    {
      "teamKey": "market_sz",
      "displayName": "深圳外部群团队",
      "group": {
        "peerId": "oc_xxx",
        "entryAccountId": "marketing-bot",
        "requireMention": true
      },
      "supervisor": {
        "agentId": "supervisor_market_sz",
        "name": "奥特曼",
        "role": "主管总控",
        "responsibility": "接单、拆解、调度、收口",
        "systemPrompt": "..."
      },
      "workers": [
        {
          "agentId": "ops_market_sz",
          "accountId": "ops-bot",
          "name": "小龙虾找妈妈",
          "role": "运营专家",
          "responsibility": "活动打法、节奏、执行动作",
          "visibility": "visible",
          "systemPrompt": "..."
        }
      ],
      "workflow": {
        "mode": "serial",
        "stages": [
          {"agentId": "ops_market_sz"},
          {"agentId": "finance_market_sz"}
        ]
      }
    }
  ]
}
```

约束：

- 一个 `teamKey` 对应一个群
- 一个群只能被一个 `teamKey` 占用
- 一个群只能有一个 supervisor
- 同一群内每个 agent 都必须占用独立 `accountId`
- `workflow.stages[].agentId` 必须引用当前 team 的 worker
- worker 数量不固定，但默认推荐 2-6 个
- 并行不是默认值；只有团队模板显式声明时才允许并行阶段
- `teamKey` 必须是可直接用于路径与 service 命名的安全标识

## 运行时行为

`V5` 的行为约束比 `V4.3.1` 更严格：

1. 用户消息进入 supervisor 的群会话
2. supervisor 通过本 team 的 `team_jobs.db` 生成 `jobRef`
3. supervisor 按 `workflow.stages` 调度 worker
4. 默认生产模式是严格串行：上一 stage 未完成前，不得派下一位 worker
5. worker 仅向本 team 的 hidden main 回 `COMPLETE_PACKET`
6. hidden main 依据本 team 的状态层推进下一个阶段或最终收口

关键变化：

- hidden main 不再是全局共享的 `agent:supervisor_agent:main`
- hidden main 改为每个 supervisor 自己的 `agent:<supervisorAgentId>:main`
- team runtime manifest 必须显式产出：
  - hidden main session key
  - worker group session keys
  - SQLite db path
  - watchdog service/timer/label
  - canary / hygiene 的命令参数
- 这使 `COMPLETE_PACKET`、daily memory、watchdog 和 session hygiene 都天然限定在 team 内

## 记忆与隔离策略

`V5` 的隔离边界分两层：

1. 运行态隔离：`groupPeerId` + team 内 agent IDs
2. 持久态隔离：每个 team 独立 workspace / memory / db / sessions

这意味着：

- 可以继续保留 OpenClaw 的 `session-memory` hook 和 `memoryFlush`
- 但这些持久记忆只会落到本 team 的 agent workspace
- 新增第 2 个、第 10 个群时，不会与已有团队共用 same-brain memory

如果客户明确要求“完全无持久记忆”，`V5` 还可以提供可选的 stateless 配置开关；但这不是默认推荐。

## 交付物

`V5` 需要新增以下交付物：

- `V5` 设计文档
- `V5` 配置输入模板
- `V5` JSONC 配置快照
- `V5` Codex 提示词/交付手册
- 构建脚本对 `teams` 模型的支持
- 构建脚本输出的 team runtime manifest
- 文档中的 upgrade / rollout / verification 清单
- 以当前两群真实值填充的“完整可执行版”交付模板

## 测试与回归

`V5` 至少要覆盖这些断言：

- 输入 `teams` 后能生成正确的 `agents.list`
- 每个 team 的 supervisor / workers 会生成独立 bindings
- 同一飞书账号参与多个 team 时，群级 `systemPrompt` 仍按 `peerId` 精确分发
- 群级 `requireMention` 会真正落到 `channels.feishu.groups.<peerId>`
- hidden main 以 `agent:<supervisorAgentId>:main` 参数化生成
- 生成器会输出 runtime manifest，而不是静默丢弃 `workflow` / `visibility` / `responsibility`
- `teamKey` 不合法时会明确报错
- canary 能校验 worker 可见消息、协议外泄，以及 supervisor 最终收口目标群
- README / 模板 / 手册能明确说明 `1 supervisor + N workers` 的约束
- `V5` 文档包含当前两群与三机器人真实配置

## 分阶段实施

第一阶段只做仓库能力升级，不直接动客户现网：

- 文档与设计先升级到 `V5`
- 生成器升级为 `teams` 输入 + team runtime manifest 输出
- 输出一份 `V5` 示例 JSONC 和一份 `V5` 参考手册
- 把当前两群、三机器人、长版提示词沉淀成可直接复用的 Codex 提示词
- 测试覆盖生成器、runtime manifest、文档、快照与 canary

第二阶段再决定是否对远端 VMware 现网做 `V5` 演进验证。
