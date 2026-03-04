from __future__ import annotations

import json
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
import os
from typing import Any

from .adapter import AdapterError, LauncherResult, invoke_launcher
from .config import load_config
from .git_ops import (
    GitError,
    changed_files,
    commit_all,
    create_or_switch_branch,
    current_branch,
    diff,
    ensure_clean_git,
)
from .io import append_text, read_json, write_json, write_text
from .models import LoopState
from .prompts import compile_prompt, tail_text


VALID_TASK_STATUSES = {"todo", "in_progress", "blocked", "done"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def init_project(root: Path) -> None:
    ralph_dir = root / "ralph"
    (ralph_dir / "prompts").mkdir(parents=True, exist_ok=True)

    prd = {
        "tasks": [
            {
                "id": "task-1",
                "title": "Replace with your first task",
                "description": "Describe expected outcome",
                "status": "todo",
                "acceptance_criteria": ["Define measurable pass criteria"],
                "priority": "high",
                "dependencies": [],
            }
        ]
    }
    if not (ralph_dir / "prd.json").exists():
        write_json(ralph_dir / "prd.json", prd)

    config = load_config(None)
    if not (ralph_dir / "config.json").exists():
        write_json(ralph_dir / "config.json", config)

    if not (ralph_dir / "progress.log").exists():
        write_text(ralph_dir / "progress.log", f"[{_now()}] initialized\n")

    if not (ralph_dir / "loop-state.json").exists():
        st = LoopState(run_id=str(uuid.uuid4()), mode="paused")
        write_json(ralph_dir / "loop-state.json", st.to_dict())

    if not (ralph_dir / "prompts/system.md").exists():
        write_text(
            ralph_dir / "prompts/system.md",
            "You are a coding agent. Make minimal, correct changes that satisfy the PRD task and preserve existing behavior.\n",
        )

    if not (ralph_dir / "prompts/iteration.md").exists():
        write_text(
            ralph_dir / "prompts/iteration.md",
            "Complete the highest-priority unfinished task. Update files directly. If blocked, explain blocker clearly.\n",
        )

    if not (root / "validate.sh").exists():
        validate_path = root / "validate.sh"
        write_text(
            validate_path,
            "#!/usr/bin/env bash\nset -euo pipefail\n# add project checks here (test/lint/build)\necho 'validate placeholder'\n",
        )
        os.chmod(validate_path, 0o755)


def _all_done(prd: dict) -> bool:
    tasks = prd.get("tasks", [])
    return bool(tasks) and all(t.get("status") == "done" for t in tasks)


def _dependencies_done(task: dict[str, Any], task_map: dict[str, dict[str, Any]]) -> bool:
    for dep_id in task.get("dependencies", []):
        dep = task_map.get(dep_id)
        if not dep or dep.get("status") != "done":
            return False
    return True


def _next_task(prd: dict) -> dict | None:
    tasks = prd.get("tasks", [])
    task_map = {str(t.get("id")): t for t in tasks}
    for priority in ["high", "medium", "low"]:
        for t in tasks:
            if t.get("priority") != priority:
                continue
            if t.get("status") not in {"todo", "in_progress", "blocked"}:
                continue
            if not _dependencies_done(t, task_map):
                continue
            return t
    return None


def _run_validation(root: Path, command: str) -> tuple[bool, str]:
    proc = subprocess.run(command, cwd=root, shell=True, capture_output=True, text=True)
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode == 0, out.strip()


def _apply_task_updates_from_launcher(prd: dict[str, Any], launcher_result: LauncherResult, fallback_task_id: str) -> tuple[list[str], list[str]]:
    tasks = prd.get("tasks", [])
    task_map = {str(t.get("id")): t for t in tasks}

    updated: list[str] = []
    ignored: list[str] = []

    for upd in launcher_result.claimed_task_updates:
        if not isinstance(upd, dict):
            ignored.append("non-object update")
            continue

        task_id = str(upd.get("id") or fallback_task_id)
        status = str(upd.get("status") or "").strip()

        if status not in VALID_TASK_STATUSES:
            ignored.append(f"invalid status for {task_id}: {status}")
            continue

        task = task_map.get(task_id)
        if not task:
            ignored.append(f"unknown task id: {task_id}")
            continue

        if status == "done" and not _dependencies_done(task, task_map):
            ignored.append(f"dependencies not done for {task_id}")
            continue

        task["status"] = status
        updated.append(f"{task_id}:{status}")

    if launcher_result.blockers:
        task = task_map.get(fallback_task_id)
        if task and task.get("status") != "done":
            task["status"] = "blocked"
            updated.append(f"{fallback_task_id}:blocked")

    return updated, ignored


def run_loop(
    root: Path,
    prd_path: Path,
    config_path: Path | None,
    launcher: str | None,
    model: str | None,
    max_iterations: int | None,
    no_commit: bool,
    dry_run: bool,
) -> None:
    ralph_dir = root / "ralph"
    state_path = ralph_dir / "loop-state.json"
    progress_path = ralph_dir / "progress.log"
    prompts_dir = ralph_dir / "prompts"

    config = load_config(config_path or (ralph_dir / "config.json"))
    launcher = launcher or config.get("launcher", "codex")
    model = model or config.get("model")
    max_iters = max_iterations or int(config.get("max_iterations", 30))

    if config.get("require_clean_git", True):
        ensure_clean_git(root)
    if current_branch(root) == "main":
        run_id = str(uuid.uuid4())[:8]
        create_or_switch_branch(root, f"ralph/{run_id}")

    state = LoopState.from_dict(read_json(state_path)) if state_path.exists() else LoopState(run_id=str(uuid.uuid4()))
    state.mode = "running"
    write_json(state_path, state.to_dict())

    start = datetime.now(UTC)
    failures = 0

    try:
        for _ in range(max_iters):
            if datetime.now(UTC) - start > timedelta(minutes=int(config.get("max_runtime_minutes", 120))):
                state.mode = "blocked"
                state.review_needed = True
                state.last_error = "max runtime reached"
                write_json(state_path, state.to_dict())
                append_text(progress_path, f"[{_now()}] BLOCKED: max runtime reached\n")
                return

            prd = read_json(prd_path)
            if _all_done(prd):
                state.mode = "completed"
                write_json(state_path, state.to_dict())
                append_text(progress_path, f"[{_now()}] COMPLETED\n")
                return

            task = _next_task(prd)
            if not task:
                state.mode = "blocked"
                state.review_needed = True
                state.last_error = "no available task"
                write_json(state_path, state.to_dict())
                append_text(progress_path, f"[{_now()}] BLOCKED: no available task\n")
                return

            state.iteration += 1
            state.last_task_id = task.get("id")

            system_prompt = (prompts_dir / "system.md").read_text() if (prompts_dir / "system.md").exists() else ""
            iteration_prompt = (prompts_dir / "iteration.md").read_text() if (prompts_dir / "iteration.md").exists() else ""
            prompt = compile_prompt(system_prompt, iteration_prompt, json.dumps(prd, indent=2), tail_text(progress_path), diff(root))
            prompt_file = ralph_dir / f"prompt-{state.iteration}.md"
            write_text(prompt_file, prompt)

            iteration_artifact: dict[str, Any] = {
                "timestamp": _now(),
                "iteration": state.iteration,
                "launcher": launcher,
                "model": model,
                "task_id": task.get("id"),
                "prompt_file": str(prompt_file),
                "command": None,
                "files_changed": [],
                "validation": {"ok": None, "output": ""},
                "commit": None,
                "summary": "",
                "task_updates_applied": [],
                "task_updates_ignored": [],
                "blockers": [],
                "error": None,
            }

            try:
                launcher_result = LauncherResult(command="", raw_output="")
                if not dry_run:
                    launcher_result = invoke_launcher(launcher, model, prompt_file, config.get("adapter", {}), root)
                iteration_artifact["command"] = launcher_result.command
                iteration_artifact["summary"] = launcher_result.summary
                iteration_artifact["blockers"] = launcher_result.blockers

                updated, ignored = _apply_task_updates_from_launcher(prd, launcher_result, str(task.get("id")))
                iteration_artifact["task_updates_applied"] = updated
                iteration_artifact["task_updates_ignored"] = ignored

                valid, validation_out = _run_validation(root, config.get("validate_command", "./validate.sh"))
                iteration_artifact["validation"] = {"ok": valid, "output": validation_out[:2000]}
                iteration_artifact["files_changed"] = changed_files(root)

                append_text(
                    progress_path,
                    f"[{_now()}] iter={state.iteration} launcher={launcher} model={model} task={task.get('id')} "
                    f"files={len(iteration_artifact['files_changed'])} validate={'ok' if valid else 'fail'}\n",
                )

                if not valid:
                    failures += 1
                    state.last_error = validation_out[:1000]
                    if failures >= int(config.get("max_consecutive_failures", 3)):
                        state.mode = "blocked"
                        state.review_needed = True
                        write_json(state_path, state.to_dict())
                        append_text(progress_path, f"[{_now()}] BLOCKED: repeated validation failures\n")
                        iteration_artifact["error"] = "repeated validation failures"
                        write_json(ralph_dir / f"iteration-{state.iteration}.json", iteration_artifact)
                        return
                else:
                    failures = 0
                    if task.get("status") in {"todo", "in_progress", "blocked"}:
                        task["status"] = "done"
                        iteration_artifact["task_updates_applied"].append(f"{task.get('id')}:done (validation fallback)")
                    write_json(prd_path, prd)

                if config.get("auto_commit", True) and not no_commit and not dry_run:
                    commit_hash = commit_all(root, f"ralph-loop: iter {state.iteration} task {task.get('id')}")
                    state.last_commit = commit_hash
                    iteration_artifact["commit"] = commit_hash

                write_json(state_path, state.to_dict())
                write_json(ralph_dir / f"iteration-{state.iteration}.json", iteration_artifact)

            except (AdapterError, GitError, Exception) as e:  # noqa: BLE001
                failures += 1
                state.last_error = str(e)
                iteration_artifact["error"] = str(e)
                append_text(progress_path, f"[{_now()}] ERROR iter={state.iteration}: {e}\n")
                write_json(ralph_dir / f"iteration-{state.iteration}.json", iteration_artifact)
                if failures >= int(config.get("max_consecutive_failures", 3)):
                    state.mode = "blocked"
                    state.review_needed = True
                    write_json(state_path, state.to_dict())
                    return
                write_json(state_path, state.to_dict())

        state.mode = "blocked"
        state.review_needed = True
        state.last_error = "max iterations reached"
        write_json(state_path, state.to_dict())
        append_text(progress_path, f"[{_now()}] BLOCKED: max iterations reached\n")
    except KeyboardInterrupt:
        state.mode = "paused"
        state.last_error = "interrupted"
        write_json(state_path, state.to_dict())
        append_text(progress_path, f"[{_now()}] PAUSED: interrupted by operator\n")
