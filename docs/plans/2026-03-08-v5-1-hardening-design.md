# V5.1 Hardening Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把 `V5 Team Orchestrator` 从“主要依赖 prompt 判断流程”升级为可长期复用的 `V5.1 Hardening`，通过确定性状态机彻底消除多群串线、阶段漏派、收口静默和 stale session 反复复发的问题。

**Architecture:** `V5.1 Hardening` 的核心原则是：`LLM 负责内容，代码负责流程`。`supervisor` 不再根据 prompt 自己理解“下一步派谁/该不该收口”，而是通过 registry 的确定性命令读取 `nextAction`，再按返回结果派单或收口。多群隔离仍然沿用 `V5 team unit`，但关键控制面改成 `Deterministic Orchestrator`，由 SQLite 状态层显式保存 `workflow/current_stage/waiting_for_agent/next_action`。

**Tech Stack:** Python 3、SQLite、OpenClaw `@openclaw/feishu`、Markdown 文档、仓库内 `core_feishu_config_builder.py` 与 `core_job_registry.py`

---

## 问题复盘

现有 `V5` 已经完成：
- 多群 team unit 隔离
- 每群独立 hidden main
- 真实双群 + 三机器人模板化

但线上反复出现的问题仍然集中在控制面：
- `ops COMPLETE_PACKET` 到达后，主管没有继续派发财务
- 主管会直接 `NO_REPLY`
- 同一阶段有时被错误跳过
- 靠 `session hygiene` 或手工重放才能恢复

这类故障的共性不是“群隔离没做”，而是“状态推进仍然交给 prompt 临场判断”。

## 为什么 prompt 状态机会重复失效

当前 `V5` 文档虽然写了严格串行，但真实约束仍主要存在于 `SOUL.md / systemPrompt`：
- 主管 prompt 负责理解 `workflow.stages`
- 主管 prompt 负责判断当前该派谁
- 主管 prompt 负责判断何时 `ready-to-rollup`

这会带来三个结构性问题：
- 模型会把“已有 completion packet”误判为“可以收口”
- 中间态发生时，模型可以合法输出 `NO_REPLY`
- prompt 一旦局部漂移，就需要靠清 session 或热修救火

结论：继续堆 prompt 不是根治方案。

## 方案比较

### 方案 A：继续强化 prompt

优点：
- 改动小

缺点：
- 仍依赖模型即时判断
- 线上会继续出现同类故障

结论：不推荐。

### 方案 B：Deterministic Orchestrator

优点：
- 流程推进完全可验证
- 多群扩容只是配置复制
- 文档、生成器、远端部署能保持同一套协议

缺点：
- 需要升级 registry 和文档

结论：推荐。

### 方案 C：独立外部编排服务

优点：
- 隔离最硬

缺点：
- 偏离当前 OpenClaw skill 主线
- 运维复杂度高

结论：暂不作为当前主线。

## 推荐方案：Deterministic Orchestrator

`V5.1 Hardening` 正式采用 `Deterministic Orchestrator`：

- `start-job-with-workflow`
  - 建单并写入 workflow
  - 明确首个 `nextAction=dispatch`
- `mark-dispatch`
  - 只允许派发当前 `waitingForAgentId`
  - 派发后把状态推进为 `wait_worker`
- `mark-worker-complete`
  - 只接受当前阶段 worker 的 completion
  - 自动推进到下一阶段 `dispatch`
  - 全部完成后才进入 `rollup`
- `get-next-action`
  - supervisor 唯一可信的下一步来源
- `build-rollup-context`
  - 生成按 workflow 排序的收口上下文
- `ready-to-rollup`
  - 不再根据“已有 participant 都 done”推断
  - 只在状态机返回 `rollup` 时为真

一句话总结：

`LLM 负责内容，代码负责流程`

## 数据模型变更

`jobs` 表新增：
- `workflow_json`
- `orchestrator_version`
- `current_stage_index`
- `waiting_for_agent_id`
- `next_action`

迁移要求：
- `init-db` 必须对旧 `team_jobs.db` 自动补列
- 不能要求线上先删库重建

## Prompt 收缩策略

主管 prompt 从“解释完整状态机”收缩为“执行控制面命令”：

1. 用户发任务
2. 调 `start-job-with-workflow`
3. 发主管接单
4. 调 `get-next-action`
5. 若返回 `dispatch`，只派指定 worker
6. 收到 `COMPLETE_PACKET` 后再次调 `get-next-action`
7. 若返回 `rollup`，调 `build-rollup-context` 后统一收口
8. `close-job done`

worker prompt 保持固定：
- `message(progress) -> message(final) -> sessions_send(COMPLETE_PACKET) -> NO_REPLY`

## 多群与持久记忆边界

`V5.1 Hardening` 不改变 `V5` 的 team unit 隔离模型：
- 每个 team 仍然独立 `workspace / sessions / db / watchdog / hidden main`
- 每个群继续用自己的 `groupPeerId`
- memory 继续按 team workspace 隔离

根治点不在“再加更多 session hygiene”，而在“控制面不再依赖 prompt”。

## 验收标准

必须满足：
- 不需要 `WARMUP` 才能跑主流程
- `ops` 完成后必定派发 `finance`
- 未轮到的 worker 不能被派发
- 主管只在 `rollup` 阶段收口
- 双群并发时互不影响
- 旧数据库升级后可直接运行

## 回滚策略

若 `V5.1 Hardening` 远端验证失败：
- 保留 `V5` 旧 prompt 和旧 runtime manifest 备份
- 回滚 `openclaw.json`
- 回滚 `core_job_registry.py`
- 回滚 team workspace 下的 `SOUL.md`

但长期主线仍应收敛到 `V5.1 Hardening`，不再继续增加“热修 prompt”分支。
