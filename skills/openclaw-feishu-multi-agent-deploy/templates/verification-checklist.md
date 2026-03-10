# 验收清单

## A. 变更前
- [ ] `openclaw --version` 已记录
- [ ] `openclaw plugins list` 已确认 `@openclaw/feishu`
- [ ] 配置文件已备份（含时间戳）
- [ ] 飞书权限和事件订阅已完成审批
- [ ] 已确认目标平台：`Linux` / `macOS` / `WSL2`；若客户是 Windows，已明确记录采用 `WSL2` 还是接受原生偏差
- [ ] 已确认 service manager：`systemd --user` / `launchd` / `manual`

## B. 配置校验
- [ ] `openclaw config validate` 通过
- [ ] `bindings` 顺序正确（精确在前、兜底在后）
- [ ] `defaultAccount` 已设置且存在于 `accounts`
- [ ] 无冲突规则（同一 `channel/accountId/peer.id` 未映射到多个 agent）
- [ ] 未存在指向已删除 agent 的陈旧 bindings

## C. 功能验证
- [ ] 私聊路由正确（至少 1 条）
- [ ] 每个目标群路由正确
- [ ] requireMention=true 的群必须 @ 才触发
- [ ] requireMention=false 的群不 @ 可触发（且权限已具备）
- [ ] 多 Bot 群未出现重复触发
- [ ] agent 身份（名称/角色行为）符合目标职责
- [ ] 跨群上下文隔离正常（无串内容）
- [ ] （V5.1）每个 team 都有独立 `teamKey`、hidden main、workspace、SQLite 和 watchdog
- [ ] （V5.1）supervisor 群级可见消息统一通过 `controller -> outbox -> sender` 落地，不再依赖普通 assistant 文本直出
- [ ] （V5.1）worker 的两条群内可见消息都带固定标题：`【角色进度｜TG-xxxx】`、`【角色结论｜TG-xxxx】`，没有丢 `jobRef`
- [ ] （V5.1）supervisor 最终统一收口是完整结构化方案，包含 `任务主题`、各角色结论、`联合风险与红线`、`明日三件事`
- [ ] （V5.1）同一 `jobRef` 在群里只出现 1 次 `【主管最终统一收口｜TG-xxxx】`，没有重复收口
- [ ] （V5.1）若主管群 session 对真实用户消息出现裸 `NO_REPLY`，已先执行 `scripts/v51_team_orchestrator_hygiene.py` 清理 supervisor `group/main` 与 worker `group/main` 会话后再复测
- [ ] （V5.1）timer 当前执行的是 `v51_team_orchestrator_reconcile.py resume-job`，而不是只跑被动 `watchdog-tick`
- [ ] （V5.1）若 supervisor 首轮未建单，`v51_team_orchestrator_reconcile.py` 能从最新 transcript 补建单、补接单、补派发
- [ ] （V5.1）worker 完成后必须通过 `callbackCommand(ingest-callback ...)` 写入 `stage_callbacks`，而不是向 hidden main / plaintext / transcript 发文本回调
- [ ] （V5.1）worker 主协议提交的是 `progressDraft / finalDraft / summary / details / risks / actionItems`，不再自己直接发群消息
- [ ] （V5.1）若 callback 附带 `progressMessageId / finalMessageId`，它们必须是真实 messageId，不能是 `pending / placeholder / sent / <pending...>`
- [ ] （V5.1）`resume-job` 只消费 `inbound_events / stage_callbacks / outbound_messages` 正式状态，不再从 hidden main / worker transcript 文本恢复 callback
- [ ] （V5.1）主管最终统一收口会优先引用各 worker 的完整 `finalVisibleText` 终案正文，群里看到的是可直接执行的终案方案，而不是只拼两三行摘要
- [ ] （V5.1）control-plane 每次直派 worker 前都会重置当前 `agent:<worker>:main`，避免旧协议会话残留
- [ ] （V5.1）若 waiting worker 的新 `main` 会话对 `TASK_DISPATCH` 裸回 `NO_REPLY`，`resume-job` 会在单次执行里做有限次内联重派，而不是只重派一次后等待下一轮 timer
- [ ] （V5.1）当前 stage 推进后，旧 stage 的重复 callback 不会在下一 stage 被重新消费或触发误重派
- [ ] （V5.1）worker 回调里的 `progressMessageId / finalMessageId` 都是群里真实 messageId，不包含 `pending / sent / <pending...> / *_placeholder`
- [ ] （V5.1）同一群内每个 agent 均使用独立 `accountId`
- [ ] （V5.1）新群与老群互不串线，worker 与 supervisor 全部回到当前 `groupPeerId`
- [ ] （V5.1）runtime manifest 已生成并归档

## D. 稳定性验证
- [ ] 网关重启后路由仍正确
- [ ] 若目标为 Linux / WSL2：当前版本对应的 `systemd --user` timer/service 正常
- [ ] 若目标为 macOS：当前版本对应的 `launchd` job 正常
- [ ] 若目标为 Windows：已明确不是原生 Windows service 正式验收，或已单独记录偏差与补救方案
- [ ] 5 分钟连续对话无异常报错
- [ ] 日志无权限拒绝与 schema 报错
- [ ] （V5.1）多 team 并行时无 cross-team session / memory / db 污染
- [ ] （V5.1）双群并发 canary 时新单编号全局唯一
- [ ] （V5.1）双群并发 canary 时单群只出现一条 active job
- [ ] （V5.1）双群并发 canary 时无重复阶段消息
- [ ] （V5.1）gateway 重启后不再持续刷历史 `delivery-recovery` 坏消息噪音
- [ ] （V5.1）双群并发 canary 时主管最终统一收口始终带 `jobRef`

## E. 回滚可用性
- [ ] 回滚命令可执行
- [ ] 回滚后服务恢复到变更前状态
