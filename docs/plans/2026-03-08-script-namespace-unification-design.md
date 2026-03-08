# Script Namespace Unification Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `OpenClaw-Feishu-Multi-Agent` 仓库建立统一、可长期维护的脚本命名体系，彻底移除失真的旧脚本名，收敛为 `core_* / v31_* / v431_* / v51_*` 三层模型。

**Architecture:** 脚本体系分成两层半。`core_*` 承载稳定的共用能力，例如状态机、会话清理、canary 解析、配置生成；`v31_* / v431_* / v51_*` 作为公开协议入口，表达不同交付主线的运行契约；模板、文档、远端部署、测试只引用版本入口或明确允许的公共 builder，不再直接引用历史遗留脚本名。所有旧脚本名一次性删除，不保留兼容别名。

**Tech Stack:** Python 3、SQLite、OpenClaw、Markdown 文档、`unittest`、`rg`

---

## 背景问题

当前仓库已经出现明显的命名债：

- `V5.1 Hardening` 一度复用带历史版本语义的运行时入口
- 公共配置生成器实际上同时服务 `V4.3.1` 和 `V5.1`
- `V3.1` 的跨群 canary 一度仍是 shell，而其余主线工具主要是 Python
- README、SKILL、模板、测试、systemd/launchd 模板、历史计划文档里混杂旧命名

这会持续制造两个问题：

1. 认知失真  
看到 `v4_3_*`，无法判断它是“只服务 `V4.3`”，还是“已经被 `V5.1` 复用了”。

2. 维护失真  
同一个公共基础脚本被多个主线复用，但文件名又绑在某个旧版本上，后续每次升级都容易做错依赖判断。

## 设计目标

- 仓库、文档、远端部署统一使用新命名
- 不保留旧脚本名兼容层
- 新命名能清晰表达“公共基础能力”和“版本协议入口”的边界
- 后续新增 `V5.2` 或 `V6` 时，不再复制整套基础设施
- 对客户和 Codex 来说，入口明确、可预测、可 grep

## 非目标

- 这次不做完整 Python package 化
- 这次不重构 OpenClaw 协议本身
- 这次不变更 `V3.1 / V4.3.1 / V5.1` 的业务语义

## 方案比较

### 方案 A：每个版本完整复制一套脚本

示例：
- `v31_job_registry.py`
- `v431_job_registry.py`
- `v51_job_registry.py`

优点：
- 版本感最直观

缺点：
- 重复代码会快速失控
- 修一个基础 bug 要改多份
- 很快再次形成维护债

结论：不推荐。

### 方案 B：`core_*` + 版本公开入口

示例：
- `core_job_registry.py`
- `v431_single_group_runtime.py`
- `v51_team_orchestrator_runtime.py`

优点：
- 公共能力和版本协议分层清楚
- 最适合当前 skill 仓库
- 后续扩版本时只增入口层，不重复核心实现

缺点：
- 需要一次性做完整迁移

结论：推荐。

### 方案 C：完整包化 + console entrypoints

优点：
- 最标准

缺点：
- 对当前仓库和远端现网太重
- 增加安装/分发复杂度

结论：暂不采用。

## 最终决策

采用方案 B：

- `core_*` 负责稳定公共能力
- `v31_* / v431_* / v51_*` 负责对外协议入口
- 模板、文档、远端部署、测试只使用新入口
- 旧脚本名一次性删除

## 命名规则

### 公共基础层

只放不绑定单一版本的能力：

- `core_feishu_config_builder.py`
- `core_job_registry.py`
- `core_session_hygiene.py`
- `core_canary_engine.py`

规则：
- 小写 + 下划线
- 名称表达“能力”而不是“历史来源”
- 允许被多个主线复用

### 版本公开层

按“主线版本 + 场景”命名：

- `v31_cross_group_canary.py`
- `v431_single_group_runtime.py`
- `v431_single_group_hygiene.py`
- `v431_single_group_canary.py`
- `v51_team_orchestrator_runtime.py`
- `v51_team_orchestrator_hygiene.py`
- `v51_team_orchestrator_canary.py`
- `v51_team_orchestrator_deploy.py`

规则：
- 版本号只保留主线表达，不带点
- 名称必须体现部署场景
- 对用户和文档暴露的脚本优先使用版本入口，而不是 `core_*`

## 统一脚本清单

| 统一脚本 | 分层 | 说明 |
|---|---|---|
| `core_feishu_config_builder.py` | `core_*` | 公共生成器，负责 patch 与 runtime manifest 产出 |
| `core_job_registry.py` | `core_*` | 核心状态机，版本无关 |
| `core_session_hygiene.py` | `core_*` | 通用会话清理引擎 |
| `core_canary_engine.py` | `core_*` | 共享日志 / session / SQLite canary 解析逻辑 |
| `v31_cross_group_canary.py` | `v31_*` | `V3.1` 跨群验收入口，统一为 Python |
| `v431_single_group_runtime.py` | `v431_*` | `V4.3.1` 单群运行时入口 |
| `v431_single_group_hygiene.py` | `v431_*` | `V4.3.1` 单群会话卫生入口 |
| `v431_single_group_canary.py` | `v431_*` | `V4.3.1` 单群验收入口 |
| `v51_team_orchestrator_runtime.py` | `v51_*` | `V5.1` team orchestrator 运行时入口 |
| `v51_team_orchestrator_hygiene.py` | `v51_*` | `V5.1` team orchestrator 会话卫生入口 |
| `v51_team_orchestrator_canary.py` | `v51_*` | `V5.1` team orchestrator 验收入口 |
| `v51_team_orchestrator_deploy.py` | `v51_*` | `V5.1` team orchestrator 交付入口 |

新增公开入口：

- `v431_single_group_runtime.py`
- `v431_single_group_hygiene.py`
- `v51_team_orchestrator_runtime.py`
- `v51_team_orchestrator_hygiene.py`
- `v51_team_orchestrator_canary.py`

## 入口策略

### `V3.1`

- 公开入口以跨群 canary 为主
- 若后续有必要再补 `v31_cross_group_runtime.py`
- 当前优先把 shell canary 统一为 Python

### `V4.3.1`

- 文档和模板统一使用：
  - `v431_single_group_runtime.py`
  - `v431_single_group_hygiene.py`
  - `v431_single_group_canary.py`

### `V5.1`

- 文档和模板统一使用：
  - `v51_team_orchestrator_runtime.py`
  - `v51_team_orchestrator_hygiene.py`
  - `v51_team_orchestrator_canary.py`
  - `v51_team_orchestrator_deploy.py`

## 行业最佳实践对齐

这套设计与两类最佳实践一致：

1. Python 命名与 CLI 分层  
公共实现不应继续背着失真的版本名字；公开入口应表达稳定契约，而不是泄漏内部历史。

2. 平台/协议分层  
真正会变化的是 `V3.1 / V4.3.1 / V5.1` 的交付口径；真正应复用的是状态机、会话清理、生成器、日志校验。

## 文档与模板策略

这次是一次性切断旧名，因此：

- README、SKILL、模板、参考文档、客户交付模板全部改新名
- 测试常量和断言全部改新名
- systemd/launchd 模板里的 `ExecStart` 全部改新名
- 远端部署脚本和 runtime manifest 全部改新名

### 历史文档策略

为了与“直接切断旧名”保持一致，这次连历史计划文档也一并更新脚本路径，不保留旧名引用。

代价：
- 旧计划文档的时间线仍然保留，但脚本名会反映当前统一命名

收益：
- 仓库整体 grep 干净
- 不会再出现“某份文档到底是不是旧入口”的歧义

## 验收标准

重构完成后必须满足：

- 仓库脚本目录只保留 `core_* / v31_* / v431_* / v51_*` 新命名
- README、SKILL、模板、测试、部署脚本、远端运行时不再引用旧名
- `V3.1 / V4.3.1 / V5.1` 的专项测试和全量测试全部通过
- `git diff --check` 通过

## 迁移顺序

推荐顺序：

1. 先加测试，禁止旧名继续出现
2. 新建 `core_*` 与 `v31/v431/v51_*` 文件
3. 更新测试常量
4. 更新 README / SKILL / 模板 / 交付文档
5. 删除旧脚本
6. 最后切远端测试机

## 风险与缓解

风险：
- `V4.3.1` 与 `V5.1` 文档命令量很大，替换不全容易留死角
- 远端部署脚本可能仍然写死旧路径
- 旧 shell canary 转 Python 时输出兼容性可能变化

缓解：
- 先写“仓库内禁止旧名”测试
- `rg` 全仓扫描旧名
- 先本地全量验证，再碰远端
