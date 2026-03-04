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

## 使用 Codex 的实战案例（安装到上线）

下面这套话术可直接复制给 Codex，适合你给客户做“飞书多机器人多角色”交付。

1. 先让 Codex 安装本仓库 skill（安装完成后按提示重启 Codex）

```text
请使用 $skill-installer，
从 GitHub 安装这个 skill 到我的 Codex：
https://github.com/seaworld008/OpenClaw-Feishu-Multi-Agent/tree/main/skills/openclaw-feishu-multi-agent-deploy
安装成功后提醒我重启 Codex。
```

2. 重启 Codex 后，给它这个“真实部署任务”

```text
请使用 openclaw-feishu-multi-agent-deploy skill，帮我完成一个客户的飞书多 Agent 部署。

场景：
- OpenClaw 已在生产运行（brownfield）
- 使用官方 feishu 插件路线（channel=feishu）
- 两个飞书机器人：
  - bot-main：服务销售和运营
  - bot-finance：服务财务
- 三个 Agent：
  - sales-agent（销售咨询）
  - ops-agent（运营执行）
  - finance-agent（财务分析）
- 路由目标：
  - oc_sales_group -> sales-agent（accountId=bot-main）
  - oc_ops_group -> ops-agent（accountId=bot-main）
  - oc_fin_group -> finance-agent（accountId=bot-finance）

要求：
1) 先读取并检查现有 ~/.openclaw/openclaw.json
2) 按 incremental 输出 to_add / to_update / to_keep_unchanged
3) 只改 channels.feishu、bindings、tools.agentToAgent 必要字段
4) 绑定顺序必须“精确规则在前，兜底规则在后”
5) 输出完整命令：备份、应用、openclaw config validate、重启、canary 验证、回滚
6) 给出最终可粘贴 patch 和验收清单
```

3. 你只需要把占位值换成真实值
- `accountId`、`appId`、`appSecret`
- 群 ID（`oc_xxx`）和 Agent ID
- 是否免 @（若免 @，确认飞书已审批 `im:message.group_msg`）

4. 交付验收建议
- 先在 canary 群验证，再全量放量
- 每条 binding 至少做一次实测（群+私聊）
- 留存回滚命令和验证证据（日志/截图/命令输出）

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
