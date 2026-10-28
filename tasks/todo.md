# Tasks: plugin removal and Pydantic validation

Implementation checklist for tasks/plan.md. Implemented 2026-10-28; verification evidence is recorded in plan.md.

- [x] 1. Remove QueueRunner runtime/export/entry point and its isolated test. Verify RetryRunner tests still collect and its exports remain intact. Dependencies: none.
- [x] 2. Remove QueueRunner documentation page, toctree link, diagram assets and active examples. Keep historical release notes. Verify active-reference search. Depends on 1.
- [x] 3. Remove ConnectionsPool source/export/entry point. Verify connection package imports, preserve PyATS pool and inspect built metadata. Dependencies: none.
- [x] Checkpoint A: removed plugins have no active registrations/references; retained plugins import.
- [x] 4. Add focused characterization/regression tests for ValidateFuncArgs, binding, optional mixins, model strictness, passthrough and Task/Host identity. Tests live in a dedicated offline module. Dependencies: none.
- [x] 5. Implement explicit-model-only validation.py, cached signatures/final models and Pydantic 2 field inspection. Verify focused tests, concurrent calls, wraps metadata and optional-dependency absence. Depends on 4.
- [x] 6. Migrate connections/files/http/network imports; run focused offline task tests. Depends on 5.
- [x] 7. Migrate Netmiko/NAPALM/Scrapli imports; verify mixin precedence/defaults/keyword-only/extra behavior. Depends on 5.
- [x] 8. Migrate remaining task imports; delete yangdantic.py after active import search is clear. Verify all 21 importing modules. Depends on 6–7.
- [x] Checkpoint B: explicit model validation remains on all 32 decorated functions; no old module imports; composed models are cached.
- [x] 9. Record complete boundary/model coverage checklist across tasks, functions, inventory, processors and connections, separating input rejection from runtime/result logic. Dependencies: none.
- [x] 10. Migrate uncovered task argument validation to models, beginning with tcp_ping; split into small task-family changes. Verify all intended input forms and side-effect-free rejection. Depends on 5,9.
- [x] 11. Migrate inventory/function input validation in small subsystem changes. Verify cross-field rules and inherited/defaulted values. Depends on 9.
- [x] 12. Migrate processor input validation and replace assertions in test-suite model validators. Verify invalid missing fields, normal and optimized Python. Depends on 9.
- [x] 13. Migrate uncovered connection input validation; preserve third-party extras policies and operational exceptions. Depends on 9.
- [x] Checkpoint C: coverage checklist complete; all input contract enforcement uses Pydantic models with regression tests.
- [x] 14. Write release/migration notes and update private findings statuses without closing unrelated findings. Depends on 1–13.
- [x] 15. Run retained offline regressions, formatting/lint checks, Sphinx, wheel build and fresh installation/entry-point inspection. Report integration limitations explicitly. Depends on 14.
- [x] Final checkpoint: review diff against requested scope; verify no compatibility shims, accidental PyATS pool removal, stale entry points or unrelated fixes.
