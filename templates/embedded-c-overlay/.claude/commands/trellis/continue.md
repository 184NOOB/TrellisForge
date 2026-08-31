# Continue Current Task

Resume the current task by following `.trellis/workflow.md` and the project
local Trellis Skills.

1. Run `python ./.trellis/scripts/get_context.py` and
   `python ./.trellis/scripts/get_context.py --mode phase`.
2. Route from the task status and artifact presence; do not infer a phase from
   memory.
3. Load the specific step with `--step <X.X> --platform claude`.
4. Keep required steps in order. `task.py start` still requires planning
   convergence and subsequent user approval.

This command is only a routing entry point; the workflow and Skills are
canonical.
