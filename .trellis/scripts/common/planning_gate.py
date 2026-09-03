"""Project-local planning convergence gate for ``task.py start``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .io import read_json


@dataclass(frozen=True)
class PlanningGateResult:
    """Result returned before a planning task may enter implementation."""

    ok: bool
    errors: tuple[str, ...] = ()


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _markdown_section(text: str, heading: str) -> str | None:
    pattern = re.compile(
        rf"^##[ \t]+{re.escape(heading)}[ \t]*$\n(.*?)(?=^##[ \t]+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1) if match else None


def _list_field(section: str, label: str) -> str | None:
    pattern = re.compile(
        rf"^-[ \t]+{re.escape(label)}[ \t]*:[ \t]*(.*?)[ \t]*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = pattern.search(section)
    return match.group(1).strip() if match else None


def validate_planning_gate(task_dir: Path) -> PlanningGateResult:
    """Validate persisted convergence and approval before status mutation.

    Tasks already beyond ``planning`` are re-attachments and do not pass
    through this phase-transition gate again.
    """

    task_json = task_dir / "task.json"
    data = read_json(task_json) if task_json.is_file() else None
    if not isinstance(data, dict):
        return PlanningGateResult(False, ("task.json is missing or invalid",))
    if data.get("status") != "planning":
        return PlanningGateResult(True)

    errors: list[str] = []
    meta = data.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    if not _as_bool(meta.get("planning_ready")):
        errors.append("task metadata planning_ready must be true after convergence")
    if not _as_bool(meta.get("plan_approved")):
        errors.append("task metadata plan_approved must be true after subsequent user approval")

    prd_path = task_dir / "prd.md"
    try:
        prd = prd_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return PlanningGateResult(False, tuple(errors + ["prd.md is missing or not valid UTF-8"]))

    workflow = _markdown_section(prd, "Workflow Settings")
    review_level = _list_field(workflow, "Review level") if workflow else None
    if review_level not in {"light", "standard", "strict"}:
        errors.append("prd.md must contain Workflow Settings with Review level: light|standard|strict")

    convergence = _markdown_section(prd, "Planning Convergence")
    if convergence is None:
        errors.append("prd.md must contain a Planning Convergence section")
    else:
        expected = {
            "Status": "ready",
            "Blocking user decisions": "0",
            "Blocking technical decisions": "0",
            "Final summary ready": "yes",
        }
        for label, expected_value in expected.items():
            actual = _list_field(convergence, label)
            if actual is None or actual.lower() != expected_value:
                errors.append(f"Planning Convergence requires {label}: {expected_value}")

    return PlanningGateResult(not errors, tuple(errors))
