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

## D. 稳定性验证
- [ ] 网关重启后路由仍正确
- [ ] 5 分钟连续对话无异常报错
- [ ] 日志无权限拒绝与 schema 报错
- [ ] （V3）日志无 sessions 权限拒绝与 sendPolicy 拦截

## E. 回滚可用性
- [ ] 回滚命令可执行
- [ ] 回滚后服务恢复到变更前状态
