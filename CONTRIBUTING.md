# Contributing to ralph-loop

Thanks for improving ralph-loop.

## Development setup

```bash
cd /data/.openclaw/workspace/src/ralph-loop
./scripts/install-dev.sh
```

If needed:
```bash
export PATH="/data/.local/bin:$PATH"
```

## Typical workflow

1. Create a branch
2. Make small, focused changes
3. Run checks locally
4. Open a PR with a clear summary

## Local checks (before PR)

```bash
python3 -m compileall src
python3 -m pytest -q
```

If your change touches loop behavior, also run a quick manual loop smoke test:

```bash
ralph-loop init
ralph-loop run --prd ralph/prd.json --config ralph/config.json
ralph-loop status
```

## Code standards

- Keep modules single-purpose
- Prefer explicit state transitions over implicit behavior
- Add/adjust tests for guardrail/state-machine changes
- Preserve append-only diagnostics (`progress.log`, `iteration-*.json`) semantics

## Commit and PR guidance

- Use descriptive commit messages
- In PR description include:
  - Problem statement
  - Behavioral change
  - Validation evidence (test output, status snippets)
  - Risk/rollback notes for engine changes

## What not to commit

Do **not** commit generated files:
- `__pycache__/`, `*.pyc`
- `*.egg-info/`, `dist/`, `build/`
- runtime workspace artifacts in `ralph/`
- demo generated run-state (`demo/ralph/loop-state.json`, `demo/ralph/progress.log`)
