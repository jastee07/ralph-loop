# Demo Fixture End-to-End Acceptance

This document captures a reproducible v1 acceptance run using the bundled `demo/` project.

## Preconditions

From repo root:

```bash
cd /data/.openclaw/workspace/src/ralph-loop
./scripts/install-dev.sh
```

## 1) Reset demo state

```bash
cd /data/.openclaw/workspace/src/ralph-loop/demo
rm -rf .git
git init
git config user.email "demo@example.com"
git config user.name "Demo User"
git add .
git commit -m "demo baseline"
```

## 2) Initialize loop files (idempotent)

```bash
ralph-loop init --root .
```

## 3) Dry-run acceptance execution

```bash
ralph-loop run --root . --prd ralph/prd.json --config ralph/config.json --dry-run --no-commit --max-iterations 1
```

Expected outcomes:
- `ralph/loop-state.json` exists and updates iteration/mode fields
- `ralph/progress.log` appends iteration line
- `ralph/iteration-1.json` exists with launcher/model/task/validation fields

## 4) Verify status

```bash
ralph-loop status --root .
```

Expected output includes:
- `mode=...`
- `iter=...`
- `tasks=<done>/<total> done`

## 5) Optional guarded failure test

Set validation to fail:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('ralph/config.json')
c = json.loads(p.read_text())
c['validate_command'] = "python3 -c 'import sys; sys.exit(1)'"
c['max_consecutive_failures'] = 2
p.write_text(json.dumps(c, indent=2) + '\n')
PY
```

Run:

```bash
ralph-loop run --root . --dry-run --no-commit --max-iterations 3
```

Expected outcomes:
- `loop-state.json` transitions to `mode=blocked`
- `review_needed=true`
- `progress.log` contains `BLOCKED: repeated validation failures`

---

If all expected outcomes above occur, demo fixture acceptance is satisfied for v1.
