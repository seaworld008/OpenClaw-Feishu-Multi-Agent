#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
用法:
  check_v3_dispatch_canary.sh --log <path> --start-line <n> [--agents "a,b,c"] [--task-id "id"] [--dispatch-pattern "regex"]

说明:
  - 从日志指定起始行之后，检查是否出现目标 agent 会话派发轨迹
  - 同时要求出现派发证据正则；默认会检查一组常见 sessions_send 相关模式
  - 默认 agent: sales_agent,ops_agent,finance_agent
  - 成功返回 0 (DISPATCH_OK)
  - 失败返回 2 (DISPATCH_INCOMPLETE)
  - 证据不足返回 3 (DISPATCH_UNVERIFIED)
EOF
}

LOG=""
START_LINE=""
AGENTS="sales_agent,ops_agent,finance_agent"
TASK_ID=""
DISPATCH_PATTERNS=(
  "sessions_send"
  "tool.*sessions_send"
  "dispatch.*session"
  "send.*session"
)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --log)
      LOG="${2:-}"
      shift 2
      ;;
    --start-line)
      START_LINE="${2:-}"
      shift 2
      ;;
    --agents)
      AGENTS="${2:-}"
      shift 2
      ;;
    --task-id)
      TASK_ID="${2:-}"
      shift 2
      ;;
    --dispatch-pattern)
      DISPATCH_PATTERNS+=("${2:-}")
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

if [[ -z "$LOG" || -z "$START_LINE" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$LOG" ]]; then
  echo "日志文件不存在: $LOG" >&2
  exit 1
fi

if ! [[ "$START_LINE" =~ ^[0-9]+$ ]]; then
  echo "start-line 必须是正整数" >&2
  exit 1
fi

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

tail -n "+$((START_LINE + 1))" "$LOG" > "$TMP_FILE"

IFS=',' read -r -a AGENT_LIST <<< "$AGENTS"

missing=()
for agent in "${AGENT_LIST[@]}"; do
  agent="$(echo "$agent" | xargs)"
  if [[ -z "$agent" ]]; then
    continue
  fi
  if rg -q "session=agent:${agent}:" "$TMP_FILE"; then
    echo "OK: found dispatch trace for ${agent}"
  else
    echo "MISS: no dispatch trace for ${agent}"
    missing+=("$agent")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "DISPATCH_INCOMPLETE: missing agents => ${missing[*]}"
  exit 2
fi

if [[ -n "$TASK_ID" ]] && ! rg -q --fixed-strings "$TASK_ID" "$TMP_FILE"; then
  echo "DISPATCH_UNVERIFIED: task id not found in log window => $TASK_ID"
  exit 3
fi

dispatch_found=0
for pattern in "${DISPATCH_PATTERNS[@]}"; do
  if [[ -n "$pattern" ]] && rg -q "$pattern" "$TMP_FILE"; then
    echo "OK: found dispatch evidence pattern => $pattern"
    dispatch_found=1
    break
  fi
done

if [[ $dispatch_found -eq 0 ]]; then
  echo "DISPATCH_UNVERIFIED: no dispatch evidence pattern matched"
  exit 3
fi

echo "DISPATCH_OK: all target agent session traces found"
exit 0
