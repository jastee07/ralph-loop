from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


class AdapterError(RuntimeError):
    pass


@dataclass
class LauncherResult:
    command: str
    raw_output: str
    summary: str = ""
    claimed_task_updates: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


def _parse_output(raw_output: str) -> tuple[str, list[dict[str, Any]], list[str]]:
    """
    Expected structured shape (optional):
    {
      "summary": "...",
      "claimed_task_updates": [{"id": "task-1", "status": "done", "reason": "..."}],
      "blockers": ["..."]
    }
    If launcher output isn't valid JSON, keep raw as summary fallback.
    """
    if not raw_output:
        return "", [], []

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return raw_output.strip(), [], []

    if not isinstance(parsed, dict):
        return raw_output.strip(), [], []

    summary = str(parsed.get("summary") or "").strip()
    updates = parsed.get("claimed_task_updates")
    blockers = parsed.get("blockers")

    safe_updates = updates if isinstance(updates, list) else []
    safe_blockers = [str(b) for b in blockers] if isinstance(blockers, list) else []
    return summary, safe_updates, safe_blockers


def invoke_launcher(
    launcher: str,
    model: str,
    prompt_file: Path,
    adapter_cfg: dict,
    cwd: Path,
) -> LauncherResult:
    if launcher == "codex":
        template = adapter_cfg.get("codex_command", "codex --model {model} --prompt-file {prompt_file}")
    elif launcher in {"claude", "claude-code"}:
        template = adapter_cfg.get("claude_command", "claude code --model {model} --prompt-file {prompt_file}")
    else:
        raise AdapterError(f"Unsupported launcher: {launcher}")

    command = template.format(model=model, prompt_file=str(prompt_file))
    proc = subprocess.run(shlex.split(command), cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AdapterError(proc.stderr.strip() or proc.stdout.strip() or f"launcher failed: {command}")

    raw_output = proc.stdout.strip()
    summary, claimed_task_updates, blockers = _parse_output(raw_output)
    return LauncherResult(
        command=command,
        raw_output=raw_output,
        summary=summary,
        claimed_task_updates=claimed_task_updates,
        blockers=blockers,
    )
