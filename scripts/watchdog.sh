#!/usr/bin/env bash
set -euo pipefail

# Ralph loop watchdog (tmux + heartbeat)
#
# Supervises a long-running ralph-loop command inside a tmux session.
# - Restarts on missing session/process death
# - Detects potential stalls via progress.log/iteration artifacts + pane output
# - Escalates to restart after configurable consecutive no-progress checks
#
# Usage (example):
#   scripts/watchdog.sh \
#     --session ralph-main \
#     --run-cmd "ralph-loop run --prd ralph/prd.json --config ralph/config.json" \
#     --workdir "$PWD" \
#     --interval 90

SESSION="ralph-main"
WORKDIR="$PWD"
RUN_CMD="ralph-loop run --prd ralph/prd.json --config ralph/config.json"
INTERVAL=90
STALL_CHECKS=2
RESTART_CAP_PER_HOUR=3
STATE_FILE=".ralph-runtime/watchdog-state.json"
LOG_FILE=".ralph-runtime/watchdog.log"

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --session NAME               tmux session name (default: $SESSION)
  --workdir DIR                repository/work directory (default: current dir)
  --run-cmd CMD                command to launch under tmux
  --interval SECONDS           heartbeat interval (default: $INTERVAL)
  --stall-checks N             consecutive no-progress checks before restart (default: $STALL_CHECKS)
  --restart-cap-per-hour N     max restarts/hour before exit (default: $RESTART_CAP_PER_HOUR)
  --state-file PATH            state file path (default: $STATE_FILE)
  --log-file PATH              watchdog log path (default: $LOG_FILE)
  -h, --help                   show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION="$2"; shift 2 ;;
    --workdir) WORKDIR="$2"; shift 2 ;;
    --run-cmd) RUN_CMD="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    --stall-checks) STALL_CHECKS="$2"; shift 2 ;;
    --restart-cap-per-hour) RESTART_CAP_PER_HOUR="$2"; shift 2 ;;
    --state-file) STATE_FILE="$2"; shift 2 ;;
    --log-file) LOG_FILE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

cd "$WORKDIR"
mkdir -p "$(dirname "$STATE_FILE")" "$(dirname "$LOG_FILE")" ralph

ts() { date +"%Y-%m-%dT%H:%M:%S%z"; }
log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

capture_sig() {
  local pane_out progress_sig iter_sig
  pane_out="$(tmux capture-pane -pt "$SESSION" 2>/dev/null | tail -n 40 || true)"

  if [[ -f ralph/progress.log ]]; then
    progress_sig="$(stat -c '%Y:%s' ralph/progress.log 2>/dev/null || echo '0:0')"
  else
    progress_sig="0:0"
  fi

  # shellcheck disable=SC2012
  local latest_iter
  latest_iter="$(ls -1 ralph/iteration-*.json 2>/dev/null | tail -n 1 || true)"
  if [[ -n "$latest_iter" && -f "$latest_iter" ]]; then
    iter_sig="$(stat -c '%Y:%s' "$latest_iter" 2>/dev/null || echo '0:0')"
  else
    iter_sig="0:0"
  fi

  printf '%s|%s|%s' "$progress_sig" "$iter_sig" "$(printf '%s' "$pane_out" | sha1sum | awk '{print $1}')"
}

all_tasks_done() {
  [[ -f ralph/prd.json ]] || return 1
  python3 - <<'PY'
import json,sys
try:
    with open('ralph/prd.json','r',encoding='utf-8') as f:
        data=json.load(f)
    tasks=data.get('tasks',[])
    if not tasks:
        sys.exit(1)
    done=all((t.get('status') or '').lower()=='done' for t in tasks)
    sys.exit(0 if done else 1)
except Exception:
    sys.exit(1)
PY
}

start_session() {
  log "Starting tmux session '$SESSION'"
  tmux new-session -d -s "$SESSION" "cd '$WORKDIR' && $RUN_CMD; echo EXIT:$?; sleep 999999"
}

restart_session() {
  log "Restarting session '$SESSION'"
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  start_session
}

# state
last_sig=""
no_progress=0
restart_times=()

if [[ -f "$STATE_FILE" ]]; then
  last_sig="$(python3 - <<PY
import json
p='$STATE_FILE'
try:
  d=json.load(open(p))
  print(d.get('last_sig',''))
except Exception:
  print('')
PY
)"
fi

log "Watchdog online (session=$SESSION interval=${INTERVAL}s)"

while true; do
  now_epoch="$(date +%s)"

  # sliding-window restart cap
  keep=()
  for t in "${restart_times[@]:-}"; do
    if (( now_epoch - t < 3600 )); then keep+=("$t"); fi
  done
  restart_times=("${keep[@]:-}")
  if (( ${#restart_times[@]} >= RESTART_CAP_PER_HOUR )); then
    log "Restart cap reached (${RESTART_CAP_PER_HOUR}/hour). Exiting watchdog for manual intervention."
    exit 2
  fi

  if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    log "Session missing"
    start_session
    restart_times+=("$now_epoch")
    sleep "$INTERVAL"
    continue
  fi

  if all_tasks_done; then
    log "All tasks done; watchdog exiting cleanly"
    exit 0
  fi

  sig="$(capture_sig)"
  if [[ -n "$last_sig" && "$sig" == "$last_sig" ]]; then
    ((no_progress+=1))
    log "No progress detected (count=$no_progress/$STALL_CHECKS)"
  else
    no_progress=0
    log "Progress observed"
  fi

  if (( no_progress >= STALL_CHECKS )); then
    log "Confirmed stall; collecting quick diagnostics"
    { echo "--- status snapshot ---"; ralph-loop status || true; echo "--- tail progress.log ---"; tail -n 40 ralph/progress.log 2>/dev/null || true; } >> "$LOG_FILE" 2>&1
    restart_session
    restart_times+=("$now_epoch")
    no_progress=0
    sig=""
  fi

  last_sig="$sig"
  python3 - <<PY
import json, time
p='$STATE_FILE'
d={'last_sig':'''$last_sig''','no_progress':$no_progress,'updated_at':int(time.time())}
json.dump(d,open(p,'w'),indent=2)
PY

  sleep "$INTERVAL"
done
