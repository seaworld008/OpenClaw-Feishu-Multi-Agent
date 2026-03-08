# V4.3.1 新机器快速启动 SOP

适用目标：
- 新 Linux / macOS / WSL2 机器
- 需要快速落地单群生产稳定版
- 目标效果：主管接单、运营两条、财务两条、主管最终收口

## 1. 复制与准备

1. 安装或同步本仓库 / skill。
2. 确认目标机满足：
   - `python3`
   - OpenClaw `2026.3.x`
   - 官方飞书插件 `@openclaw/feishu`
   - 可写 `~/.openclaw`
3. 准备好：
   - 团队群 `peerId`
   - `aoteman / xiaolongxia / yiran_yibao`
   - 三个机器人的 `appId / appSecret`

## 2. 应用配置

1. 用 [codex-prompt-templates-v4.3.1-single-group-production.md](/Volumes/soft/13-openclaw%20安装部署/3-openclaw-mulit-agents-skill/feishu-openclaw-multi-agent/OpenClaw-Feishu-Multi-Agent/skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md) 让 Codex 生成 patch。
2. 执行：

```bash
openclaw config validate
openclaw gateway restart
```

## 3. 初始化数据库与 watchdog

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_runtime.py \
  --db ~/.openclaw/workspace-supervisor_agent/.openclaw/team_jobs.db \
  init-db
```

按平台启用 watchdog：
- Linux / WSL2：`templates/systemd/v4-3-watchdog.service` + `v4-3-watchdog.timer`
- macOS：`templates/launchd/v4-3-watchdog.plist`

## 4. 先做一次会话卫生

首次上线、协议改动后、或从别的环境迁移过来时，先执行：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_hygiene.py \
  --home ~/.openclaw \
  --group-peer-id oc_f785e73d3c00954d4ccd5d49b63ef919 \
  --include-workers \
  --delete-transcripts
```

目的：
- 清空 `supervisor` 群会话
- 清空 `supervisor` hidden main 会话
- 清空 `ops / finance` 团队群会话
- 切断旧协议污染

## 5. 一次性初始化 worker

在团队群执行：

```text
@小龙虾找妈妈 WARMUP
@易燃易爆 WARMUP
```

预期：

```text
READY_FOR_TEAM_GROUP|agentId=ops_agent
READY_FOR_TEAM_GROUP|agentId=finance_agent
```

说明：
- 这是部署动作
- 不是最终用户的日常动作

## 6. 正式验收

在团队群发送：

```text
@奥特曼 启动本群高级团队模式：

我们要做一轮 3 天限时促销。
目标：卖出 10 单；预算不超过 5000 元；毛利率不低于 35%。

请你：
1) 让运营先发进度，再发活动打法结论
2) 让财务先发进度，再发预算与 ROI 结论
3) 最后由你统一给出一个简短执行方案
```

预期群内顺序：
1. 主管接单
2. 运营进度
3. 财务进度
4. 运营结论
5. 财务结论
6. 主管最终收口

不应出现：
- `ACK_READY`
- `REPLY_SKIP`
- `COMPLETE_PACKET`
- `WORKFLOW_INCOMPLETE`

## 7. canary 验收

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_canary.py \
  --db ~/.openclaw/workspace-supervisor_agent/.openclaw/team_jobs.db \
  --job-ref TG-20260307-031 \
  --session-root ~/.openclaw/agents \
  --require-visible-messages
```

通过标准：
- `status=done`
- `ops_agent` / `finance_agent` 都是 `done`
- 两边都有真实 `progressMessageId` 与 `finalMessageId`
- 群里没有内部协议泄漏

## 8. 日常维护

如果只是用户连续发新任务：
- 不需要 `WARMUP`
- 不需要手工清理 session

只有这些场景才需要重跑会话卫生：
1. 改了 `systemPrompt`
2. 改了 `callbackSessionKey`
3. 改了 `COMPLETE_PACKET` 字段
4. 发现 supervisor/worker 明显复用旧行为

推荐命令：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_hygiene.py \
  --home ~/.openclaw \
  --group-peer-id oc_f785e73d3c00954d4ccd5d49b63ef919 \
  --include-workers \
  --delete-transcripts
openclaw gateway restart
```
