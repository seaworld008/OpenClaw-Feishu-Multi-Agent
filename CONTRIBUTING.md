# Contributing

感谢你关注 `OpenClaw-Feishu-Multi-Agent`。

这个项目同时服务两类读者：

- 开发者入口：希望复用 orchestration、runtime、模板与测试能力
- 交付入口：希望直接把飞书多 Agent 团队交付给客户上线

我们欢迎两类贡献，但希望改动都满足同一个原则：`small, reviewable, testable`。

## Before You Start

开始前建议先读：

1. [README.md](README.md)
2. [SECURITY.md](SECURITY.md)
3. [skills/openclaw-feishu-multi-agent-deploy/SKILL.md](skills/openclaw-feishu-multi-agent-deploy/SKILL.md)

如果你是第一次接触这个仓库：

- 想理解产品能力与交付模型：先看 README 的交付入口
- 想修改 orchestration 行为：先看 `tests/` 和 `skills/openclaw-feishu-multi-agent-deploy/scripts/`
- 想修文档：优先改 README 和 `skills/openclaw-feishu-multi-agent-deploy/references/`

## What We Accept

欢迎的贡献包括：

- 文档修复与示例完善
- 安全去敏、密钥治理、错误链接修复
- runtime / controller / outbox / callback sink 的缺陷修复
- 测试补齐和回归约束加强
- 更好的 onboarding、CI、模板和开源治理改进

不建议直接提交的大改动：

- 没有测试覆盖的大范围重构
- 未经说明的协议变更
- 把本地 `generated/` 产物或 live 配置重新提交进仓库

## Branch and PR Guidance

- 优先使用短小、聚焦的分支和提交
- 一个 PR 只解决一个主问题
- 如果改动行为，请补测试
- 如果改动文档入口，请同步 README

推荐 commit 风格：

- `feat: ...`
- `fix: ...`
- `docs: ...`
- `security: ...`
- `test: ...`

## Verification

提交前至少跑与改动相关的验证。

常用命令：

```bash
pytest tests/test_openclaw_feishu_multi_agent_skill.py -q
pytest tests/test_v51_team_controller.py tests/test_v51_outbox_sender.py tests/test_v51_worker_callback_sink.py -q
```

如果你改的是 README / 模板 /治理文件，至少要确认：

- 文档链接可打开
- 示例不包含 live secret
- 文案与当前主线 `V5.1 Hardening` 一致

## Security Rules

- 不要提交 live secret
- 不要提交客户私有 `generated/` 产物
- 如果发现泄露，请先看 [SECURITY.md](SECURITY.md)

## Good First Contributions

适合第一次参与的任务：

- 修 README 歧义
- 补充模板注释
- 增加缺失测试
- 修复失效的外部链接
- 清理示例中的去敏问题
