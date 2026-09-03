# Finish Work

Run the project-local `trellis-finish-work` Skill to wrap up this session.
Code commits belong to workflow Phase 3.4, not this command.

1. Run `python ./.trellis/scripts/get_context.py --mode record`.
2. Classify dirty paths. If any non-bookkeeping path belongs to the current
   task, stop and return to Phase 3.4; do not commit from this command.
3. Archive the current task with `task.py archive` when applicable.
4. Record the session with `add_session.py`; show the archive/journal diff.
5. Obtain fresh user approval before any bookkeeping commit. Never push.

`.agents/skills/trellis-finish-work/SKILL.md` is authoritative for exact
commands, task selection, reporting, and approval boundaries.
