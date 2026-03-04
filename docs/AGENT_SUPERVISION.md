# Agent Supervision: tmux + Heartbeat Watchdog

This guide covers production-style operation for long-lived coding agents.

## Why

Agents fail for boring reasons: terminal disconnects, host restarts, network blips, temp cleanup. A watchdog should recover routine failures automatically.

## Baseline pattern

- Run each agent loop in a dedicated `tmux` session
- Keep the session alive after command exit (for postmortem logs)
- Heartbeat checks liveness + progress + completion
- Auto-restart on crash; restart on confirmed stall

## tmux launch pattern

Example:

```bash
tmux new-session -d -s ralph-main "ralph-loop run --prd ralph/prd.json --config ralph/config.json; echo EXIT:$?; sleep 999999"
```

`sleep 999999` keeps the pane available for inspection after process exit.

## Included script (recommended starting point)

A reference watchdog is included at:

- `scripts/watchdog.sh`

Example usage:

```bash
scripts/watchdog.sh \
  --session ralph-main \
  --run-cmd "ralph-loop run --prd ralph/prd.json --config ralph/config.json" \
  --workdir "$PWD" \
  --interval 90
```

## Heartbeat policy (recommended)

Avoid a single brittle signal (like identical stdout twice).
Use a **multi-signal** stall detector:

1. **Alive**: tmux session exists
2. **Progress**: at least one changed signal since last heartbeat:
   - pane output changed, or
   - `ralph/progress.log` size or mtime changed, or
   - latest `iteration-*.json` timestamp advanced
3. **Done**: `prd.json` shows all tasks complete
4. **Stall suspicion**: no progress for 2 checks
5. **Confirmed stall**: no progress for N minutes (e.g., 10-20m) while not done

## Recovery ladder

Use escalation instead of immediate hard kill:

1. **Soft** (first suspicion): capture diagnostics (`status`, last log tail)
2. **Nudge**: send interrupt/continue or run `ralph-loop status` in-session
3. **Hard restart** (confirmed): kill process/session and relaunch
4. **Escalate to human** after repeated restart failures

## Minimal heartbeat checks

- `tmux has-session -t <name>`
- Compare `stat` for `ralph/progress.log`
- Parse `ralph/loop-state.json` for mode/error/review_needed
- Parse task completion from `ralph/prd.json`

## Suggested thresholds

- Heartbeat interval: 60-120s
- Stall suspicion: 2 consecutive no-progress checks
- Confirmed stall: 10-20 minutes no progress
- Restart cap: 3 restarts/hour then alert

## Operational notes

- Keep watchdog separate from agent process
- Store watchdog events in a dedicated log
- Record restart reason + snapshot of loop state for audits
- If loop enters `review_needed`, prefer human intervention over blind restart
