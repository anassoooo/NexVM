# Implementation Checklist: VM Management

**Purpose**: Validate requirement quality and cross-artifact consistency both before and after implementation  
**Created**: 2026-04-06  
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [tasks.md](../tasks.md)  
**Focus**: Full coverage — security, state machine, API contracts, frontend  
**Depth**: Standard (~35 items)  
**Timing**: Pre-implementation readiness + post-implementation quality gate

---

## Requirement Completeness

- [ ] CHK001 - Are all 20 functional requirements (FR-001 through FR-020) traceable to at least one task in tasks.md? [Completeness, Spec §FR]
- [ ] CHK002 - Are the six VBoxManage whitelisted commands in the spec (FR-017) consistent with the five listed in contracts/vbox-commands.md? [Consistency, Spec §FR-017 vs Contract]
- [ ] CHK003 - Is FR-014 (logging before response) consistently reflected in the task descriptions for all six operations in T002? [Consistency, Spec §FR-014 vs Tasks §T002]
- [ ] CHK004 - Are the error response status codes in the spec edge cases (e.g., 503 for VBoxManage not installed) documented in the API contract? [Completeness, Spec §Edge Cases vs Contract]
- [ ] CHK005 - Is the `os` field validation requirement (free text, non-empty) consistently specified across spec FR-001, data-model validation summary, and the VMCreate Pydantic schema? [Consistency]
- [ ] CHK006 - Are the exact VM name validation rules (regex pattern) consistently defined across spec FR-016, data-model validation summary, and the VMCreate schema in data-model.md? [Consistency, Spec §FR-016 vs Data Model]

## State Machine Clarity

- [ ] CHK007 - Does the state machine diagram in data-model.md match the valid transitions described in spec FR-005, FR-007, FR-009? [Consistency, Data Model §State Machine vs Spec]
- [ ] CHK008 - Is the "error → starting" retry transition explicitly specified in both the state machine table and a spec functional requirement? [Completeness, Spec §FR-005 vs Data Model]
- [ ] CHK009 - Are concurrency guards (409 on transitional states) specified with identical triggering conditions in FR-009 and the API contract error tables? [Consistency, Spec §FR-009 vs Contract]
- [ ] CHK010 - Is the behavior when VBoxManage succeeds but the subsequent DB write fails fully specified beyond "mismatch is logged"? [Clarity, Spec §Edge Cases]
- [ ] CHK011 - Is `updated_at` update behavior documented consistently between the API contract (service layer sets it) and the data model? [Consistency, Contract §Common Patterns vs Data Model]

## API Contract Consistency

- [ ] CHK012 - Do all six endpoint paths in the API contract match the routes defined in T004? [Consistency, Contract vs Tasks §T004]
- [ ] CHK013 - Are the HTTP status codes for each endpoint consistent across the spec acceptance scenarios and the API contract error tables? [Consistency, Spec §Acceptance Scenarios vs Contract]
- [ ] CHK014 - Is the `VMActionRequest` schema in data-model.md (single `vm_id` field) consistent with how T004 defines the POST body for start/stop/delete/status? [Consistency, Data Model vs Tasks §T003-T004]
- [ ] CHK015 - Is the 404 response for cross-user VM access documented identically in FR-015 and all relevant API contract error tables? [Consistency, Spec §FR-015 vs Contract]
- [ ] CHK016 - Are timeout error responses specified in the API contract for all endpoints that invoke VBoxManage (create, start, stop)? [Completeness, Contract]

## Task Coverage

- [ ] CHK017 - Does T002 `create_vm` specify handling for all three VBoxManage failure modes: non-zero generic exit, name conflict ("already exists"), and binary not found (FileNotFoundError)? [Completeness, Tasks §T002]
- [ ] CHK018 - Are the 18 test cases in T006 mapped one-to-one to acceptance scenarios in the spec, and are any spec scenarios uncovered? [Coverage, Tasks §T006 vs Spec §Acceptance Scenarios]
- [ ] CHK019 - Does T002 `delete_vm` task description specify the log action is written before the DB DELETE or after — and is this consistent with FR-014 ("before returning")? [Clarity, Tasks §T002 vs Spec §FR-014]
- [ ] CHK020 - Is the `log_action` function interface (parameters: user_id, action, target, status, message) defined or referenced in any task or plan artifact? [Gap, Tasks]
- [ ] CHK021 - Does T001 specify what exception types `run_vbox_command` should raise vs. return, so T002 knows how to handle each case? [Clarity, Tasks §T001]

## Security Requirements

- [ ] CHK022 - Is the subprocess safety requirement (list args, no shell=True) specified in both the spec (FR-017), the contract, and the T001 task description? [Consistency, Spec §FR-017 vs Contract vs Tasks §T001]
- [ ] CHK023 - Is the requirement that `user_id` filtering (not RLS) is the authorization control for service-role DB writes explicitly stated in both data-model.md and the T002 task? [Completeness, Data Model vs Tasks §T002]
- [ ] CHK024 - Does the spec or plan document whether the VM name from the DB (used in VBoxManage args) could contain injection-relevant characters after Pydantic validation? [Clarity, Spec §FR-016]
- [ ] CHK025 - Is the requirement that 404 (not 403) is returned for cross-user access consistently specified across FR-015, the API contract, and the test cases in T006? [Consistency, Spec §FR-015 vs Contract vs Tasks §T006]

## Frontend Requirements

- [ ] CHK026 - Are the color-coded status badge requirements (green/grey/amber/red) from FR-018 explicitly referenced in the T007 vm-card task? [Consistency, Spec §FR-018 vs Tasks §T007]
- [ ] CHK027 - Is the requirement that action buttons are disabled during transitional states (FR-019) specified with identical state lists in T007? [Consistency, Spec §FR-019 vs Tasks §T007]
- [ ] CHK028 - Is the "no polling, refetch after action" assumption from the spec reflected in how T008 and T009 handle data refresh? [Completeness, Spec §Assumptions vs Tasks §T008-T009]
- [ ] CHK029 - Is the empty state message text ("No VMs yet — create your first one") specified in both the spec (User Story 4) and T008? [Consistency, Spec §User Story 4 vs Tasks §T008]
- [ ] CHK030 - Are form validation rules in T010 (Zod schema) specified as matching FR-001 exactly, including the name regex pattern? [Completeness, Tasks §T010 vs Spec §FR-001]

## Non-Functional & Edge Cases

- [ ] CHK031 - Is the 30-second timeout for VBoxManage calls specified consistently across FR-013, the vbox-commands contract, and T001? [Consistency, Spec §FR-013 vs Contract vs Tasks §T001]
- [ ] CHK032 - Is the requirement that VBoxManage not found returns 503 specified in both the spec edge cases and the API contract? [Completeness, Spec §Edge Cases vs Contract]
- [ ] CHK033 - Are RAM boundary values (512, 16384 valid; 511, 16385 rejected) consistently specified in FR-001, data-model validation, and test cases? [Consistency, Spec §FR-001 vs Data Model vs Tasks §T006]
- [ ] CHK034 - Is the "single-tenant, one VirtualBox host" assumption's impact on concurrent VM operations by different users addressed in any task or the plan? [Gap, Spec §Assumptions]
- [ ] CHK035 - Is the cascade-delete behavior (user account deletion while VM running) documented as a known limitation with a specific mitigation or acceptance statement? [Clarity, Spec §Edge Cases]
