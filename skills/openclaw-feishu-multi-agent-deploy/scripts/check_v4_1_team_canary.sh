#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
用法:
  check_v4_1_team_canary.sh --task-id <id> [--session-root <path>] [--supervisor-agent <id>] [--required-agents "ops_agent,finance_agent"] [--optional-agents "sales_agent"] [--log <path> --start-line <n>] [--expect-review] [--max-review-round <n>]

说明:
  - 优先从 ~/.openclaw/agents/*/sessions/*.jsonl 查证据，再回退到网关日志窗口
  - 默认必需执行角色: ops_agent,finance_agent
  - 默认可选执行角色: sales_agent
  - 若 supervisor 返回 nextAction=tool_call_required，表示本轮没有任何真实工具调用
  - 成功返回 0 (TEAM_CANARY_OK)
  - 缺少真实派单链返回 2 (DISPATCH_INCOMPLETE)
  - 证据不足或互审证据不足返回 3 (DISPATCH_UNVERIFIED)
EOF
}

TASK_ID=""
SESSION_ROOT="${HOME}/.openclaw/agents"
SUPERVISOR_AGENT="supervisor_agent"
REQUIRED_AGENTS="ops_agent,finance_agent"
OPTIONAL_AGENTS="sales_agent"
LOG=""
START_LINE=""
EXPECT_REVIEW=0
MAX_REVIEW_ROUND=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-id)
      TASK_ID="${2:-}"
      shift 2
      ;;
    --session-root)
      SESSION_ROOT="${2:-}"
      shift 2
      ;;
    --supervisor-agent)
      SUPERVISOR_AGENT="${2:-}"
      shift 2
      ;;
    --required-agents)
      REQUIRED_AGENTS="${2:-}"
      shift 2
      ;;
    --optional-agents)
      OPTIONAL_AGENTS="${2:-}"
      shift 2
      ;;
    --log)
      LOG="${2:-}"
      shift 2
      ;;
    --start-line)
      START_LINE="${2:-}"
      shift 2
      ;;
    --expect-review)
      EXPECT_REVIEW=1
      shift
      ;;
    --max-review-round)
      MAX_REVIEW_ROUND="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$TASK_ID" ]]; then
  echo "缺少必填参数 --task-id" >&2
  usage >&2
  exit 1
fi

if [[ -n "$LOG" && -z "$START_LINE" ]]; then
  echo "提供 --log 时必须同时提供 --start-line" >&2
  exit 1
fi

if [[ -n "$START_LINE" ]] && ! [[ "$START_LINE" =~ ^[0-9]+$ ]]; then
  echo "start-line 必须是正整数" >&2
  exit 1
fi

if ! [[ "$MAX_REVIEW_ROUND" =~ ^[0-9]+$ ]]; then
  echo "max-review-round 必须是非负整数" >&2
  exit 1
fi

TMP_LOG=""
if [[ -n "$LOG" ]]; then
  if [[ ! -f "$LOG" ]]; then
    echo "日志文件不存在: $LOG" >&2
    exit 1
  fi
  TMP_LOG="$(mktemp)"
  tail -n "+$((START_LINE + 1))" "$LOG" > "$TMP_LOG"
fi

cleanup() {
  if [[ -n "$TMP_LOG" && -f "$TMP_LOG" ]]; then
    rm -f "$TMP_LOG"
  fi
}
trap cleanup EXIT

trim() {
  echo "$1" | xargs
}

agent_session_dir() {
  local agent="$1"
  echo "${SESSION_ROOT}/${agent}/sessions"
}

agent_has_session_task() {
  local agent="$1"
  local dir
  dir="$(agent_session_dir "$agent")"
  [[ -d "$dir" ]] && rg -q --fixed-strings "$TASK_ID" "$dir"
}

agent_has_log_trace() {
  local agent="$1"
  [[ -n "$TMP_LOG" ]] && rg -q "session=agent:${agent}:" "$TMP_LOG"
}

supervisor_has_pattern() {
  local pattern="$1"
  local dir
  dir="$(agent_session_dir "$SUPERVISOR_AGENT")"
  if [[ -d "$dir" ]] && rg -q "$pattern" "$dir"; then
    return 0
  fi
  [[ -n "$TMP_LOG" ]] && rg -q "$pattern" "$TMP_LOG"
}

supervisor_task_pattern() {
  local pattern="$1"
  local dir
  dir="$(agent_session_dir "$SUPERVISOR_AGENT")"
  if [[ -d "$dir" ]] && rg -q --multiline "(?s)${TASK_ID}.*${pattern}|${pattern}.*${TASK_ID}" "$dir"; then
    return 0
  fi
  [[ -n "$TMP_LOG" ]] && rg -q --multiline "(?s)${TASK_ID}.*${pattern}|${pattern}.*${TASK_ID}" "$TMP_LOG"
}

print_source() {
  local agent="$1"
  if agent_has_session_task "$agent"; then
    echo "session-jsonl"
    return
  fi
  if agent_has_log_trace "$agent"; then
    echo "gateway-log"
    return
  fi
  echo "missing"
}

if ! agent_has_session_task "$SUPERVISOR_AGENT" && ! agent_has_log_trace "$SUPERVISOR_AGENT"; then
  echo "DISPATCH_INCOMPLETE: supervisor 没有命中任务 => ${SUPERVISOR_AGENT} / ${TASK_ID}"
  exit 2
fi

IFS=',' read -r -a REQUIRED_LIST <<< "$REQUIRED_AGENTS"
missing_required=()
for raw in "${REQUIRED_LIST[@]}"; do
  agent="$(trim "$raw")"
  [[ -z "$agent" ]] && continue
  source_kind="$(print_source "$agent")"
  if [[ "$source_kind" == "missing" ]]; then
    echo "MISS: ${agent} 缺少任务证据"
    missing_required+=("$agent")
  else
    echo "OK: ${agent} 命中任务证据 (${source_kind})"
  fi
done

if [[ ${#missing_required[@]} -gt 0 ]]; then
  echo "DISPATCH_INCOMPLETE: missingTargets => ${missing_required[*]}"
  exit 2
fi

dispatch_patterns=(
  "dispatchEvidence"
  "sessions_send"
  "sendStatus"
  "sentAt"
  "evidenceSource"
)

spawn_unavailable_patterns=(
  "mode=\"session\" requires thread=true"
  "thread=true is unavailable because no channel plugin registered subagent_spawning hooks"
  "Thread bindings are unavailable"
)

dispatch_found=0
for pattern in "${dispatch_patterns[@]}"; do
  if supervisor_task_pattern "$pattern"; then
    echo "OK: supervisor 命中派单证据模式 => $pattern"
    dispatch_found=1
    break
  fi
done

if [[ $dispatch_found -eq 0 ]]; then
  for pattern in "${spawn_unavailable_patterns[@]}"; do
    if supervisor_task_pattern "$pattern"; then
      echo "DISPATCH_INCOMPLETE: 当前渠道不支持 thread-bound sessions_spawn，需先对缺失 worker 手工 warm-up"
      exit 2
    fi
  done
  if supervisor_task_pattern "tool_call_required|no_tool_call"; then
    echo "DISPATCH_INCOMPLETE: supervisor 本轮没有任何真实工具调用（tool_call_required）"
    exit 2
  fi
  if supervisor_task_pattern "DISPATCH_INCOMPLETE"; then
    echo "DISPATCH_INCOMPLETE: supervisor 仍处于未完成态，未找到真实派单证据"
    exit 2
  fi
  echo "DISPATCH_UNVERIFIED: supervisor 未输出 dispatchEvidence/sessions_send 证据"
  exit 3
fi

if supervisor_task_pattern "DISPATCH_INCOMPLETE" && supervisor_task_pattern "已派单|已安排|已分配|assigned|dispatched"; then
  echo "DISPATCH_INCOMPLETE: supervisor 出现未完成态但正文包含口头派单语义"
  exit 2
fi

if ! supervisor_task_pattern "dispatchEvidence"; then
  echo "DISPATCH_UNVERIFIED: supervisor 缺少 dispatchEvidence 字段"
  exit 3
fi

if [[ $EXPECT_REVIEW -eq 1 ]]; then
  if ! supervisor_task_pattern "reviewEvidence"; then
    echo "DISPATCH_UNVERIFIED: 期望互审，但缺少 reviewEvidence"
    exit 3
  fi
  if supervisor_task_pattern "reviewRound[^0-9]*[2-9]"; then
    echo "DISPATCH_INCOMPLETE: 发现超过 1 轮互审的证据"
    exit 2
  fi
else
  if supervisor_task_pattern "reviewRound[^0-9]*[2-9]"; then
    echo "DISPATCH_INCOMPLETE: 发现 reviewRound 超出上限"
    exit 2
  fi
fi

echo "TEAM_CANARY_OK: supervisor 与必需执行角色已形成真实派单链路"
exit 0
