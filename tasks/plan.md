# Plan: Remove legacy plugins and standardize Pydantic validation

Proposed 2026-10-28. Implemented; verification notes follow.

## Review conclusions

- Remove QueueRunner and ConnectionsPool as requested. Both are public plugin entry points, although no internal consumer of ConnectionsPool was found beyond its exports/registration. External use cannot be ruled out; release notes must identify the breaking removals.
- yangdantic.py is actively imported by 21 task modules, with 32 decorated functions. Keep its useful implementation under `nornir_salt/utils/validation.py`, retain the name `ValidateFuncArgs`, update all callers, and delete the old module. Do not retain an alias unless compatibility is explicitly requested.
- Every existing decorator call supplies an explicit model. Remove the unused model-free inference/configuration branch rather than repairing unused functionality. This retires registry R07 by removing that path.
- Preserve third-party argument mixins: Netmiko, NAPALM and Scrapli use them. These extend explicit Pydantic models; they are not a separate validation engine.
- `pyats.connections.pool.ConnectionPool` in pyats_send_commands is a different dependency feature and remains.
- All input validation must use Pydantic models. Field constraints, field/model validators and Pydantic validation errors are the single policy mechanism. Runtime failures and type-based result transformation remain ordinary implementation logic; an isinstance is not automatically an input validator.

## Validation design

`pydantic_models.py` holds input schemas; `validation.py` binds function arguments and invokes those schemas. Require `type[BaseModel]`, not a model instance. Cache the function signature and the final mixin-augmented model per decorated function, using Pydantic 2 class-level model_fields and ConfigDict where required. Remove construct()/__fields__ use. Avoid function-specific cached state shared across unrelated decorations.

Use Python signature binding to handle positional, keyword-only, default, variadic and duplicate arguments correctly, preserving Python call errors. Flatten bound **kwargs into the schema input without losing passthrough arguments. Binding errors are Python calling-convention errors; application value validation belongs to Pydantic.

The current decorator discards the validated model and invokes the function with original arguments. Therefore accepted coercions do not reach the task. For this change preserve check-only invocation behavior and object identity, and tighten schemas to reject representations a function cannot actually consume. Preserve intentional existing input forms explicitly. Do not silently switch every task to model_dump output: it can serialize live Task/Host objects and change passthrough behavior. Any intentional normalization must be explicit, consumed by the caller and tested as a separate contract change.

Preserve current unknown-key policies per model: tasks forwarding third-party kwargs must not suddenly reject them. Mixins must tolerate unavailable optional dependencies, preserve base-field precedence, skip return/self/variadic names, include keyword-only fields and allow omission without automatically accepting explicit None for non-nullable fields.

Audit direct model consumers too: not every boundary needs the decorator. RetryRunner already uses an explicit model. Processors, inventory constructors, functions and connection open parameters must also validate through models where they enforce input contracts.

Replace assert-based checks in modelTestsProcessorTest's model validator with explicit ValueError/Pydantic errors and safe missing-field handling. Optimization must not disable validation. Schema/data testing features such as CerberusTest remain supported: validating user-selected device data against a test schema is distinct from validating Nornir-Salt function/configuration inputs.

## Ordered implementation

1. Remove QueueRunner source, runner exports/entry point, QueueRunner-only test and its registration. Remove its Sphinx page, toctree entry, diagram assets and active examples/comments. Keep RetryRunner tests and historical release notes.
2. Remove ConnectionsPool source, exports and entry point. Check package imports and wheel entry-point metadata; preserve PyATS's unrelated pool.
3. Introduce focused offline validation tests, then move/simplify the decorator in validation.py with explicit models and cached metadata. Verify missing optional mixins, binding, strictness, defaults, extra kwargs, object identity and concurrent use.
4. Migrate imports in small task-family batches (connections/files/http/network; Netmiko/NAPALM/Scrapli; remaining task modules). Each batch must import and pass its focused tests. Delete yangdantic.py only after all active callers migrate.
5. Inventory every input boundary/manual rejection in an explicit checklist. Migrate by subsystem: task inputs (tcp_ping is a known gap), inventory/functions (DictInventory and InventoryFun), processor constructors/options, then connection plugin inputs. Reuse existing models; add missing models and cross-field rules. Correct assertion-based model checks. Keep intentional coercions/forms documented and test rejected inputs before side effects. This is a separate repository-wide workstream, not a filename-only cleanup.
6. Document removals, new validation path and error behavior; annotate the private registry R01/R02/R03/R04/R11 as retired by removal, R07 as retired by deleting unused inference, and R14 according to actual decorator verification. Other findings remain open. Build and inspect a fresh wheel, test installed entry points/imports, run offline regressions and Sphinx checks.

Track execution in tasks/todo.md. Each subsystem migration should stay in a focused commit; do not combine unrelated review fixes, dependency upgrades or CI modernization with this work.

## Acceptance and verification

- No active source, export, entry point, test or documentation page references either removed plugin or old validation import. Historical changelog mentions and private review artifacts remain valid history.
- Fresh wheel has no removed modules/diagram assets or entry points; RetryRunner still imports and registers. Reinstall in a fresh environment to avoid stale installed metadata masking removals.
- All 32 existing decorated functions retain validation and task metadata through functools.wraps, including RetryRunner's CONNECTION_NAME discovery.
- Invalid inputs produce Pydantic validation errors before network/file/thread side effects; Python binding errors retain ordinary TypeError behavior. No newly introduced hand-written value validation outside model validators.
- Test model constraints under normal Python and python -O so assertions cannot disable enforcement. Invalid missing fields yield structured validation errors rather than KeyError.
- Model composition occurs once per decorated function, remains safe under concurrent invocation and does not require an optional integration dependency to be installed.
- Run focused offline tests, the established offline suite, formatting/lint checks without auto-fix, wheel build/install/import/entry-point checks and Sphinx build. Lab integration is a separately reported check; do not claim coverage from unavailable devices.

## Risks and boundaries

Plugin removals and old module-path deletion intentionally break downstream configuration/imports. Document migration to Nornir's built-in runner where appropriate or RetryRunner with explicit retry settings; do not claim identical semantics. There is no automatic pool replacement.

Repository-wide model enforcement can change accepted inputs and error classes. Characterize each boundary before migration, retain runtime operational errors, and avoid global strict/extra policies imposed without tests. This work is larger than deleting the two plugins; implementation should report progress per subsystem.

## Implementation notes ? 2026-10-28

Implemented the focused changes with no new helper functions beyond Pydantic validators and the existing decorator wrapper. Validation audit:

- Tasks: existing explicit-model decorators migrated; tcp_ping gained a model; file_diff indexes and config dry_run checks moved into models.
- Inventory/functions: existing inventory model owns group references; update_host and MakePlugin use models. No changes to inventory batch mutation (R12).
- Processors: DataProcessor options/path, ToFileProcessor, DiffProcessor and TestsProcessor options use models; rendered-list validation and test-suite required fields use models. Result-type errors, custom/Cerberus data testing and operational failures retain their existing semantics.
- Connections: all five retained connection open methods use a common input model; resolved credential mappings and jumphost trust policy are validated by models. Integration libraries continue to own protocol-specific extras.
- Runtime callbacks and opaque integration objects did not acquire speculative new schemas; existing input contract checks were migrated rather than redesigning every interface.

Verification: 443 offline tests pass (4 device-dependent runner tests deselected); 26 focused validation tests also pass under python -O. Changed-file Black checks and undefined-name/syntax checks pass; Sphinx HTML build succeeds. Wheel/sdist and installed-package checks recorded in private/validation_wheel_check.txt. Full live-device integration and other Python versions were not exercised. No dependency changes or unrelated registry fixes included.
