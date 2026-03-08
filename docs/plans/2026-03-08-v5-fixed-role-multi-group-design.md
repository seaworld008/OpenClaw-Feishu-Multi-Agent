# V5 Fixed-Role Multi-Group Design

**Goal:** 把当前 `V5 Team Orchestrator / V5.1 Hardening` 的推荐生产形态收敛成一套更明确的正式标准：bot 可以跨很多群复用，但 role 全局固定不变；每个群只定义自己的角色组合、职责和提示词。

## Recommended Standard

- `bot 复用，role 固定`
- 同一个 bot 可以跨很多群复用，但它在所有群里都保持同一个角色
- 每个群的角色组合可以不同，只要仍然满足 `1 supervisor + N workers`
- 每个群的 `systemPrompt / description / responsibility / workflow.stages` 都按群独立配置

## Why This Standard

- 它不引入新的运行协议，直接复用现有 `teams[]` 模型
- 它把“机器人账号复用”和“角色职责稳定”这两件事拆开，降低运维复杂度
- 它允许后续新增 `第 3 / 第 10` 个群时只复制一个 `team` 块，而不是重新设计 agent 编排

## Template Shape

推荐模板由两层组成：

1. 全局固定账号到角色的映射
- `aoteman -> supervisor`
- `xiaolongxia -> ops`
- `yiran_yibao -> finance`

2. 群级 team 模板
- 每个群一个 `teamKey`
- 每个群一个 `group.peerId`
- 每个群一套 `supervisor`
- 每个群一个或多个 `workers`
- 每个群一条串行 `workflow.stages`

## Non-Goals

- 不支持同一个 bot 在不同群里切换不同角色作为正式标准
- 不引入任意 mesh 工作流引擎
- 不改变 `V5.1 Hardening` 的 control-plane 协议
