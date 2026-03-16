# Open Source Launch Post Draft

## 为什么现在开源

我们把 `OpenClaw-Feishu-Multi-Agent` 开源，不是为了单纯公开一套提示词，而是希望把一条已经在真实交付里反复验证过的主线方法公开出来：

- 多角色分析
- 确定性控制面
- 顺序发布群消息
- supervisor 决策型终稿

这个项目想解决的不是“机器人能不能进群”，而是“多机器人团队能不能稳定、可交付、可扩展地在真实客户环境里工作”。

## 适合谁

这套仓库主要适合两类人：

1. 开发者
- 想研究多 Agent orchestration
- 想复用 controller / outbox / callback sink 思路
- 想在 Feishu 上做更可控的群协作系统

2. 客户/交付团队
- 想直接拿来交付多机器人团队
- 想把一套 demo 方案升级成生产可运行方案
- 想减少“prompt 自己决定流程”带来的不稳定

## 它和常见方案有什么不同

最核心的不同是：

- `LLM 负责内容，代码负责流程`

也就是说：

- worker 不直接决定群里什么时候发什么
- controller 决定状态推进
- outbox / sender 决定消息真正发出
- supervisor 最终统一收口不是自由发挥，而是基于全量角色结论做决策型终稿

## 你可以先看什么

第一次进入仓库，建议直接看：

1. `README.md`
2. `ARCHITECTURE.md`
3. `DEMO.md`
4. `examples/`

如果你是交付团队，再继续看：

1. `codex-prompt-templates-v51-team-orchestrator.md`
2. `V5.1-新机器快速启动-SOP.md`
3. `客户首次使用真实案例.md`
