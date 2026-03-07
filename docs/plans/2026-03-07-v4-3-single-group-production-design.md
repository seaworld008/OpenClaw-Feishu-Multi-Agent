# V4.3 Single-Group Production Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现有单群可见协作能力之上，设计一版适合真实客户上线的 `V4.3` 单群生产方案：用户不再手输 `taskId`，主管自动生成内部 `jobRef`，并通过单群活跃任务队列与状态层保证多轮对话不串任务。

**Architecture:** 保留 `V4.2.1` 的可见协作形态，但把用户输入、主管编排、worker 回包和最终收口全部挂到外部状态层。控制面仍使用 `sessions_send/sessions_history`，展示层继续由 worker 显式 `message` 发群消息。单群只允许一个活跃任务，其余新任务入队或被识别为补充说明。

**Tech Stack:** OpenClaw `@openclaw/feishu`、Feishu 群聊、SQLite（默认推荐）或飞书多维表格（可视化替代）

---

## 目标结论

1. 生产环境不要求用户输入 `taskId`。
2. supervisor 在接单时自动生成内部 `jobRef`，用于日志、状态表、worker 协同和故障排查。
3. 一个团队群默认只维护一个活跃任务，其余新任务进入队列或被判断为当前任务补充说明。
4. worker 继续先发群内进度，再发群内结论，详细结果和结构化完成包仍回 supervisor。
5. 最终收口不再只依赖 transcript，自上而下以状态表为准。
