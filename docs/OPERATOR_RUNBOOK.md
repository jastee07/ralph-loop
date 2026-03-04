# Ralph Loop Operator Runbook

## 1) Install

### Dev install (editable)
```bash
cd /data/.openclaw/workspace/src/ralph-loop
./scripts/install-dev.sh
```

If `ralph-loop` is not found afterward, add:
```bash
export PATH="/data/.local/bin:$PATH"
```

## 2) Quickstart in a repo

```bash
# from your target repo
ralph-loop init

# edit tasks in ralph/prd.json first
ralph-loop run --prd ralph/prd.json --config ralph/config.json
```

## 3) Day-to-day commands

```bash
ralph-loop status
ralph-loop resume
ralph-loop validate
```

## 4) Required artifacts to inspect

- `ralph/loop-state.json` → current mode, iteration, review-needed/error fields
- `ralph/progress.log` → append-only execution timeline
- `ralph/iteration-<n>.json` → per-iteration diagnostics
- `ralph/prd.json` → task state progression

## 5) Common operator flow

1. Prepare/refresh task list in `ralph/prd.json`
2. Run `ralph-loop run`
3. Watch `ralph/status` and inspect latest `iteration-<n>.json`
4. If blocked/review-needed, resolve issue (tests, task ambiguity, adapter output)
5. Resume with `ralph-loop resume`

## 6) Troubleshooting

### A) "Git working tree is not clean"
- Commit/stash local changes first, or set `require_clean_git=false` in `ralph/config.json`

### B) Immediate blocked state from validation failures
- Run `ralph-loop validate`
- Fix failing checks or temporarily adjust `validate_command`
- Resume after fix

### C) No task selected / "no available task"
- Check task statuses and dependency chains in `ralph/prd.json`
- Ensure at least one `todo`/`in_progress` task has all dependencies done

### D) Launcher command failures
- Verify command templates in `ralph/config.json` under `adapter`
- Confirm launcher binary exists in PATH (`codex` or `claude`)

### E) Interrupted run recovery
- Ctrl+C sets mode to `paused`
- Continue with `ralph-loop resume`

## 7) Guardrail tuning (`ralph/config.json`)

- `max_iterations`
- `max_consecutive_failures`
- `max_runtime_minutes`
- `auto_commit`
- `require_clean_git`

Default posture is conservative (local-only, no auto-push, PR-before-merge).
