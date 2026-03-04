from __future__ import annotations

import argparse
from pathlib import Path

from .engine import init_project, run_loop
from .io import read_json


def cmd_init(args: argparse.Namespace) -> None:
    init_project(Path(args.root).resolve())
    print("Initialized ralph project scaffold.")


def cmd_run(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    prd_path = Path(args.prd).resolve()
    config_path = Path(args.config).resolve() if args.config else None
    run_loop(
        root=root,
        prd_path=prd_path,
        config_path=config_path,
        launcher=args.launcher,
        model=args.model,
        max_iterations=args.max_iterations,
        no_commit=args.no_commit,
        dry_run=args.dry_run,
    )
    print("Run finished. Check ralph/loop-state.json and ralph/progress.log")


def cmd_resume(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    prd = root / "ralph" / "prd.json"
    config = root / "ralph" / "config.json"
    run_loop(
        root=root,
        prd_path=prd,
        config_path=config,
        launcher=args.launcher,
        model=args.model,
        max_iterations=args.max_iterations,
        no_commit=args.no_commit,
        dry_run=args.dry_run,
    )
    print("Resume finished.")


def cmd_status(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    st = read_json(root / "ralph" / "loop-state.json")
    prd = read_json(root / "ralph" / "prd.json")
    done = sum(1 for t in prd.get("tasks", []) if t.get("status") == "done")
    total = len(prd.get("tasks", []))
    print(f"mode={st.get('mode')} iter={st.get('iteration')} review_needed={st.get('review_needed')}")
    print(f"tasks={done}/{total} done")
    if st.get("last_error"):
        print(f"last_error={st.get('last_error')}")


def cmd_validate(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    import subprocess

    proc = subprocess.run(args.command or "./validate.sh", cwd=root, shell=True)
    raise SystemExit(proc.returncode)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ralph-loop")
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--root", default=".")
    p_init.set_defaults(func=cmd_init)

    p_run = sub.add_parser("run")
    p_run.add_argument("--root", default=".")
    p_run.add_argument("--prd", default="ralph/prd.json")
    p_run.add_argument("--config")
    p_run.add_argument("--launcher", choices=["codex", "claude-code"])
    p_run.add_argument("--model")
    p_run.add_argument("--max-iterations", type=int)
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--no-commit", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_resume = sub.add_parser("resume")
    p_resume.add_argument("--root", default=".")
    p_resume.add_argument("--launcher", choices=["codex", "claude-code"])
    p_resume.add_argument("--model")
    p_resume.add_argument("--max-iterations", type=int)
    p_resume.add_argument("--dry-run", action="store_true")
    p_resume.add_argument("--no-commit", action="store_true")
    p_resume.set_defaults(func=cmd_resume)

    p_status = sub.add_parser("status")
    p_status.add_argument("--root", default=".")
    p_status.set_defaults(func=cmd_status)

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("--root", default=".")
    p_validate.add_argument("--command")
    p_validate.set_defaults(func=cmd_validate)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
