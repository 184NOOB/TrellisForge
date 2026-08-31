---
name: grill-me
description: Relentlessly interview the user about a plan, product decision, architecture, UX design, or release risk until shared understanding is reached. Use when the user asks to stress-test a plan, says "grill me", asks for ruthless questions, or when a critical decision tree cannot be safely resolved from code or local context alone.
---

# Grill Me

Use this skill to turn vague or risky plans into clear decisions.

## Core Rules

- Ask one question at a time.
- For each question, include your recommended answer.
- Walk the decision tree branch by branch; resolve dependencies before moving on.
- If a question can be answered by reading code, docs, tests, logs, configs, or local files, inspect those first instead of asking the user.
- Do not grill the user about small choices that can be safely decided from project patterns.
- Stop grilling once the remaining decisions are low-risk or implementation is clear.

## Question Shape

Use this format:

```text
Question:
[one concrete question]

Recommended answer:
[what I would choose and why]

Why it matters:
[risk or dependency unlocked by the answer]
```

## Decision Discipline

- Separate facts from assumptions.
- Name tradeoffs plainly.
- Push back when an answer would grow scope, hide risk, or weaken the release.
- When the user gives an answer, summarize the decision in one sentence and continue to the next unresolved branch.
- If the user gets frustrated, narrow the next question instead of explaining the whole tree.

## When To Stop

Stop and switch back to execution when:

- the critical branch is resolved;
- there is a safe conservative default;
- more questions would only polish wording;
- the next step is clearly a code change, test, doc update, or handoff.
