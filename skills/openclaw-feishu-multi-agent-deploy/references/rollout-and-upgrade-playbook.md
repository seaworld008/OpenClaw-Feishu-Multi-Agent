# 上线与升级手册

## A. 首次上线（Greenfield）
1. 准备 deployment inputs（建议从 templates 复制）
2. 生成配置 patch
3. `openclaw config validate`
4. 重启网关
5. 若目标为 `V4.3.1`，先执行一次会话卫生：
```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_hygiene.py \
  --home ~/.openclaw \
  --group-peer-id <团队群peerId> \
  --include-workers \
  --delete-transcripts
```
5. 安装平台对应 watchdog（Linux/WSL2 用 `systemd --user`，macOS 用 `launchd`）
6. 执行一次性 `WARMUP`
7. 验收 checklist 全部通过

## B. 增量改造（Brownfield，推荐）
1. 备份：
```bash
TS=$(date +%Y%m%d-%H%M%S)
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak.$TS
```
2. 只改必要字段：`channels.feishu` + `bindings`
3. canary 群验证（至少 2 条消息 + 1 次重启后复测）
4. 放量到全量群

### 会话卫生说明
- 只改普通 bindings / account secret 时，通常不需要清 session。
- 只要修改了以下任一项，就要先跑 `v431_single_group_hygiene.py`：
  - `supervisor/ops/finance` 的 `systemPrompt`
  - `callbackSessionKey`
  - `COMPLETE_PACKET` 字段
  - hidden main session 的消费逻辑

### 平台补充
- Linux / WSL2：优先启用 `templates/systemd/v4-3-watchdog.service` + `templates/systemd/v4-3-watchdog.timer`
- macOS：优先启用 `templates/launchd/v4-3-watchdog.plist`
- Windows：默认转为 `WSL2` 路线，并参考 `references/windows-wsl2-deployment-notes.md`

## C. 回滚
```bash
cp ~/.openclaw/openclaw.json.bak.$TS ~/.openclaw/openclaw.json
openclaw gateway restart
```

## D. 升级 OpenClaw / 插件时
1. 先记录版本：
```bash
openclaw --version
openclaw plugins list | rg -i feishu
```
2. 升级后先做 schema 校验：
```bash
openclaw config validate
```
3. 验证关键兼容点：
- `match.channel` 仍为 `feishu`（官方插件）
- `defaultAccount` 是否仍有效
- `groups.<chat_id>.requireMention` 是否按预期生效
- `bindings` 顺序未被误改
4. 做最小回归：
- 私聊 1 条
- canary 群 2 条（含 @ 与非 @）
- 多账号场景每个 accountId 至少 1 条
