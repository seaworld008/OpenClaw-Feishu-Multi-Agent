# V5.1 Parallel Stage Ordered Publish Design

## Goal

在保持当前 `latest-only` 控制面单写架构的前提下，引入：

1. worker 并行分析
2. 群内消息按固定顺序发布
3. 主管最终统一收口继续基于所有已完成 worker 的结构化结论动态汇总

核心目标不是让 worker 自由并发发群消息，而是：

`parallel execution + ordered publish`

也就是：

- 后台并行
- 前台串行
- 状态单写
- 可见消息仍由 controller/outbox 统一控制

## Why

当前串行模型的问题：

- 总耗时接近所有 worker 执行时间之和
- 当 worker 之间没有强依赖时，串行纯属浪费时间

直接让 worker 并行且继续自己发群消息的问题：

- 群里顺序不可控
- 更容易重复发送
- 先完成的 worker 会抢发
- controller 只能事后补救

因此必须把“执行并行”和“发布顺序”拆开。

## Parallel Stage Schema

新的 `workflow` 推荐结构：

```json
{
  "workflow": {
    "stages": [
      {
        "stageKey": "analysis",
        "mode": "parallel",
        "agents": [
          {"agentId": "ops_internal_main"},
          {"agentId": "finance_internal_main"},
          {"agentId": "legal_internal_main"}
        ],
        "publishOrder": [
          "ops_internal_main",
          "finance_internal_main",
          "legal_internal_main"
        ]
      },
      {
        "stageKey": "rollup",
        "mode": "serial",
        "agents": [
          {"agentId": "supervisor_internal_main"}
        ]
      }
    ]
  }
}
```

约束：

- `stageKey` 必填，且在一个 workflow 内唯一
- `mode` 只能是 `serial` 或 `parallel`
- `parallel` stage 必须提供 `publishOrder`
- `publishOrder` 必须完整覆盖本 stage 的 worker，且顺序唯一
- `serial` stage 下 `agents` 长度必须为 1
- 现有平铺 `workflow.stages=[{"agentId": ...}]` 视为旧 schema，后续仅保留迁移兼容，不再作为主线

## Publish Gate State Model

新增 runtime store 表：

```sql
CREATE TABLE publish_gates (
  job_ref TEXT NOT NULL,
  stage_key TEXT NOT NULL,
  mode TEXT NOT NULL,
  publish_order_json TEXT NOT NULL,
  publish_cursor INTEGER NOT NULL DEFAULT 0,
  stage_status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (job_ref, stage_key)
);
```

`stage_status` 取值：

- `pending`
- `running`
- `ready_to_publish`
- `publishing`
- `completed`

语义：

- `pending`: 该 stage 尚未开始
- `running`: 该 stage 的 worker 已并行派发
- `ready_to_publish`: 至少一个 worker 已完成并进入待发布队列
- `publishing`: controller 正在按 `publishOrder` 推进可见消息
- `completed`: 当前 stage 的 worker 都已完成且都已按顺序发布

`publish_cursor` 语义：

- 指向下一个允许发布的 `agentId` 在 `publishOrder` 中的索引
- callback 先到不代表立即发群
- 只有 `publish_cursor` 指向的 worker 才能进入 outbox

## Worker Callback / Outbox Boundary

### Worker Callback

worker 只负责提交结构化结果，不直接决定群里可见时机。

推荐 payload：

```json
{
  "jobRef": "TG-...",
  "stageKey": "analysis",
  "agentId": "ops_internal_main",
  "progressDraft": "【运营进度｜TG-...】...",
  "finalDraft": "【运营结论｜TG-...】...",
  "summary": "...",
  "details": ["...", "..."],
  "risks": ["...", "..."],
  "actionItems": ["...", "..."]
}
```

要求：

- worker 可以并行完成
- worker 只回调 draft 和结构化结论
- worker 不再直接向群发可见 progress/final

### Outbox

outbox 只接收 controller 批准后的消息：

- `ack`
- `worker_progress`
- `worker_final`
- `rollup`

去重键需要扩成：

- `team_key`
- `job_ref`
- `message_kind`
- `stage_key`
- `agent_id`

这样同一 stage 下多个并行 worker 能被精确追踪，不会互相覆盖。

## Controller Responsibilities

controller 新职责：

1. 并行 stage 开始时，一次性派发所有 worker
2. 记录 callback 到达
3. 更新 publish gate
4. 按 `publishOrder` 决定当前谁允许进入 outbox
5. 当一个 worker 发布完成后，推进 `publish_cursor`
6. 当当前 stage 所有 worker 都已发布完成后，再进入下一个 stage 或 rollup

controller 不做的事：

- 不允许 worker 自己决定何时发群消息
- 不允许 reconcile 根据 transcript 直接抢发未到顺序的 worker 结果

## Migration Strategy

分三步：

1. 先增加 schema 和 store/controller API，不切现网主流程
2. 再让 controller 接管 `parallel stage + ordered publish`
3. 最后把现有 worker “直接发群消息”路径降为 deprecated，并迁移到 callback-only

## Acceptance Criteria

1. 并行 stage 下多个 worker 可以同时完成 callback
2. 群里只按 `publishOrder` 顺序看到 `progress/final`
3. 任何 worker 即使先完成，也不能越过前序 worker 先发群消息
4. 所有 worker 发布完成后，主管才允许最终统一收口
5. 主管最终统一收口仍基于所有 worker 已完成的结构化结论动态综合
