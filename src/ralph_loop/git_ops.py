from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


def run_git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise GitError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def current_branch(repo: Path) -> str:
    return run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")


def ensure_clean_git(repo: Path) -> None:
    status = run_git(repo, "status", "--porcelain")
    if status:
        raise GitError("Git working tree is not clean. Commit/stash first.")


def create_or_switch_branch(repo: Path, branch: str) -> None:
    existing = run_git(repo, "branch", "--list", branch)
    if existing:
        run_git(repo, "checkout", branch)
    else:
        run_git(repo, "checkout", "-b", branch)


def commit_all(repo: Path, message: str) -> str:
    run_git(repo, "add", "-A")
    proc = subprocess.run(["git", "commit", "-m", message], cwd=repo, capture_output=True, text=True)
    if proc.returncode != 0:
        out = (proc.stderr or proc.stdout).strip()
        if "nothing to commit" in out.lower():
            return run_git(repo, "rev-parse", "HEAD")
        raise GitError(out)
    return run_git(repo, "rev-parse", "HEAD")


def diff(repo: Path) -> str:
    return run_git(repo, "diff", "--", ".", check=False)


def changed_files(repo: Path) -> list[str]:
    out = run_git(repo, "status", "--porcelain", check=False)
    files: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if path:
            files.append(path)
    return files
