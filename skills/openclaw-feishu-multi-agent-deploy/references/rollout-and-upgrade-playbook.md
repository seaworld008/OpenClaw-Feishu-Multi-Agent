# 上线与升级手册

## 迁移原则

- `V5.1 Hardening` brownfield 迁移必须按 team 分批切换，不能一次性并发替换所有群
- brownfield 切换顺序固定为：`internal_main` -> `external_main`
- 同一时刻只允许一个 team 进入 clean redeploy / hygiene / canary
- 并发双群测试只用于最终验收，不作为第一轮排障手段

## 迁移前备份范围

至少备份：

- `~/.openclaw/openclaw.json`
- `~/.openclaw/v51-runtime-manifest.json`
- `~/.openclaw/teams/`
- `~/.config/systemd/user/v51-team-*`

## A. 首次上线（Greenfield）
1. 准备 deployment inputs（建议从 templates 复制）
2. 生成配置 patch
3. `openclaw config validate`
4. 重启网关
5. 若目标为 `V5.1 Hardening`，先执行一次会话卫生：
```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_hygiene.py \
  --home ~/.openclaw \
  --group-peer-id <teamGroupPeerId> \
  --include-workers \
  --delete-transcripts
```
6. 安装平台对应 watchdog（Linux/WSL2 用 `systemd --user`，macOS 用 `launchd`）
7. 执行一次性 `WARMUP`
8. 验收 checklist 全部通过

## B. 增量改造（Brownfield，推荐）
1. 备份：
```bash
TS=$(date +%Y%m%d-%H%M%S)
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak.$TS
```
2. 额外归档 `~/.openclaw/v51-runtime-manifest.json`、`~/.openclaw/teams/` 和 `~/.config/systemd/user/v51-team-*`
3. 先切 `internal_main`
4. 只改必要字段并执行 clean redeploy + hygiene
5. `internal_main` 单群 canary 通过后，再切 `external_main`
6. 两个 team 都完成单群 canary 后，再做双群并发验收
7. 最后放量到全量群

### 会话卫生说明
- 只改普通 bindings / account secret 时，通常不需要清 session。
- 只要修改了以下任一项，就要先跑 `v51_team_orchestrator_hygiene.py`：
  - `roleCatalog`
  - `teams[].supervisor/workers[]`
  - `workflow.stages`
  - hidden main session 的消费逻辑

### 平台补充
- Linux / WSL2：优先启用 `templates/systemd/v51-team-watchdog.service` + `templates/systemd/v51-team-watchdog.timer`
- macOS：优先启用 `templates/launchd/v51-team-watchdog.plist`
- Windows：默认转为 `WSL2` 路线，并参考 `templates/windows/wsl.conf.example`

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

## E. 双群并发最终验收

当 `internal_main` 与 `external_main` 都完成各自单群切换后，再做一次双群并发 canary。通过标准固定为：

1. 新单编号全局唯一
2. 单群只出现一条 active job
3. 无重复阶段消息
4. 主管最终统一收口始终带 `jobRef`
