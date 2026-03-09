# V5.1 Documentation Productization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把 `V5.1 Hardening` 用户文档重构成单一 canonical schema、单一阅读路径、带真实案例和真实提示词的产品化文档体系。

**Architecture:** 先在测试中定义“V5.1 文档必须统一为 `roleCatalog + teams(profileId + override)`，并显式覆盖扩容/裁剪操作”的契约，再重写主线文档。文档层采用“总入口 + 长版产品手册 + 首次使用子文档”的结构，确保用户从介绍效果到配置落地到扩展操作都能闭环。

**Tech Stack:** Markdown、JSON、JSONC、Python `unittest`

---

### Task 1: 写失败的文档契约测试

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: 增加 RED 测试**

新增断言，要求：

- `客户首次使用真实案例.md` 出现 `"roleCatalog"` 和 `"profileId"`
- `V5.1-新机器快速启动-SOP.md` 出现 `roleCatalog` 和 `profileId`
- `codex-prompt-templates-v51-team-orchestrator.md` 明确包含“新增一个群 / 新增一个机器人账号 / 给现有群增加一个 worker / 从现有群移除一个 worker / 下线一个群”
- `客户首次使用-Codex提示词.md` 包含多种操作型真实提示词

**Step 2: 跑测试确认 RED**

Run:

```bash
python3 -m unittest \
  feishu-openclaw-multi-agent/OpenClaw-Feishu-Multi-Agent/tests/test_openclaw_feishu_multi_agent_skill.py
```

Expected: 新增文档断言失败。

### Task 2: 重写 README 和 SKILL 主入口

**Files:**
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`

**Step 1: 强化统一入口**

补充：

- V5.1 唯一推荐入口
- 用户阅读顺序
- 统一入口模板和长版产品手册

**Step 2: 保持运行模型说明**

保留：

- runtime manifest
- hidden main
- SQLite
- watchdog

### Task 3: 重写长版产品手册

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md`

**Step 1: 重构目录**

改成：

- 效果
- 架构
- 实现原理
- 统一入口配置
- 真实双群案例
- 真实提示词
- 扩容/裁剪手册
- 文件清单

**Step 2: 统一 schema**

全部改为 canonical `roleCatalog + teams(profileId + override)`。

### Task 4: 重写首次使用子文档

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用-Codex提示词.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用信息清单.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md`

**Step 1: 统一为 canonical schema**

所有给用户复制的大 JSON 全改为 `roleCatalog + profileId`。

**Step 2: 增加操作场景**

补充：

- 新增群
- 新增账号
- 新增 worker
- 删除 worker
- 删除群

**Step 3: 保留真实值**

继续保留：

- 正式双群 `peerId`
- 三个正式机器人
- `appId / appSecret`
- hidden main
- SQLite / watchdog 命名

### Task 5: 跑回归测试和格式校验

**Files:**
- Modify: none unless verification reveals gaps

**Step 1: 跑完整测试**

Run:

```bash
python3 -m unittest \
  feishu-openclaw-multi-agent/OpenClaw-Feishu-Multi-Agent/tests/test_openclaw_feishu_multi_agent_skill.py
```

**Step 2: 跑 diff 校验**

Run:

```bash
git -C feishu-openclaw-multi-agent/OpenClaw-Feishu-Multi-Agent diff --check
```

Expected: 全部通过。
