# Third-Party Notice

`templates/embedded-c-overlay/.agents/skills/grill-me/` is the upstream
Codex Grill Me skill copied for direct project-local installation. Its intended
source and pinned revision are:

```text
repository: mio-openliven/codex-grill-me-skill
path: skills/grill-me
revision: b76d047529a9873331ce2d7fa5516b22651f7ace
```

Keep upstream Grill Me semantics separate from the project adapter. Project
Trellis policy belongs in `__PROJECT_PREFIX__-trellis-grill-adapter`, not in
the copied upstream skill.

