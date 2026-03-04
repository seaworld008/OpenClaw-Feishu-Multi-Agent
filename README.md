# OpenClaw-Feishu-Multi-Agent

面向交付团队的通用 Skill 仓库：用于基于 OpenClaw 搭建飞书多机器人多角色多 Agent 协作体系，支持客户环境快速落地、增量上线、可回滚与可升级。

## 当前版本

- `v1.0.0`（2026-03-04）
- 默认技术路线：官方插件 `@openclaw/feishu`
- 兼容路线：legacy `chat-feishu`

## 仓库结构

```text
agents/
  openai.yaml
skills/
  openclaw-feishu-multi-agent-deploy/
    SKILL.md
    templates/
    references/
    scripts/
CHANGELOG.md
VERSION
README.md
```

## 核心能力

- 单机器人/多机器人多 Agent 路由（single-bot / multi-bot）
- Brownfield 增量改造（incremental）与灰度放量（canary）
- 配置生成脚本（从输入 JSON 生成 patch + 验证摘要）
- 前置条件、验收清单、回滚流程、升级回归手册

## 快速使用

1. 进入 Skill 目录

```bash
cd skills/openclaw-feishu-multi-agent-deploy
```

2. 填写输入模板（任选其一）

- `references/input-template.json`（默认 plugin）
- `references/input-template-plugin.json`（plugin 完整示例）
- `references/input-template-legacy-chat-feishu.json`（legacy 兼容）

3. 生成 patch

```bash
python3 scripts/build_openclaw_feishu_snippets.py \
  --input references/input-template.json \
  --out references/generated
```

4. 在 OpenClaw 环境执行验证

```bash
openclaw config validate
openclaw gateway restart
openclaw agents list --bindings
```

## 交付建议流程

- 先读：`references/prerequisites-checklist.md`
- 再做：`templates/deployment-inputs.example.yaml`
- 上线前：`templates/brownfield-change-plan.example.md`
- 上线后：`templates/verification-checklist.md`
- 升级回归：`references/rollout-and-upgrade-playbook.md`

## 最佳实践来源

- OpenClaw 官方文档与 Release（已在 `references/source-cross-validation-2026-03-04.md` 记录）
- 飞书开放平台官方文档（事件订阅、消息事件、鉴权）

## 维护约定

- `references/generated/` 仅存放本地临时生成产物，不纳入版本控制
- 每次能力升级后同步更新：`VERSION` 与 `CHANGELOG.md`
