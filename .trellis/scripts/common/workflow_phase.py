#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow Phase Extraction.

Extracts step-level content from .trellis/workflow.md and optionally filters
platform-specific blocks.

Step ids are full dotted numbers: ``get_step("2.1")`` returns the 2.1 body
*plus* its numbered substeps (``#### 2.1.1``, ``#### 2.1.2``, ...), while
``get_step("2.1.1")`` locates that single substep. Bare major ids (``1``,
``2``, ``3``) stay unresolved and yield empty content.

Platform marker syntax in workflow.md:

    [Claude Code, Cursor, ...]
    agent-capable content
    [/Claude Code, Cursor, ...]

Two platform family aliases exist on top of equality matching: ``[Codex]``
matches ``codex-sub-agent`` and ``codex-inline`` (which never match each
other), and ``[Claude Code]`` matches ``claude`` / ``claude-code``. No
cross-family alias exists.

Provides:
    get_phase_index   - Extract the Phase Index section (no --step)
    get_step          - Extract a single step (#### X.Y[.Z]) section + substeps
    filter_platform   - Strip platform blocks that don't include the given name

``filter_platform`` is only reachable through ``--mode phase``
(``common/git_context.py``); the empty-content check there runs *before*
platform filtering, so a substep whose body is filtered out still exits 0.
"""

from __future__ import annotations

import re

from .paths import DIR_WORKFLOW, get_repo_root


def _workflow_md_path():
    return get_repo_root() / DIR_WORKFLOW / "workflow.md"

# Match a line that *is* a platform marker: "[A, B, C]" or "[/A, B, C]"
_MARKER_RE = re.compile(r"^\[(/?)([A-Za-z][^\[\]]*)\]\s*$")

# Step heading: "#### 1.0 Title", "#### 2.1.1 Title"; capture the full number.
# The old `(\d+\.\d+)` pattern collapsed "2.1.1" to "2.1", which made numbered
# substeps invisible to get_step.
_STEP_HEADING_RE = re.compile(r"^####\s+(\d+(?:\.\d+)+)\b.*$")

# Phase Index starts here; Phase 1/2/3 step bodies follow; ends at Breadcrumbs.
_PHASE_INDEX_HEADING = "## Phase Index"


def _read_workflow() -> str:
    path = _workflow_md_path()
    if not path.exists():
        raise FileNotFoundError(f"workflow.md not found: {path}")
    return path.read_text(encoding="utf-8")


def _parse_marker(line: str) -> tuple[bool, list[str]] | None:
    """Parse a platform marker line.

    Returns:
        (is_closing, [platform_names]) if line is a marker, else None.
    """
    m = _MARKER_RE.match(line)
    if not m:
        return None
    is_closing = m.group(1) == "/"
    names = [p.strip() for p in m.group(2).split(",") if p.strip()]
    return is_closing, names


def get_phase_index() -> str:
    """Return the compact Phase Index summary from workflow.md.

    SessionStart and no-step phase context use this small summary as their
    orientation payload. Detailed Phase 1/2/3 instructions are loaded with
    ``get_step`` on demand. ``[workflow-state:STATUS]`` tag blocks are
    consumed by the per-turn hook, so they're stripped from this output.
    """
    text = _read_workflow()
    lines = text.splitlines()

    start: int | None = None
    end: int | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if start is None and stripped == _PHASE_INDEX_HEADING:
            start = i
            continue
        if start is not None and stripped == "## Phase 1: Plan":
            end = i
            break

    if start is None:
        return ""
    if end is None:
        end = len(lines)

    section = "\n".join(lines[start:end]).rstrip()
    # Strip [workflow-state:STATUS]...[/workflow-state:STATUS] blocks since
    # they're injected separately by inject-workflow-state.py per-turn.
    import re as _re
    tag_re = _re.compile(
        r"\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n.*?\n\s*\[/workflow-state:\1\]\n?",
        _re.DOTALL,
    )
    return tag_re.sub("", section).rstrip() + "\n"


def get_step(step_id: str) -> str:
    """Return the `#### X.Y[.Z]` section matching step_id (header + body).

    Numbered substep merge rules:

    - ``step_id`` ``X.Y`` starts at the exact ``#### X.Y`` heading when it
      exists; otherwise (and only for a dotted id) it falls back to the first
      ``#### X.Y.`` prefix heading, for documents that only ship the substep.
    - Headings whose number equals ``step_id`` or starts with ``step_id + "."``
      belong to the section and stay inside it; any other ``####`` heading ends
      it. A ``####`` heading whose number cannot be parsed ends it too.
    - Bare major ids (``1``, ``2``, ``3``) never fall back, so they still
      return empty and make the CLI exit 2.

    Body also ends at the next `##` heading or a `---` rule line.
    """
    text = _read_workflow()
    lines = text.splitlines()

    start: int | None = None
    for i, line in enumerate(lines):
        m = _STEP_HEADING_RE.match(line)
        if m and m.group(1) == step_id:
            start = i
            break
    if start is None and "." in step_id:
        prefix = step_id + "."
        for i, line in enumerate(lines):
            m = _STEP_HEADING_RE.match(line)
            if m and m.group(1).startswith(prefix):
                start = i
                break
    if start is None:
        return ""

    def _belongs(number: str) -> bool:
        return number == step_id or number.startswith(step_id + ".")

    end: int = len(lines)
    for j in range(start + 1, len(lines)):
        line = lines[j]
        if line.startswith("#### "):
            m = _STEP_HEADING_RE.match(line)
            if m is None or not _belongs(m.group(1)):
                end = j
                break
            continue
        if line.startswith("## "):
            end = j
            break
        # Horizontal rule at column 0
        if line.strip() == "---":
            end = j
            break

    return "\n".join(lines[start:end]).rstrip() + "\n"


# Platform family aliases, keyed by normalized marker/platform name
# (lowercase, '-' / '_' / space stripped). Symmetric by construction:
#
#   [Codex]         <- codex-sub-agent, codex-inline
#   [codex-sub-agent] <- codex only (never codex-inline)
#   [codex-inline]  <- codex only (never codex-sub-agent)
#   [Claude Code]   <- claude, claude-code
#   [claude-code]   <- claude
#
# No cross-family alias exists: `claude` never matches [Codex] and `codex*`
# never matches [Claude Code].
_PLATFORM_FAMILY_ALIASES: dict[str, frozenset[str]] = {
    "codex": frozenset({"codexsubagent", "codexinline"}),
    "codexsubagent": frozenset({"codex"}),
    "codexinline": frozenset({"codex"}),
    "claude": frozenset({"claudecode"}),
    "claudecode": frozenset({"claude"}),
}


def _normalize_platform(name: str) -> str:
    """Lowercase and strip '-' / '_' / spaces for stable comparisons."""
    return name.lower().replace("-", "").replace("_", "").replace(" ", "")


def _platform_matches(platform: str, block_names: list[str]) -> bool:
    """Case-insensitive match with the two platform family aliases.

    Normalization makes ``claude-code`` == ``Claude Code``. On top of
    equality, ``[Codex]`` matches the concrete ``codex-sub-agent`` /
    ``codex-inline`` names (which never match each other), and
    ``[Claude Code]`` matches ``claude``. See ``_PLATFORM_FAMILY_ALIASES``.
    """
    needle = _normalize_platform(platform)
    for name in block_names:
        hay = _normalize_platform(name)
        if needle == hay or needle in _PLATFORM_FAMILY_ALIASES.get(hay, ()):
            return True
    return False


def resolve_effective_platform(platform: str, config: dict) -> str:
    """Map ``codex`` to a dispatch-mode-namespaced virtual platform name.

    When ``--platform codex`` is passed, return ``"codex-sub-agent"`` by
    default or ``"codex-inline"`` when explicitly configured in
    ``.trellis/config.yaml``. ``sub-agent`` remains an alias for ``auto``.
    ``filter_platform`` then surfaces blocks whose marker lists include the
    namespaced name (e.g. ``[codex-sub-agent, ...]`` or ``[codex-inline, Kilo,
    Antigravity, Devin]``).

    Because both namespaced names belong to the ``codex`` family, the
    ``[Codex]`` marker is rendered for either resolved value (see
    ``_PLATFORM_FAMILY_ALIASES``); ``[codex-sub-agent]`` and ``[codex-inline]``
    stay exclusive to their own dispatch mode.

    Native Codex context injection supports the ``auto`` default. Invalid
    explicit values fall back to ``inline`` safely; this renderer deliberately
    does not warn because it can run in normal CLI output flows.

    Other platforms are returned unchanged (``claude`` stays ``claude`` and
    matches ``[Claude Code]`` through the family alias).

    Scope: the only caller is ``--mode phase`` in ``common/git_context.py``;
    SessionStart / Phase Index injection does not run ``filter_platform``.
    """
    if platform == "codex":
        mode = "auto"
        codex_cfg = config.get("codex") if isinstance(config, dict) else None
        if codex_cfg is not None:
            if not isinstance(codex_cfg, dict):
                mode = "inline"
            else:
                cfg_mode = str(codex_cfg.get("dispatch_mode", mode)).strip().lower()
                if cfg_mode == "inline":
                    mode = "inline"
                elif cfg_mode in ("auto", "sub-agent"):
                    mode = "auto"
                else:
                    mode = "inline"
        return "codex-sub-agent" if mode == "auto" else "codex-inline"
    return platform


def filter_platform(content: str, platform: str) -> str:
    """Keep lines outside any `[...]` block + lines inside blocks that include platform.

    Matching is equality after normalization plus the ``codex`` / ``claude``
    family aliases (``_PLATFORM_FAMILY_ALIASES``). Marker lines themselves are
    dropped from the output.

    Callers should note that the CLI's empty-content check runs *before* this
    filter (``common/git_context.py``), so content that becomes empty here
    still exits 0.
    """
    lines = content.splitlines()
    out: list[str] = []

    in_block = False
    keep_block = False

    for line in lines:
        marker = _parse_marker(line)
        if marker is not None:
            is_closing, names = marker
            if not is_closing:
                in_block = True
                keep_block = _platform_matches(platform, names)
            else:
                in_block = False
                keep_block = False
            continue  # drop the marker line itself

        if in_block:
            if keep_block:
                out.append(line)
            continue
        out.append(line)

    # Collapse runs of 3+ blank lines that may arise from dropped markers
    collapsed: list[str] = []
    blank_run = 0
    for line in out:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                collapsed.append(line)
        else:
            blank_run = 0
            collapsed.append(line)

    return "\n".join(collapsed).rstrip() + "\n"
