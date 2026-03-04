# ralph-loop

Python CLI implementing a Ralph-style coding loop.

## Install (editable)

```bash
cd /data/.openclaw/workspace/src/ralph-loop
./scripts/install-dev.sh
```

Manual equivalent:

```bash
PYTHONUSERBASE=/data/.local python3 -m pip install --user --break-system-packages -e .
```

## Commands

- `ralph-loop init`
- `ralph-loop run --prd ralph/prd.json --config ralph/config.json`
- `ralph-loop resume`
- `ralph-loop status`
- `ralph-loop validate`

## Runbook

See:
- `docs/OPERATOR_RUNBOOK.md` for setup, daily ops, and troubleshooting
- `docs/DEMO_ACCEPTANCE.md` for reproducible v1 demo acceptance steps
- `docs/PACKAGING.md` for install/packaging options (dev, pipx, homebrew path)

## Defaults

- launcher: `codex`
- model: `openai-codex/gpt-5.3-codex`
- auto-commit: `true`
- require PR before merge: `true`
- creates branch: `ralph/<run_id>`

## Iteration Artifacts

Each loop iteration writes `ralph/iteration-<n>.json` including:
- timestamp, launcher, model, command
- targeted task and task update decisions
- changed files
- validation result/output
- commit hash (if committed)
- blockers/errors
