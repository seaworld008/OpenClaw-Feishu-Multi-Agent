# 验收清单

## A. 变更前
- [ ] `openclaw --version` 已记录
- [ ] `openclaw plugins list` 已确认 `@openclaw/feishu`
- [ ] 配置文件已备份（含时间戳）
- [ ] 飞书权限和事件订阅已完成审批

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
- [ ] （V3）主管能真实派发到目标会话（非仅文本派单）
- [ ] （V3）日志出现目标会话派发轨迹（sales/ops/finance）
- [ ] （V3）三方回传后主管可自动收口
- [ ] （V3）执行 `scripts/check_v3_dispatch_canary.sh` 返回 `DISPATCH_OK`
- [ ] （V3）若脚本返回 `DISPATCH_UNVERIFIED`，已补查原始日志中的 `sessions_send` / 派发证据
- [ ] （V4/V4.1/V4.2）主管未出现“未完成态却口头声称已安排/已派单”
- [ ] （V4/V4.1/V4.2）worker warm-up 后，主管可对必需执行角色形成真实派单链路
- [ ] （V4/V4.1/V4.2）`dispatchEvidence` 与 worker session jsonl 一致
- [ ] （V4.1/V4.2）若发生互审，`reviewEvidence` 存在且轮次不超过 1
- [ ] （V4.2）若返回 `SEND_PATH_AVAILABLE_BUT_LIST_MISS`，已改以 `dispatchEvidence` 与 worker session jsonl 复核，而不是继续把 `sessions_list` 当成唯一依据
- [ ] （V4.2）若返回 `TIMEOUT_BUT_WORKER_DELIVERED`，已检查 worker 回包证据，并确认 supervisor 具备二次收口策略
- [ ] （V4.2）若详细执行任务采用 fire-and-forget，已确认 `dispatchEvidence` 中记录 `accepted`，并通过 `sessions_history` / worker session jsonl 完成二次收口
- [ ] （V4.2）若出现被 `@` 后 `NO_REPLY`，已同时检查 `messages.groupChat.mentionPatterns`、supervisor `groupChat.mentionPatterns` 与 `PLAIN_TEXT` / 代码块包裹兼容
- [ ] （V4.2）若刚改过 supervisor / mention / tools / sendPolicy，已 fresh session 后再验收；不要直接沿用旧团队群会话
- [ ] （V4.2）若 fresh session 已创建，已确认 `supervisor_agent` workspace 不再保留默认 `BOOTSTRAP.md`，且 `IDENTITY.md` / `USER.md` / `SOUL.md` 已生产化
- [ ] （V4.2）若 `sessions_send` 出现 `No session found`，已核对主管使用的固定 sessionKey 是否为 `agent:<agentId>:feishu:group:<peerId>`
- [ ] （V4.2）执行 `scripts/check_v4_2_team_canary.sh` 后，结果已记录到验收报告
- [ ] （V4.2.1）若本次交付包含“群内可见协作”，已使用 `--require-visible-messages` 执行 `scripts/check_v4_2_team_canary.sh`
- [ ] （V4.2.1）`ops_agent` 已在团队群发出真实可见短摘要，且 worker session 中可定位真实 `messageId`
- [ ] （V4.2.1）`finance_agent` 已在团队群发出真实可见短摘要，且 worker session 中可定位真实 `messageId`
- [ ] （V4.2.1）worker 群发摘要为短消息，详细执行结果仍回主管，未把完整长文刷到群里
- [ ] （V4.2.1）主管最终收口发生在 worker 群发摘要之后，形成“群内可见协作 + 主管统一交付”的完整链路
- [ ] （V4.3）用户可不输入 `taskId`，supervisor 会自动生成内部 `jobRef`
- [ ] （V4.3）同一个团队群同时最多只有 1 个 `activeJob`
- [ ] （V4.3）第二个独立任务在当前任务未结束时会进入队列，而不是与当前任务串线
- [ ] （V4.3）用户补充说明会归并到当前 `activeJob`，不会错误新建第二个任务
- [ ] （V4.3）状态层（SQLite 或飞书多维表格镜像）中可查到 `jobRef`、状态、worker messageId 和最终收口证据
- [ ] （V4.3）supervisor 只有在 `ops_agent` 与 `finance_agent` 都写入完整完成包后，才最终统一收口
- [ ] （V4.3.1）部署完成后已做一次性 `WARMUP`，worker 的 team session 已创建成功
- [ ] （V4.3.1）worker 只发 1 条进度摘要和 1 条结论摘要，不再出现“任务已接收/等待具体内容”
- [ ] （V4.3.1）运营与财务的结论摘要允许多行完整输出，不再被压成一句话
- [ ] （V4.3.1）supervisor 在群里只发接单与最终收口两条消息，不再插入中间状态播报
- [ ] （V4.3.1）群里不再出现 `ACK_READY / REPLY_SKIP / COMPLETE_PACKET / WORKFLOW_INCOMPLETE`
- [ ] （V4.3.1）worker 的内部回调统一走 `agent:supervisor_agent:main`，hidden main 会话完成 `mark-worker-complete -> ready-to-rollup -> close-job done`
- [ ] （V4.3.1）`watchdog-tick` 可识别 stale active job，并在需要时提升队列中的下一条任务
- [ ] （V4.3.1）执行 `scripts/check_v4_3_canary.py` 返回 `V4_3_CANARY_OK`

## D. 稳定性验证
- [ ] 网关重启后路由仍正确
- [ ] 5 分钟连续对话无异常报错
- [ ] 日志无权限拒绝与 schema 报错
- [ ] （V3）日志无 sessions 权限拒绝与 sendPolicy 拦截
- [ ] （V4/V4.1/V4.2）日志无持续 `thread=true` / `subagent_spawning hooks` 重试风暴
- [ ] （V4.3）group session 已配置 reset 策略，长期运行不会无限复用同一 transcript
- [ ] （V4.3.1）active job 卡住后不会永久阻塞后续任务，watchdog 或关闭流程可以释放队列

## E. 回滚可用性
- [ ] 回滚命令可执行
- [ ] 回滚后服务恢复到变更前状态
