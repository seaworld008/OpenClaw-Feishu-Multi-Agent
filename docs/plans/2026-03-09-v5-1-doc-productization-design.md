# V5.1 Documentation Productization Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把当前 `V5.1 Hardening` 的用户文档体系升级成真正可交付的产品文档：用户只看主线入口，就能理解目标效果、架构、实现原理、真实配置、真实 Codex 提示词，以及后续扩容/裁剪操作，不再在不同文件之间切换两套 schema。

**Architecture:** 保留现有文件分工，但收敛成一套单一口径。`README.md` 负责导航和统一入口，`SKILL.md` 负责交付约束与运行模型，`references/codex-prompt-templates-v51-team-orchestrator.md` 升级为完整产品手册，覆盖效果、架构、配置、实现原理、真实数据和扩展操作。`references/客户首次使用真实案例.md`、`references/V5.1-新机器快速启动-SOP.md`、`references/客户首次使用信息清单.md`、`references/客户首次使用-Codex提示词.md` 分别承担真实配置案例、首次部署 SOP、输入收集清单和面向 Codex 的执行提示词，全部统一为 `roleCatalog + teams(profileId + override)` canonical schema。

**Tech Stack:** Markdown、JSON、JSONC、Python `unittest`

---

## 背景与问题

当前 V5.1 文档体系虽然已经有主入口、有真实双群数据、有首次使用文档和长版模板，但还存在三类问题：

1. 主线 schema 不完全统一：部分文件说明 `roleCatalog + teams(profileId + override)`，但长 JSON 仍是 inline `teams`.
2. 用户视角不连续：有真实数据，但“从效果到架构到配置到落地到扩展”的阅读路径不完整。
3. 扩展操作缺少显式说明：新增群、新增机器人、给群加 worker、删 worker、删群这些真实变更场景，没有产品化说明。

## 目标状态

交付完成后，用户只需要顺序阅读：

1. `README.md`
2. `references/codex-prompt-templates-v51-team-orchestrator.md`
3. `references/客户首次使用信息清单.md`
4. `references/客户首次使用真实案例.md`
5. `references/客户首次使用-Codex提示词.md`
6. `references/V5.1-新机器快速启动-SOP.md`

就能完成下面 6 件事：

1. 理解 `V5.1 Hardening` 最终上线效果。
2. 理解 `roleCatalog + teams(profileId + override)` 的 canonical schema。
3. 理解 runtime manifest / hidden main / SQLite / watchdog 的实现原理。
4. 直接复制真实案例并替换真实值完成第一次配置。
5. 直接复制真实 Codex 提示词做生产交付。
6. 明确如何做扩容、裁剪和回滚。

## 设计原则

### 1. 单一 schema

所有主线文档统一采用：

- 根层 `roleCatalog`
- team 层 `profileId + agentId + override`
- `visibleLabel` 作为显示层单一来源

旧 inline `teams` 只作为兼容说明，不再出现在用户直接复制的主示例里。

### 2. 单一阅读路径

每份文档都只承担一种角色：

- `README.md`：总入口与导航
- `SKILL.md`：交付约束与运行模型
- 长版 `codex-prompt-templates-v51-team-orchestrator.md`：产品手册和真实生产模板
- `客户首次使用真实案例.md`：真实值案例
- `客户首次使用-Codex提示词.md`：操作型提示词
- `客户首次使用信息清单.md`：信息采集清单
- `V5.1-新机器快速启动-SOP.md`：新机器从 0 到上线

### 3. 真实数据和真实提示词保留

主线产品手册和真实案例继续保留：

- 当前正式双群 `peerId`
- 三个正式机器人 `accountId / appId / appSecret`
- teamKey
- hidden main
- SQLite 路径
- service / timer / launchd 命名
- 真实 supervisor / worker systemPrompt

### 4. 扩展操作显式化

文档必须单独说明以下真实运维动作：

- 新增一个群
- 新增一个机器人账号
- 给现有群增加一个 worker
- 从现有群移除一个 worker
- 下线一个群
- 替换单个角色的 `systemPrompt / visibleLabel / responsibility`

## 文档结构设计

### README

新增或强化：

- “如果只看一个文件，先看哪一个”
- V5.1 统一入口
- 用户上手顺序
- `V5.1 Hardening` 正式推荐模板说明

### 长版产品手册

重构成以下章节：

1. 你将得到什么效果
2. 统一入口与 canonical schema
3. 架构与实现原理
4. 当前正式生产基线（真实双群、真实机器人、真实运行时命名）
5. 统一入口配置详解
6. 真实完整输入示例
7. 真实 supervisor / worker 提示词
8. Codex 真实交付提示词
9. 扩容与裁剪操作手册
10. 文件与产物清单

### 首次使用真实案例

保持“真实可替换案例”的定位，但内容改为：

- 直接给出 canonical schema 大 JSON
- 配套解释每一段的作用
- 单独列出“替换哪些值”
- 单独列出“如何改成 1 个群 / 新增群 / 加 worker / 删 worker”

### 首次使用 Codex 提示词

拆成多个可直接复制的真实提示词：

- 首次交付
- 新增一个群
- 新增一个机器人账号
- 给现有群新增 worker
- 从现有群删 worker
- 下线一个群

### 新机器 SOP

保留安装和上线步骤，但把长 JSON 示例切到 canonical schema，并明确引用统一入口模板与真实案例。

## 测试策略

回归测试要覆盖：

1. 主线用户文档都出现 `roleCatalog` 和 `profileId`。
2. 用户直接复制的文档不再以内联 `teams` 作为主示例。
3. 产品手册明确覆盖扩展操作。
4. README 仍然链接全部用户入口。
5. 真实案例和真实提示词仍保留真实双群、真实机器人和真实 app 数据。
