# Validation Policy

## Commands

- Static checks: `<STATIC_CHECKS>`
- Unit/module tests: `<TEST_COMMANDS>`
- Target builds: `<TARGET_BUILD_COMMANDS>`
- Hardware validation: `<HARDWARE_VALIDATION_PROCEDURE>`

## Reporting

Report each category separately as `pass`, `fail`, `not run`, or `not
applicable`, with the exact command or reason. A host build does not prove
hardware behavior. Do not substitute generic Web lint/typecheck commands for
the project-defined checks.

