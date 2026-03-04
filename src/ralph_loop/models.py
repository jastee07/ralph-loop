from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LoopState:
    run_id: str
    iteration: int = 0
    mode: str = "paused"
    last_task_id: str | None = None
    last_commit: str | None = None
    review_needed: bool = False
    last_error: str | None = None
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["updated_at"] = now_iso()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoopState":
        return cls(**data)
