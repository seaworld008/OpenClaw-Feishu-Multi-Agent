# Changelog

## [1.6.3] - 2026-03-11

### Changed
- `V5.1 Hardening` 正式支持 `parallel stage + publishOrder`：
  - worker 可并行分析
  - 群内消息统一由 `controller -> outbox -> sender` 按顺序发布
- worker 协议收口为 `draft-only callback`：
  - 主协议提交 `progressDraft / finalDraft / summary / details / risks / actionItems`
  - worker 不再直接向群发送 `progress/final`
  - 完整 callback 结束标记改为 `CALLBACK_OK`
- 统一入口模板、README、SKILL、SOP 与交付模板同步切到最新并行控制面模型。
- 新增 SeaWorld 双群并行验收记录：
  - `docs/plans/2026-03-11-seaworld-parallel-validation.md`
- `VERSION` 与 README 当前版本头同步到 `1.6.3 / 2026-03-11`。

### Fixed
- 修复 parallel workflow 建单时 worker metadata 退化成纯 `agentId`，导致远端错误 `accountId` 的问题。
- 修复外部群 worker 与 controller/outbox 双写可见消息导致的重复发送问题。
- 修复 gateway 重启后持续恢复历史 `delivery-queue` 坏消息的噪音问题。
- 修复 worker 提前提交空 `finalText` callback 导致 stage 卡死的问题。

## [1.6.2] - 2026-03-09

### Changed
- README 和 `openclaw-feishu-multi-agent-deploy/SKILL.md` 进一步收口为统一入口口径：
  - 主线只强调 `accounts + roleCatalog + teams`
  - `channels.feishu`、`bindings`、必要的 `agents.list` 和 `v51 runtime manifest` 明确为 builder 派生产物
  - `single-bot / multi-bot` 降级为部署拓扑背景，不再像第二套并列配置入口
- README 中的“飞书与 OpenClaw 信息采集”与“真实 Codex 提示词”统一到 `V5.1 Hardening` 双群 team-orchestrator 结构。
- `VERSION` 与 README 当前版本头同步到 `1.6.2 / 2026-03-09`。

### Fixed
- 修复 README 前半段仍可能把用户带回旧 route-first 心智的问题。
- 修复公开入口文档与当前版本元信息不完全同步的问题。

## [1.6.1] - 2026-03-08

### Added
- 新增 `V5.1 Hardening` 设计与实施文档：
  - `docs/plans/2026-03-08-v5-1-hardening-design.md`
  - `docs/plans/2026-03-08-v5-1-hardening-implementation.md`
- `v5 runtime manifest` 新增 `Deterministic Orchestrator` 控制面元数据：
  - `orchestratorVersion`
  - `runtime.controlPlane.commands.startJob`
  - `runtime.controlPlane.commands.nextAction`
  - `runtime.controlPlane.commands.buildRollupContext`
  - `runtime.controlPlane.commands.readyToRollup`

### Changed
- `core_job_registry.py` 升级为 `V5.1 Hardening` 控制面，新增：
  - `start-job-with-workflow`
  - `get-next-action`
  - `build-rollup-context`
- `ready-to-rollup` 从“按已有 participant 推断”改为“按显式状态机 `next_action=rollup` 判断”。
- README、SKILL、`V5` 交付模板、输入模板和 JSONC 快照统一升级到 `V5.1 Hardening` 口径，明确 `LLM 负责内容，代码负责流程`。

### Fixed
- 修复 `V5` 主管在 worker 完成后仍可能直接 `NO_REPLY`、漏派下一阶段 worker 的结构性问题。
- 修复旧 `team_jobs.db` 升级到 `V5.1 Hardening` 时缺少状态机字段的问题。

## [1.6.0] - 2026-03-08

### Added
- 新增 `V5 Team Orchestrator` 的生产级双群基线文档与模板，正式固化：
  - 内部团队群 `oc_f785e73d3c00954d4ccd5d49b63ef919`
  - 外部团队群 `oc_7121d87961740dbd72bd8e50e48ba5e3`
  - 三个正式机器人 `aoteman` / `xiaolongxia` / `yiran_yibao`
- 新增 `v5 runtime manifest` 作为标准交付物，用于 team 级 hidden main、watchdog、session hygiene 和 canary 落地。

### Changed
- README、SKILL、`deployment-inputs.example.yaml`、`V5` 交付模板统一升级到 `V5 Team Orchestrator` 主线口径：
  - 当前主线版本收敛为 `V3.1`、`V4.3.1`、`V5`
  - `V5` 明确采用 `One Team = 1 Supervisor + N Workers`
  - 生成器输出 patch + summary + runtime manifest
- `V5` 文档与 JSONC 快照对齐当前脚本产物，补齐 hidden main、teamKey、双群与 Codex 真实交付入口。

### Fixed
- 修复 `V5` 文档仍停留在骨架、缺少真实双群信息和运行时产物说明的问题。
- 修复 README 版本号与 `VERSION` 文件不一致的问题。

## [1.5.2] - 2026-03-07

### Added
- 新增 `templates/openclaw-v4-3-1-single-group-production.example.jsonc`，提供 `V4.3.1` 单群生产稳定版的去敏 `openclaw.jsonc` 参考快照。

### Changed
- README 在 `V4.3.1` 章节补充 JSONC 配置快照入口，便于直接对照字段结构。

### Fixed
- 修复仓库只有长文档和局部 route 示例、缺少一份完整去敏 `openclaw.json` 参考快照的问题。

## [1.5.1] - 2026-03-07

### Added
- 新增 `scripts/v431_single_group_hygiene.py`，用于首次上线、协议变更或脏上下文后，一次性清理 `supervisor group/main + worker group` 会话。
- 新增 [V4.3.1 新机器快速启动 SOP](skills/openclaw-feishu-multi-agent-deploy/references/v4-3-1-quick-start.md)，统一 `init-db -> hygiene -> WARMUP -> canary` 的最小闭环。

### Changed
- `V4.3.1` 主文档、README、SKILL、上线手册和验收清单统一接入会话卫生流程。
- `V4.3.1` 真实通过样板升级为 `TG-20260307-031`，并同步最新 `messageId` 与最终收口证据。
- `deployment-inputs.example.yaml` 增加 `runtime_hygiene` 段，明确何时需要执行会话卫生脚本。

### Fixed
- 修复仓库只记录了人工恢复经验、没有把“快速启动 + 会话卫生”固化为标准交付步骤的问题。
- 修复 `V4.3.1` 主文档和 README 仍引用旧成功样板 `TG-20260307-029` 的问题。

## [1.5.0] - 2026-03-07

### Added
- 新增跨平台交付材料：
  - `templates/launchd/v4-3-watchdog.plist`
  - `templates/windows/wsl.conf.example`
  - `references/windows-wsl2-deployment-notes.md`
  - `references/source-cross-validation-2026-03-07-platforms.md`
- 新增自动化测试，覆盖：
  - README / SKILL / `V4.3.1` 文档中的平台矩阵
  - `launchd` watchdog 模板存在性与关键字段
  - `WSL2` 路线说明与 `wsl.conf` 示例

### Changed
- README、SKILL、`V4.3.1` 主文档统一补充平台兼容策略：
  - Linux：`systemd --user`
  - macOS：`launchd`
  - Windows：默认推荐 `WSL2`
- `deployment-inputs.example.yaml` 增加 `platform` / `service_manager` / watchdog 平台参数。
- 验收清单与前置条件、上线升级手册新增平台分支要求，不再把 Linux 运维命令写成默认唯一答案。
- `V4.3.1` 的 Codex 真实交付模板不再使用缩减版，已补回完整输入、约束、部署后测试顺序、预期群聊效果和队列/恢复测试说明。

### Fixed
- 修复仓库交付材料明显偏 Linux、对 macOS 和 Windows 客户缺少正式运维路径的问题。
- 修复单群生产版虽然架构已稳定，但文档仍无法直接指导 macOS / WSL2 客户部署 watchdog 的问题。

## [1.4.1] - 2026-03-07

### Changed
- `V4.3.1` 主模板改为以远端真实跑通协议为准：
  - 主管群会话只负责接单与派单
  - 隐藏控制会话 `agent:supervisor_agent:main` 负责消费 `COMPLETE_PACKET`、推进 SQLite 状态机并最终收口
  - worker 结论摘要允许多行完整输出，不再压成一句话
- README、SKILL、验收清单统一补充：
  - 群里禁止泄漏 `ACK_READY / REPLY_SKIP / COMPLETE_PACKET`
  - `V4.3.1` 的可见消息固定为 6 类
  - `TG-20260307-029` 作为真实通过样板
- `v431_single_group_runtime.py` 同步远端稳定版：
  - `mark-worker-complete` 支持 `account-id/role` 缺省兜底
  - 与现网 SQLite 状态机行为对齐

### Added
- `V4.3.1` 交叉验证记录补充真实成功 run：`TG-20260307-029`
- 新增测试覆盖：
  - `mark-worker-complete` 缺省参数兜底
  - `V4.3.1` 文档中的 hidden main / `NO_REPLY` / 真实 canary 样板
  - `V4.3` canary 对群会话内部协议外泄的自动拦截

### Fixed
- 修复本地仓库 `V4.3.1` 文档仍保留旧协议（`REPLY_SKIP`、短字段限制、旧可见结论约束）的问题
- 修复本地 `v431_single_group_runtime.py` 与远端真实稳定版不一致，导致完成包可能因参数漂移卡死的问题

## [1.4.0] - 2026-03-07

### Added
- 新增 `V4.3.1` 单群生产稳定版文档：`references/codex-prompt-templates-v4.3.1-single-group-production.md`
- 新增 `V4.3.1` canary：`scripts/v431_single_group_canary.py`
- 新增 `V4.3.1` 交叉验证记录：`references/source-cross-validation-2026-03-07-v4-3-1.md`
- 新增 `V4.3.1` 实施计划：`docs/plans/2026-03-07-v4-3-1-single-group-production-stability.md`
- 新增自动化测试，覆盖：
  - `mark-dispatch`
  - `watchdog-tick`
  - `V4.3` / `V4.3.1` canary 成功路径

### Changed
- README、SKILL、验收清单统一把单群生产推荐版从 `V4.3` 升级为 `V4.3.1`
- `v431_single_group_runtime.py` 升级为生产稳定版工具，新增：
  - `mark-dispatch`
  - `get-job`
  - `list-queue`
  - `watchdog-tick`
  - 更稳的 stale recovery / ready-to-rollup 视图
- `V4.3` 文档改为基础蓝图，并新增 `V4.3.1` 作为正式稳定版入口

### Fixed
- 修复单群生产版只有状态层蓝图、没有初始化、watchdog 和自动验收的问题
- 修复 `V4.3` registry 只能建档、不能稳定表达 dispatch / stale / queue 状态的问题
- 修复仓库缺少 `V4.3` 生产闭环验收脚本的问题

## [1.3.0] - 2026-03-07

### Added
- 新增 `V4.3` 单群生产版蓝图：`references/codex-prompt-templates-v4.3-single-group-production.md`
- 新增 `V4.3` SQLite 任务状态表示例：`templates/v4-3-job-registry.example.sql`
- 新增 `V4.3` 交叉验证记录：`references/source-cross-validation-2026-03-07.md`
- 新增设计记录：`docs/plans/2026-03-07-v4-3-single-group-production-design.md`
- 新增自动化测试，覆盖 `V4.3` 文档的 `jobRef`、`activeJob/queuedJobs` 和单群唯一活跃任务索引

### Changed
- README 版本地图升级为 `V1 / V2 / V3.1 / V4 / V4.1 / V4.2 / V4.2.1 / V4.3`
- README、SKILL、验收清单统一拆分：
  - 单群演示推荐：`V4.2.1`
  - 单群生产推荐：`V4.3`
- README 补充“真实客户不应手工输入 taskId”的生产判断、`jobRef` 自动生成、activeJob 队列和状态层建议

### Fixed
- 修复仓库单群路线只强调演示链路、没有把“真实长期上线”单独建模的问题
- 修复 README 与 Skill 缺少“一个活跃任务 + 队列 + 外部状态层”生产约束的问题

## [1.2.0] - 2026-03-07

### Added
- 新增 `V4.2.1` 单群团队可见协作版文档：`references/codex-prompt-templates-v4.2.1-single-group-team.md`
- `check_v4_2_team_canary.sh` 新增 `--require-visible-messages`，可校验 worker 是否产出真实群发 `messageId`
- 新增自动化测试，覆盖：
  - `VISIBLE_MESSAGE_MISSING`
  - `--require-visible-messages` 成功路径
  - `V4.2.1` 文档中的真实成功样板与显式 `message` 规则

### Changed
- README、SKILL、验收清单统一把单群当前推荐版切换为 `V4.2.1`
- README 新增 `V4.2.1` 版本说明、真实跑通样板 `team-v4-2-015`、群内可见协作验收方式
- `V4.2.1` 正式要求 worker 在详细任务阶段显式调用 `message` 工具群发短摘要，再回主管交付详细结果

### Fixed
- 修复单群团队模式中“控制面成功但群里看不到其他机器人发言”的交付缺口
- 修复验收脚本只能校验派单链路、不能校验 worker 真实群发消息的问题

## [1.1.3] - 2026-03-07

### Added
- 为 `V4.2` 增加基于远端 VMware 实测沉淀的两类运行前提：
  - 群级 prompt 变更后必须 fresh session（优先 `/reset`）
  - `supervisor_agent` 工作区必须完成生产化初始化，不能保留默认 `BOOTSTRAP.md`
- 新增自动化测试，覆盖：
  - `V4.2` 文档要求 fresh session
  - `V4.2` 文档要求生产化 workspace 初始化
  - `V4.2` 文档要求使用官方完整 `sessionKey` 格式
  - `check_v4_2_team_canary.sh` 在无 `rg` 环境下的回退执行

### Changed
- `V4.2` 主文档、README、SKILL、验收清单统一补充：
  - stale group session 的恢复步骤
  - workspace bootstrap 残留的排障规则
  - 飞书单群 `sessionKey` 必须使用 `agent:<agentId>:feishu:group:<peerId>`
- `check_v4_2_team_canary.sh` 改为在缺少 `rg` 时自动回退到 Python 检索，不再依赖目标机器预装 ripgrep。

### Fixed
- 修复 `V4.2` 在 fresh session 后仍可能被默认 workspace bootstrap 稀释掉团队调度行为的问题。
- 修复 `V4.2` 文档对固定 `sessionKey` 格式约束不够硬，导致主管错误使用 `feishu:chat:...` 并触发 `No session found` 的问题。
- 修复远端验收脚本在没有 `rg` 的客户环境下会假失败的问题。

## [1.1.2] - 2026-03-07

### Added
- 为 `V4.2` 增加基于远端实测的正式运行策略说明：`ACK timeoutSeconds=15 -> 详细任务 timeoutSeconds=0 -> sessions_history / worker session jsonl 二次收口`。
- 新增自动化测试，覆盖 `accepted + worker evidence` 的 fire-and-forget 成功路径。

### Changed
- `V4.2` 主文档、README、SKILL、验收清单统一升级为：
  - 全局 `messages.groupChat.mentionPatterns` + 主管级 `agents.list[].groupChat.mentionPatterns`
  - ACK / 正文双阶段派单
  - `sessions_history` 二次收口
- `V4`、`V4.1` 文档补充“历史/过渡版本”提示，明确单群生产优先使用 `V4.2`。
- 交叉验证记录补充 OpenClaw 官方 `timeoutSeconds=0 -> accepted` 语义与远端 VMware 运行结论。

### Fixed
- 修复 `V4.2` 文档仍停留在“只写 ACK 双阶段建议、未写 fire-and-forget / sessions_history 实施细节”的缺口。
- 修复 `V4.2` 文档未明确要求全局 `messages.groupChat.mentionPatterns` 兜底的问题。

## [1.1.1] - 2026-03-06

### Added
- 新增 `references/source-cross-validation-2026-03-06.md`，记录 `V4.2` 单群团队模式的最新交叉验证结论。
- `V4.2` canary 新增两类状态识别：
  - `TIMEOUT_BUT_WORKER_DELIVERED`
  - `TRIGGER_MISS_ON_MENTION_OR_FORMAT_WRAP`

### Changed
- `V4.2` 主管提示词与交付模板新增：
  - `mentionPatterns` 兜底
  - `PLAIN_TEXT` / 代码块包裹兼容
  - `timeout` 二次判定
  - ACK -> 正文 的双阶段派单建议
- README、SKILL、验收清单同步补齐 `V4.2` 的 timeout / NO_REPLY / mention 处理口径。

### Fixed
- 修复 `V4.2` canary 无法正确识别“被提及后落入 NO_REPLY”的问题。
- 修复 `V4.2` canary 未单独分类“timeout 但 worker 实际已执行”这一现场高频状态的问题。

## [1.1.0] - 2026-03-06

### Added
- 新增 `V4.2` 单群团队最佳实践方案，明确采用 `send-first probe`、展示层/控制面分离，并补齐完整交付提示词。
- 新增 `scripts/check_v4_2_team_canary.sh`，用于单群团队模式的真实派单链路校验，并支持 `SEND_PATH_AVAILABLE_BUT_LIST_MISS` 分类。
- 新增 `V4.2` 相关自动化测试，覆盖真实派单成功与 `list-miss / send-path` 分支。

### Changed
- README 升级为 `V1 / V2 / V3.1 / V4 / V4.1 / V4.2` 版本化说明，明确跨群与单群的推荐路线。
- 单群版本文档统一为 `send-first probe` 口径，修复 `sessions_list` 与 `sessions_spawn` 先后顺序的自相矛盾表述。
- `V4 / V4.1 / V4.2` 的验收与故障排查说明统一强调：
  - `session jsonl > gateway log`
  - 公开群里的 `@其他机器人` 仅作为展示层
  - `tool_call_required`、`warmup_required`、`SEND_PATH_AVAILABLE_BUT_LIST_MISS` 需分类处理
- 验收清单补齐 `V4 / V4.1 / V4.2` 的单群验证项，包括真实派单证据、互审约束、Feishu `sessions_spawn` 限制处理。

### Fixed
- 修复单群版本中“已经声明采用 send-first，但仍要求先 `sessions_spawn`”的错误引导。
- 修复 `V4.1` / `V4.2` 在首次上线和失败分流场景中的提示词不一致问题。
- 修复单群 canary 与文档之间的版本入口不一致问题。

## [1.0.0] - 2026-03-04

### Added
- 新增交付级 Skill 文档，覆盖 single-bot / multi-bot、incremental / full_replace、canary 发布与回滚要求。
- 新增模板集合：部署输入、单/多 bot 路由、brownfield 变更计划、验收检查清单。
- 新增配置生成脚本 `core_feishu_config_builder.py`，支持 plugin/core patch 生成。
- 新增参考文档：前提条件、升级回归手册、Codex 提示词模板、交叉验证记录、融合说明。
- 新增 `agents/openai.yaml` 作为 agent 元信息。

### Changed
- 默认路线升级为官方 `@openclaw/feishu`（`channel=feishu`）。
- 保留 `chat-feishu` 作为历史兼容路径。
- README 升级为可版本化仓库说明，并补齐执行入口与维护约定。

### Notes
- `references/generated/` 为本地临时产物目录，默认忽略提交。
