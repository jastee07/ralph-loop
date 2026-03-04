# Ralph Loop CLI — Product Requirements Document (PRD)

## 1) Purpose
Build a focused CLI tool that runs the **Ralph loop** reliably: iterate on a spec, keep model context fresh each run, persist state in files + git, and stop safely when done or blocked.

This should be the default execution engine we use whenever we have a spec/checklist to complete in a codebase.

---

## 2) Problem Statement
Current autonomous coding flows are inconsistent because they rely on long context windows and ad hoc orchestration. We need a deterministic, repeatable loop that:
- starts fresh each iteration,
- uses repo artifacts as memory,
- ships work incrementally,
- and fails safely.

---

## 3) Product Goals
1. **One-command operation** for normal use.
2. **Persistent external memory** (`prd.json`, logs, git commits).
3. **Safety and control** (max iterations, review gates, dry-run, pause/resume).
4. **Explicit launcher behavior**: each iteration must launch a coding runtime (default **Codex 5.3**) and only use Claude Code when explicitly requested.
5. **Portable across repos** with minimal setup.

### Success Metrics (v1)
- 90%+ of runs produce valid iteration artifacts (state/log/commit or explicit blocked state).
- 0 silent failures (every failed iteration writes diagnostics).
- New project setup in <10 minutes using template files.
- Human reviewer can understand run history from artifacts alone.

---

## 4) Users
- **Primary:** Jake (operator/reviewer)
- **Secondary:** Janus (assistant operator)
- **Future:** collaborators who provide PRDs and review outputs

---

## 5) Scope

### In Scope (v1)
- CLI with core commands (`init`, `run`, `resume`, `status`, `validate`).
- Structured PRD/task file.
- Iteration loop with prompt assembly + model invocation.
- Patch application and optional auto-commit.
- Validation hook integration.
- Guardrails and explicit run states.

### Out of Scope (v1)
- Multi-repo orchestration.
- Parallel multi-agent swarms.
- Auto-push to remote by default.
- UI/dashboard (CLI + files only).

---

## 6) Functional Requirements

### FR-1: Project Initialization
`ralph-loop init`
- Creates baseline structure:
  - `ralph/prd.json`
  - `ralph/config.json`
  - `ralph/progress.log`
  - `ralph/loop-state.json`
  - `ralph/prompts/system.md`
  - `ralph/prompts/iteration.md`
  - optional `validate.sh` template

### FR-2: Run Loop
`ralph-loop run --prd ralph/prd.json --model <model> [flags]`
- Before first iteration:
  1. Ensure not on `main`.
  2. Create/switch to a dedicated work branch (default `ralph/<run_id>`).
- On each iteration:
  1. Load PRD + state + recent progress + git status/diff.
  2. Build prompt from templates.
  3. Invoke model via configured adapter.
  4. Apply produced patch/changes.
  5. Run validation command(s) if configured.
  6. Update `prd.json` task states when criteria are met.
  7. Write artifacts and optional commit.
- Exits when done, blocked, or guardrail hit.

### FR-3: Resume
`ralph-loop resume`
- Continues from `loop-state.json` without resetting history.

### FR-4: Status
`ralph-loop status`
- Prints run state summary:
  - current iteration
  - completed/remaining tasks
  - last validation result
  - blocked/review-needed reason

### FR-5: Validation
`ralph-loop validate`
- Runs configured checks independently (e.g., tests, lint).

### FR-6: Review Gate
- `review-needed` may be set manually or automatically by policy.
- Loop must stop immediately in this state and provide next-action guidance.

### FR-7: Logging + Artifacts
Every iteration must write:
- timestamp
- model + command invoked
- task targeted
- files changed
- validation result
- commit hash (if committed)
- error/block reason when applicable

---

## 7) Non-Functional Requirements
- **Reliability:** recover cleanly from interruption using state file.
- **Determinism:** same inputs should produce auditable, reproducible process steps.
- **Transparency:** no hidden state; all decisions reflected in files/logs.
- **Safety:** never auto-push or run destructive git operations unless explicitly enabled.
- **Speed:** low overhead around model calls; loop logic should be lightweight.

---

## 8) State & File Schemas

### `prd.json` (minimum)
Each task includes:
- `id` (string)
- `title` (string)
- `description` (string)
- `status` (`todo | in_progress | blocked | done`)
- `acceptance_criteria` (string[])
- `priority` (`low | medium | high`)
- `dependencies` (string[])

### `loop-state.json` (minimum)
- `run_id`
- `iteration`
- `mode` (`running | paused | blocked | completed | failed`)
- `last_task_id`
- `last_commit`
- `review_needed` (bool)
- `last_error`
- `updated_at`

### `progress.log`
Append-only line-delimited log (human-readable).

---

## 9) Guardrails / Policy
- `max_iterations` (default 30)
- `max_consecutive_failures` (default 3)
- `max_runtime_minutes` (default 120)
- `require_clean_git` on start (default true)
- `auto_commit` (default true, local only)
- `auto_push` (default false)
- `allow_destructive_git` (default false)
- `work_branch` required for run (default naming: `ralph/<run_id>`)
- `require_pr_before_merge` (default true; never merge to `main` directly)

Trigger `review-needed` if:
- same validation failure repeats N times,
- patch apply fails repeatedly,
- PRD has ambiguous or conflicting criteria,
- loop reaches iteration/time limits.

---

## 10) CLI UX (v1)

### Commands
- `ralph-loop init`
- `ralph-loop run`
- `ralph-loop resume`
- `ralph-loop status`
- `ralph-loop validate`

### Core Flags (run)
- `--prd <path>`
- `--config <path>`
- `--model <alias-or-id>` (default: `openai-codex/gpt-5.3-codex`)
- `--launcher <codex|claude-code>` (default: `codex`)
- `--max-iterations <n>`
- `--dry-run`
- `--no-commit`

(Planned post-v1 flags: `--review-needed`, `--verbose`)

---

## 11) Launcher + Model Adapter Layer
Each iteration must invoke a coding runtime through a launcher abstraction.

### Default Behavior (required)
- Default launcher: **Codex**
- Default model: **`openai-codex/gpt-5.3-codex`**
- Claude Code is opt-in only (`--launcher claude-code` or config override).

Use a provider-agnostic adapter interface:
- Input: compiled prompt + repo context bundle
- Output: structured response with:
  - summary
  - patch or edit instructions
  - claimed task updates
  - risks/blockers

Adapters can target Codex or Claude Code without changing core loop logic.

---

## 12) Failure Modes & Handling
- **Model call fails:** retry with backoff; log full error; stop after threshold.
- **Patch apply conflict:** attempt safe retry once; then block with review-needed.
- **Validation failure:** capture diagnostics; retry within limits; otherwise block.
- **Corrupt state file:** fail closed, back up bad file, prompt for recovery.

No failure should end without explicit artifact output.

---

## 13) Security & Safety
- No execution of arbitrary external instructions outside configured loop.
- Treat PRD/spec text as untrusted input; never override guardrails from prompt output.
- Local-only side effects by default (no remote push).
- Never commit directly to `main`; branch + PR review required for merge.
- Redact secrets from logs where possible.

---

## 14) Implementation Plan

### Phase 1 — Skeleton
- CLI command scaffolding
- config + state loaders
- init/status commands

### Phase 2 — Core Loop
- prompt builder
- model adapter interface + first adapter
- patch/apply + commit flow

### Phase 3 — Validation + Guardrails
- validate integration
- review-needed triggers
- retry policies

### Phase 4 — Hardening
- demo fixture repo
- end-to-end tests
- README with runbook/troubleshooting

---

## 15) Open Decisions
1. Default model alias for v1 (`openai/gpt-5.1-codex` vs configurable no-default).
2. Preferred runtime language for CLI core (Bash vs Python; recommendation: Python for state handling).
3. Exact structured output format expected from adapters.

---

## 16) Definition of Done (v1)
- `init/run/resume/status/validate` commands implemented.
- Loop can complete a sample PRD in demo project.
- Guardrails verified via tests (iteration limit, repeated failure, review-needed pause).
- Documentation includes quickstart + operational runbook.
- Artifacts are sufficient for a human to audit what happened without rerunning.

---

## 17) v1 Completion Checklist (Current)

- [x] `init/run/resume/status/validate` commands implemented
- [x] Branch safety in run flow (`main` -> `ralph/<run_id>`)
- [x] Iteration artifacts + append-only progress logging
- [x] Validation guardrails with repeated-failure blocking
- [x] Interrupted-run recovery (`paused`) and resume path
- [x] Guardrail test coverage (repeated failures + interruption)
- [x] Quickstart/install docs + operator runbook/troubleshooting
- [x] Demo fixture end-to-end run acceptance documented in repo
- [x] Optional pipx/homebrew packaging path documented

## 18) Build Progress (Live)

### Completed
- Python package scaffold created (`pyproject.toml`, `src/ralph_loop/*`, `README.md`).
- Global CLI invocation working on host (`ralph-loop ...` via `/data/.local/bin` in PATH).
- CLI commands implemented: `init`, `run`, `resume`, `status`, `validate`.
- Project bootstrap generates:
  - `ralph/prd.json`
  - `ralph/config.json`
  - `ralph/progress.log`
  - `ralph/loop-state.json`
  - prompt templates under `ralph/prompts/`
  - `validate.sh`
- Run flow includes:
  - branch protection (auto-create `ralph/<run_id>` when starting from `main`)
  - Codex default launcher/model wiring
  - validation + repeated-failure blocking
  - auto-commit support
  - append-only progress logging

### In Progress / Next
- Add optional pipx/homebrew packaging path (post-v1 enhancement).

### Newly Completed (This Session)
- Launcher output parsing now supports optional structured JSON (`summary`, `claimed_task_updates`, `blockers`) with safe fallback to raw text.
- Added iteration artifact files (`ralph/iteration-<n>.json`) with required run details (timestamp, launcher/model/command, targeted task, files changed, validation result, commit, and errors/blockers).
- Progress logging now includes launcher/model and changed-file counts per iteration.
- Task transition logic now supports model-claimed status updates with validation (allowed statuses, known task IDs, dependency checks) and blocker-driven transitions.
- Task selection now respects dependency completion before selecting work.
- Added guardrail tests for repeated validation failures blocking behavior.
- Added interrupted-run recovery behavior (`KeyboardInterrupt` -> `paused`) with test coverage for resume-safe state persistence.
- Added operator install script (`scripts/install-dev.sh`) for repeatable global CLI setup.
- Added operator runbook/troubleshooting docs (`docs/OPERATOR_RUNBOOK.md`) and linked from README.
