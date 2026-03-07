# Changelog

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
- `v4_3_job_registry.py` 同步远端稳定版：
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
- 修复本地 `v4_3_job_registry.py` 与远端真实稳定版不一致，导致完成包可能因参数漂移卡死的问题

## [1.4.0] - 2026-03-07

### Added
- 新增 `V4.3.1` 单群生产稳定版文档：`references/codex-prompt-templates-v4.3.1-single-group-production.md`
- 新增 `V4.3.1` canary：`scripts/check_v4_3_canary.py`
- 新增 `V4.3.1` 交叉验证记录：`references/source-cross-validation-2026-03-07-v4-3-1.md`
- 新增 `V4.3.1` 实施计划：`docs/plans/2026-03-07-v4-3-1-single-group-production-stability.md`
- 新增自动化测试，覆盖：
  - `mark-dispatch`
  - `watchdog-tick`
  - `V4.3` / `V4.3.1` canary 成功路径

### Changed
- README、SKILL、验收清单统一把单群生产推荐版从 `V4.3` 升级为 `V4.3.1`
- `v4_3_job_registry.py` 升级为生产稳定版工具，新增：
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
- 新增配置生成脚本 `build_openclaw_feishu_snippets.py`，支持 plugin/core patch 生成。
- 新增参考文档：前提条件、升级回归手册、Codex 提示词模板、交叉验证记录、融合说明。
- 新增 `agents/openai.yaml` 作为 agent 元信息。

### Changed
- 默认路线升级为官方 `@openclaw/feishu`（`channel=feishu`）。
- 保留 `chat-feishu` 作为历史兼容路径。
- README 升级为可版本化仓库说明，并补齐执行入口与维护约定。

### Notes
- `references/generated/` 为本地临时产物目录，默认忽略提交。
