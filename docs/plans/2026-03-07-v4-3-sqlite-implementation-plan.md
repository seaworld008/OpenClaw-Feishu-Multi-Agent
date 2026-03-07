# V4.3 SQLite Production Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现网 VMware OpenClaw 环境中落地 `V4.3` 单群生产版的最小可运行实现：不要求用户手输 `taskId`，由 supervisor 自动生成内部 `jobRef`，通过 SQLite 维护 activeJob/queue，并在 worker 可见发言后由 supervisor 最终统一收口。

**Architecture:** 继续沿用 `V4.2.1` 的可见协作链路，把真实任务状态迁移到 SQLite。supervisor 接到自然语言任务时先生成 `jobRef` 并落库，再做消息分类、派单、追收完成包和最终收口。worker 继续显式 `message` 发群消息，完成包写回 supervisor，由 supervisor 依据 SQLite 状态判断是否收口。

**Tech Stack:** OpenClaw `@openclaw/feishu`、Python `sqlite3`、Feishu 群聊、现网 `~/.openclaw/openclaw.json`

---

### Task 1: 核实现网接入点与工具可用性

**Files:**
- Modify: `/home/seaworld/.openclaw/openclaw.json`
- Inspect: `/home/seaworld/.openclaw/workspace-supervisor_agent/*`
- Test: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: 识别 supervisor/worker 当前可用工具与提示入口**

Run:
```bash
SSHPASS='123456' sshpass -e ssh -o StrictHostKeyChecking=no seaworld@192.168.180.131 \
  "python3 - <<'PY'
import json
from pathlib import Path
p=Path('/home/seaworld/.openclaw/openclaw.json')
data=json.loads(p.read_text())
print(data['tools'])
print(data['channels']['feishu']['accounts']['aoteman']['groups']['oc_f785e73d3c00954d4ccd5d49b63ef919']['systemPrompt'][:800])
PY"
```

Expected: 能确认当前单群团队仍使用 group 级 `systemPrompt`，工具集中包含 `group:sessions` 与 `group:messaging`。

**Step 2: 找出 agent 是否具备稳定本地执行入口**

Run:
```bash
SSHPASS='123456' sshpass -e ssh -o StrictHostKeyChecking=no seaworld@192.168.180.131 \
  "rg -n 'toolCall|name=\"(message|sessions_send|exec|shell|command)' /home/seaworld/.openclaw/agents/supervisor_agent/sessions/*.jsonl | tail -n 40"
```

Expected: 明确当前是否存在适合 agent 调用本地 Python 脚本的运行路径；如果没有，就不能把 SQLite 更新完全押给 agent 自己。

### Task 2: 先写 SQLite 状态层脚本与测试

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/v4_3_job_registry.py`
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/templates/v4-3-job-registry.example.sql`

**Step 1: 写 failing test，覆盖最小生产状态行为**

新增测试点：
- 自动生成 `jobRef`
- 同群只允许一个 `active` 任务
- 第二个任务进入 `queued`
- 补充说明归并到当前任务
- worker 完成包可写入 `progressMessageId/finalMessageId`

**Step 2: 运行测试，确认 RED**

Run:
```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py
```

Expected: 与 `v4_3_job_registry.py` 相关的测试失败，因为脚本尚不存在。

**Step 3: 写最小实现**

实现 CLI：
- `init-db`
- `start-job`
- `append-or-queue`
- `mark-worker-complete`
- `get-active`
- `ready-to-rollup`
- `close-job`

**Step 4: 再跑测试，确认 GREEN**

Run:
```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py
```

### Task 3: 在远端落库与初始化脚本

**Files:**
- Create: `/home/seaworld/.openclaw/state/team_jobs.db`
- Create: `/home/seaworld/.openclaw/state/v4_3_job_registry.py`

**Step 1: 上传脚本并初始化数据库**

Run:
```bash
scp skills/openclaw-feishu-multi-agent-deploy/scripts/v4_3_job_registry.py \
  seaworld@192.168.180.131:/home/seaworld/.openclaw/state/
ssh seaworld@192.168.180.131 \
  "python3 /home/seaworld/.openclaw/state/v4_3_job_registry.py init-db --db /home/seaworld/.openclaw/state/team_jobs.db"
```

Expected: `team_jobs.db` 生成成功，schema 完整。

### Task 4: 最小修改 supervisor/worker 运行逻辑

**Files:**
- Modify: `/home/seaworld/.openclaw/openclaw.json`
- Modify: `/home/seaworld/.openclaw/workspace-supervisor_agent/SOUL.md`
- Modify: `/home/seaworld/.openclaw/workspace-ops_agent/SOUL.md`
- Modify: `/home/seaworld/.openclaw/workspace-finance_agent/SOUL.md`

**Step 1: 主管接单逻辑接入 SQLite**
- 自然语言任务 -> 生成 `jobRef`
- 先写入 `jobs(active)`
- 若已存在 activeJob，则判定补充说明或入队
- 主管首发群消息改显示 `jobRef`

**Step 2: worker 完成包落 SQLite**
- worker 完成后向 supervisor 发结构化完成包
- supervisor 收到后调用脚本 `mark-worker-complete`
- 只有 `ready-to-rollup=true` 才最终收口

**Step 3: 配置 group session reset 策略**
- 增加 `session.resetByType.group.idleMinutes`
- 增加 `/reset` / `/new` 触发说明

### Task 5: 真实团队群验证

**Files:**
- Inspect: `/tmp/openclaw/openclaw-$(date +%F).log`
- Inspect: `/home/seaworld/.openclaw/state/team_jobs.db`

**Step 1: 用自然语言新任务验证**

在飞书群发送：
```text
@奥特曼 帮我做一份 4 月促销执行方案，运营和财务都参与。
```

Expected:
- 用户无需输入 `taskId`
- 主管首发 `【主管已接单｜TG-...】`
- ops/finance 各发进度摘要和结论摘要
- 主管最终收口

**Step 2: 用第二条独立任务验证队列**

在第一个任务未结束时发送：
```text
@奥特曼 再帮我起草 5 月预算看板。
```

Expected:
- 生成第二个 `jobRef`
- 进入 `queued`
- 不与当前 active 任务串线

**Step 3: 用补充说明验证归并**

发送：
```text
预算上限改成 18 万，并补一个直播渠道方案。
```

Expected:
- 归并到当前 activeJob
- 不新建任务

### Task 6: 回写仓库与文档

**Files:**
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md`
- Modify: `CHANGELOG.md`
- Modify: `VERSION`

**Step 1: 记录远端真实成功案例**
- 写清楚自然输入、自动 `jobRef`、队列、补充说明归并

**Step 2: 回归验证**

Run:
```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py
bash -n skills/openclaw-feishu-multi-agent-deploy/scripts/check_v3_dispatch_canary.sh
bash -n skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_1_team_canary.sh
bash -n skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_2_team_canary.sh
git diff --check
```
