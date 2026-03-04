from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json


DEFAULT_CONFIG: dict[str, Any] = {
    "launcher": "codex",
    "model": "openai-codex/gpt-5.3-codex",
    "max_iterations": 30,
    "max_consecutive_failures": 3,
    "max_runtime_minutes": 120,
    "require_clean_git": True,
    "auto_commit": True,
    "auto_push": False,
    "allow_destructive_git": False,
    "require_pr_before_merge": True,
    "review_needed": False,
    "validate_command": "./validate.sh",
    "adapter": {
        "codex_command": "codex --model {model} --prompt-file {prompt_file}",
        "claude_command": "claude code --model {model} --prompt-file {prompt_file}",
    },
}


def load_config(path: Path | None) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if path and path.exists():
        incoming = read_json(path)
        config.update(incoming)
    return config
