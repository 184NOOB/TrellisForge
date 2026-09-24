"""Project-local planning convergence gate for ``task.py start``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re

from .io import read_json
from .task_store import _has_subagent_platform


# Fixed strength order: light < standard < reinforced < comprehensive < strict.
# Consumers (workflow, review Skill, grill adapter, Check Agents) must accept
# exactly this set; see tests/test_review_profile_contract.py.
VALID_REVIEW_LEVELS: tuple[str, ...] = (
    "light",
    "standard",
    "reinforced",
    "comprehensive",
    "strict",
)


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


# Any markdown list item (indentation tolerated). Checked inside the
# ``## Spec References`` section body only.
_SPEC_LIST_ITEM = re.compile(r"^[ \t]*-[ \t]+", re.MULTILINE)

# Manifest file names curated by the AI during planning.
_MANIFEST_FILES = ("implement.jsonl", "check.jsonl")


def _missing_spec_references(prd: str) -> bool:
    """True when `prd.md` lacks a non-empty `## Spec References` section."""
    section = _markdown_section(prd, "Spec References")
    return section is None or _SPEC_LIST_ITEM.search(section) is None


def _manifest_problem(name: str, path: Path) -> str | None:
    """Describe why a curated manifest fails the start gate, else None.

    A real entry is a JSON object line with a non-empty string ``file`` field;
    the seed ``_example`` row has no ``file`` field. Missing files and broken
    JSON lines fail closed instead of being tolerated.
    """
    if not path.is_file():
        return (
            f"{name} is missing; append at least one curated entry with "
            "`task.py add-context` (seed rows do not satisfy the start gate)"
        )
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return f"{name} is missing or not valid UTF-8"
    has_entry = False
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return f"{name} contains a line that is not valid JSON"
        if isinstance(entry, dict):
            value = entry.get("file")
            if isinstance(value, str) and value.strip():
                has_entry = True
    if has_entry:
        return None
    return f"{name} must contain at least one curated entry; seed _example rows do not count"


def validate_planning_gate(
    task_dir: Path, repo_root: Path | None = None
) -> PlanningGateResult:
    """Validate persisted convergence and approval before status mutation.

    Tasks already beyond ``planning`` are re-attachments and do not pass
    through this phase-transition gate again.

    When ``repo_root`` is provided and the repository has a sub-agent-dispatch
    platform, both curated manifests must also carry at least one real entry.
    Callers that omit ``repo_root`` keep the legacy behavior (JSONL check
    skipped).
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
    if review_level not in VALID_REVIEW_LEVELS:
        errors.append(
            "prd.md must contain Workflow Settings with Review level: "
            + "|".join(VALID_REVIEW_LEVELS)
        )

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

    if _missing_spec_references(prd):
        errors.append(
            "prd.md must contain a Spec References section listing consulted "
            "spec files (or an explicit none-applicable entry)"
        )

    if repo_root is not None and _has_subagent_platform(repo_root):
        for name in _MANIFEST_FILES:
            problem = _manifest_problem(name, task_dir / name)
            if problem:
                errors.append(problem)

    return PlanningGateResult(not errors, tuple(errors))
