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
- [ ] （V5.1）supervisor 群级可见消息通过 `build-visible-ack/build-rollup-visible-message -> message -> record-visible-message` 落地，不再依赖普通 assistant 文本直出
- [ ] （V5.1）worker 的两条群内可见消息都带固定标题：`【角色进度｜TG-xxxx】`、`【角色结论｜TG-xxxx】`，没有丢 `jobRef`
- [ ] （V5.1）supervisor 最终统一收口是完整结构化方案，包含 `任务主题`、各角色结论、`联合风险与红线`、`明日三件事`
- [ ] （V5.1）同一 `jobRef` 在群里只出现 1 次 `【主管最终统一收口｜TG-xxxx】`，没有重复收口
- [ ] （V5.1）若主管群 session 对真实用户消息出现裸 `NO_REPLY`，已先执行 `scripts/v51_team_orchestrator_hygiene.py` 清理 supervisor `group/main` 与 worker `group/main` 会话后再复测
- [ ] （V5.1）timer 当前执行的是 `v51_team_orchestrator_reconcile.py resume-job`，而不是只跑被动 `watchdog-tick`
- [ ] （V5.1）若 supervisor 首轮未建单，`v51_team_orchestrator_reconcile.py` 能从最新 transcript 补建单、补接单、补派发
- [ ] （V5.1）若 hidden main transcript 里已出现 `COMPLETE_PACKET`，`resume-job` 能消费最近有效包并推进下一 stage / 最终收口，而不是卡在 `NO_REPLY` 或错误 assistant 文本
- [ ] （V5.1）若 hidden main 的最新 `COMPLETE_PACKET` 还是 `pending / placeholder / sent / <pending...>`，但 waiting worker 的 `main` transcript 已经有两个真实 `message` toolResult，`resume-job` 会先从 worker transcript 恢复真实 `progressMessageId / finalMessageId`，而不是直接删会话重派
- [ ] （V5.1）即便 hidden main 还没收到 `COMPLETE_PACKET`，只要 waiting worker 的 `main` transcript 已经有 callback toolCall 草稿和两个真实 `message` toolResult，`resume-job` 也会直接从 worker transcript 合成有效回调并推进下一 stage / 最终收口
- [ ] （V5.1）主管最终统一收口会优先引用各 worker 的完整 `finalVisibleText` 终案正文，群里看到的是可直接执行的终案方案，而不是只拼两三行摘要
- [ ] （V5.1）control-plane 每次直派 worker 前都会重置当前 `agent:<worker>:main`，避免旧协议会话残留
- [ ] （V5.1）若 waiting worker 的新 `main` 会话对 `TASK_DISPATCH` 裸回 `NO_REPLY`，`resume-job` 会在单次执行里做有限次内联重派，而不是只重派一次后等待下一轮 timer
- [ ] （V5.1）当前 stage 推进后，旧 stage 的 hidden main `COMPLETE_PACKET` 不会在下一 stage 被重新当成 invalid packet 触发误重派
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

## E. 回滚可用性
- [ ] 回滚命令可执行
- [ ] 回滚后服务恢复到变更前状态
