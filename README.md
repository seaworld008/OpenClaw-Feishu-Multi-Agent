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

### 占位值替换对照（重点）

你提到的这三行：

- `oc_sales_group -> sales-agent（accountId=bot-main）`
- `oc_ops_group -> ops-agent（accountId=bot-main）`
- `oc_fin_group -> finance-agent（accountId=bot-finance）`

其中每一段都需要替换为你的真实值。按下面对照填：

| 示例占位 | 你要替换成什么 | 来源位置 | 常见错误 |
|---|---|---|---|
| `oc_sales_group` / `oc_ops_group` / `oc_fin_group` | 飞书群真实 `chat_id`（通常以 `oc_` 开头） | 飞书事件 `im.message.receive_v1` 的 `chat_id`；或 OpenClaw 日志中收到消息时的会话 ID | 用了群名称而不是 `chat_id`；把多个群写成同一个 ID |
| `sales-agent` / `ops-agent` / `finance-agent` | OpenClaw 中已存在的 `agentId` | `openclaw agents list` | 写了 persona 名称但不是 `agentId`；拼写不一致 |
| `bot-main` / `bot-finance` | `channels.feishu.accounts` 里的账号键名（`accountId`） | 你的 `openclaw.json` 中 `channels.feishu.accounts.<key>` | `bindings.match.accountId` 和 accounts 键名不一致 |

### 一份可直接照抄的“替换后”示例

假设你的真实值是：
- 销售群：`oc_9f31a...`
- 运营群：`oc_7b22d...`
- 财务群：`oc_3c88e...`
- Agent ID：`sales_agent`、`ops_agent`、`finance_agent`
- 账号：`bot_main`、`bot_finance`

那么路由就应写成：

```text
- oc_9f31a... -> sales_agent（accountId=bot_main）
- oc_7b22d... -> ops_agent（accountId=bot_main）
- oc_3c88e... -> finance_agent（accountId=bot_finance）
```

### 上线前 5 条强校验（避免配错）

1. `chat_id` 唯一：一个群只对应一条精确 binding。  
2. `agentId` 存在：`openclaw agents list` 能查到。  
3. `accountId` 对齐：`bindings.match.accountId` 必须等于 `channels.feishu.accounts` 的键名。  
4. 顺序正确：精确规则在前，兜底规则在后。  
5. 先验证再放量：先 canary 群验证通过，再全量。

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
