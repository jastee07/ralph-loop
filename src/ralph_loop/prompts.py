from __future__ import annotations

from pathlib import Path


def compile_prompt(system_prompt: str, iteration_prompt: str, prd_text: str, progress_tail: str, git_diff: str) -> str:
    return (
        f"{system_prompt}\n\n"
        f"{iteration_prompt}\n\n"
        f"## PRD\n{prd_text}\n\n"
        f"## Recent Progress\n{progress_tail}\n\n"
        f"## Git Diff\n{git_diff or '(no diff)'}\n"
    )


def tail_text(path: Path, lines: int = 80) -> str:
    if not path.exists():
        return ""
    content = path.read_text().splitlines()
    return "\n".join(content[-lines:])
