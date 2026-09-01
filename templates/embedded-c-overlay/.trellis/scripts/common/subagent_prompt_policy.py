"""Conservatively structure and normalize implementer dispatch prompts.

The policy preserves task facts and explicit acceptance commands. It only
rewrites fragmented tool orchestration when it is explicitly placed in an
execution section; unclassified text is retained as business requirements and
is not presented as a mandatory tool sequence.
"""

from __future__ import annotations

import re


_POLICY_MARKER = "[Trellis dispatch policy normalized]"

_SECTION_PATTERNS = (
    ("goal", r"目标|目的|任务目标|goal|objective"),
    ("scope", r"范围|工作范围|scope|in\s+scope"),
    ("non_goals", r"非目标|不包含|排除项|non[- ]?goal|out\s+of\s+scope"),
    ("acceptance", r"验收(?:条件|标准)?|完成条件|acceptance(?:\s+criteria)?|success\s+criteria"),
    ("commands", r"验证命令|检查命令|测试命令|validation\s+commands?|check\s+commands?|test\s+commands?"),
    ("execution", r"执行策略|执行步骤|操作步骤|实施步骤|execution\s+(?:strategy|steps?)|implementation\s+steps?|workflow\s+steps?"),
)
_SECTION_LABELS = {
    "goal": "Goal",
    "scope": "Scope",
    "non_goals": "Non-goals",
    "acceptance": "Acceptance criteria",
    "commands": "Validation commands",
    "execution": "Execution strategy (normalized)",
    "business": "Business requirements (preserved; tool wording is not a mandatory order)",
}


def _remove_exact_injected_duplicates(prompt: str, injected_context: str) -> str:
    """Remove only verbatim, substantial context copies from a dispatch prompt."""
    if not injected_context or not prompt:
        return prompt
    blocks = re.findall(
        r"^=== [^\n]+ ===\n(.*?)(?=^=== |\Z)",
        injected_context,
        re.MULTILINE | re.DOTALL,
    )
    for block in blocks:
        content = block.strip()
        if len(content) < 256 or content not in prompt:
            continue
        prompt = prompt.replace(
            content,
            "[Trellis: this exact context is already injected above; duplicate omitted]",
            1,
        )
    return prompt


def _section_from_line(line: str) -> tuple[str | None, str | None]:
    """Return (section, inline content) for a recognized label, if any."""
    candidate = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)、]\s+)?", "", line).strip()
    candidate = re.sub(r"^#{1,6}\s*", "", candidate).strip()
    candidate = candidate.replace("**", "").replace("__", "").strip()
    for section, pattern in _SECTION_PATTERNS:
        label = rf"(?:{pattern})(?:\s*(?:\([^)]*\)|（[^）]*）))*"
        if re.fullmatch(label, candidate, re.IGNORECASE):
            return section, ""
        match = re.match(rf"{label}\s*(?::|：|-)\s*(.*)$", candidate, re.IGNORECASE)
        if match:
            return section, match.group(1).strip()
    return None, None


def _normalize_execution_line(line: str) -> str:
    """Collapse common per-item tool orchestration into one batch operation."""
    replacements = (
        (r"(?:逐个|逐一|挨个|每一个)\s*(?:检查|扫描|搜索)?\s*(?:所有|全部)?字段", "使用一次批量扫描全部字段"),
        (r"(每个|每一个|每一项|每项|逐个|逐一|挨个|各个|每处)([^\n。；;]{0,80}?)(?:单独|分别)(?:\s*(?:执行|运行))?\s*`?(?:grep|搜索|扫描|检查)`?", r"使用一次批量扫描全部\2"),
        (r"(每个|每一个|每一项|每项|逐个|逐一|挨个|各个|每处)([^\n。；;]{0,80}?)(?:单独|分别)\s*(?:执行|运行)\s*(?:命令|检查)", r"使用一次批量命令统一检查全部\2"),
        (r"(?:每个|每一个|每一项|每项|逐个|逐一|挨个|各个|每处)([^\n。；;]{0,80}?)(?:单独|分别)\s*(?:检查|扫描|搜索)", r"使用一次批量扫描全部\1"),
        (r"(?:逐个|逐一|挨个|每一个)\s*`?(?:grep|搜索|扫描|检查)`?", "使用一次批量扫描全部目标"),
        (r"(?:逐个|逐一|挨个|每一个)\s*(?:执行|运行)\s*(?:命令|检查)", "使用一次批量命令统一检查全部目标"),
        (r"每删一个的零调用者证据\s*(?:grep|扫描)\s*结果", "一次批量调用者扫描并输出每项零调用者证据"),
        (r"每项\s*单独\s*(?:构建|编译)", "按阶段统一构建一次"),
        (r"每处\s*(?:重新)?(?:构建|编译)", "按阶段统一构建一次"),
        (r"每次(?:修改|改动|编辑)后(?:立即)?(?:进行)?(?:完整)?(?:地)?(?:重新)?(?:扫描|构建|编译)", "阶段修改完成后统一验证一次"),
        (r"每次修改后(?:立即)?(?:进行)?完整(?:地)?扫描", "阶段修改完成后统一扫描"),
        (r"完成前必须逐条执行并在报告中附证据", "完成前统一执行批量验证，并在报告中逐项列出证据"),
        (r"判定必须逐个\s*", "判定使用批量扫描并逐项报告："),
        (r"for\s+each\s+([^\n,;:]+),?\s+run\s+(?:grep|search|check)", r"run one batch scan for all \1"),
        (r"run\s+(?:grep|search|check)\s+separately\s+for\s+each\s+([^\n,;:]+)", r"run one batch scan for all \1"),
        (r"run\s+each\s+command\s+separately", "run one batched command for the complete set"),
        (r"rebuild\s+after\s+every\s+(?:small\s+)?change", "rebuild once after the phase is complete"),
    )
    result = line
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def _structure_prompt(prompt: str) -> tuple[str, bool, bool, bool]:
    segments: list[tuple[str, list[str]]] = []
    current = "business"
    in_fence = False
    changed_execution = False
    recognized_section = False

    def append_line(section: str, line: str) -> None:
        if segments and segments[-1][0] == section:
            segments[-1][1].append(line)
        else:
            segments.append((section, [line]))

    for raw_line in prompt.splitlines():
        if raw_line.strip().startswith("```"):
            in_fence = not in_fence
            append_line(current, raw_line)
            continue

        section, inline = _section_from_line(raw_line) if not in_fence else (None, None)
        if section:
            recognized_section = True
            current = section
            if inline:
                if current == "execution" and not in_fence:
                    normalized_inline = _normalize_execution_line(inline)
                    changed_execution = changed_execution or normalized_inline != inline
                    inline = normalized_inline
                append_line(current, inline)
            continue

        if current == "execution" and not in_fence and re.match(
            r"^\s*(?:#{1,6}\s+|\*\*[^*]+\*\*\s*[:：])", raw_line
        ):
            current = "business"
        line = raw_line
        if current == "execution" and not in_fence:
            normalized = _normalize_execution_line(line)
            changed_execution = changed_execution or normalized != line
            line = normalized
        append_line(current, line)

    rendered: list[str] = []
    for key, values in segments:
        while values and not values[0].strip():
            values.pop(0)
        while values and not values[-1].strip():
            values.pop()
        if not values:
            continue
        rendered.append(f"## {_SECTION_LABELS[key]}")
        rendered.extend(values)

    structured = "\n".join(rendered).strip() or prompt.strip()
    return structured, changed_execution, any(key == "business" for key, _ in segments), recognized_section


def normalize_implement_prompt(prompt: str, injected_context: str = "") -> str:
    """Structure dispatch requirements without changing their business meaning."""
    if not isinstance(prompt, str) or not prompt.strip():
        return prompt

    deduplicated = _remove_exact_injected_duplicates(prompt, injected_context)
    structured, changed_execution, _has_business, recognized_section = _structure_prompt(deduplicated)
    if not recognized_section and "## Business requirements (preserved" not in structured:
        structured = (
            "## Business requirements (preserved; tool wording is not a mandatory order)\n"
            + structured
        )
    note = (
        "已保留任务目标、范围、非目标、验收条件和验证命令；仅对明确位于执行策略分区的碎片化工具编排做批量化改写。"
        if changed_execution
        else "未识别为执行策略的原始内容按业务要求保留，其中的工具措辞不构成强制执行顺序。"
    )
    return f"{structured}\n\n{_POLICY_MARKER}\n{note}"


def policy_marker() -> str:
    """Return the stable marker used by prompt and behavior tests."""
    return _POLICY_MARKER


def execution_contract() -> str:
    """Return the shared runtime contract for implementer dispatch."""
    return (
        "Preserve task scope, acceptance criteria, and required validation commands. "
        "Treat per-item wording as report granularity, not one tool call per item. "
        "Batch independent reads and searches; perform targeted follow-up only when "
        "a batch result proves it is needed. Do not rebuild for comment or historical "
        "documentation matches. After a real code fix, rerun only affected checks "
        "and stop when scope, evidence, verification, and report are complete."
    )
