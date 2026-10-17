# Repro — implementation tickets

Status: Created and verified in the Linear website on October 17, 2026. [Open Repro](https://linear.app/ali-madinovich/project/repro-308900fec3ae/issues). All tickets are unassigned, with no due dates. R01–R10 have High priority; R11–R14 have Medium priority. Chunks 1–4 (ALI-5 through ALI-14) are merged. Chunk 5 is ready for review; Chunk 6 prepares delivery.

Chunk 2 (ALI-8, ALI-10, ALI-9) has a successful live Crusoe tool round trip and autonomous candidate discovery. PR #2 is merged with owner approval. The measured candidate has screenshots and executed steps. See docs/CHUNK_2_VERIFICATION.md for actual usage and the first attempt's budget stop.

Chunk 3 (ALI-11, ALI-12) implements independent browser replay, deterministic coupon-preservation verification, cancellation/restart handling, and bounded outcomes. The saved live Crusoe candidate was independently confirmed in 11 replay actions / 9.52 seconds with fresh evidence and no new model requests. PR #3 is merged with owner approval. See docs/CHUNK_3_VERIFICATION.md.

Chunk 4 (ALI-13, ALI-14) adds report/bundle exports, runnable replay and opposite reproduction/regression assertions, a non-falsely-confirmed live VIP20 control, and live recovery from unsuccessful remembered steps to a separately verified defect. The actual downloaded reproduction test passes and the regression test fails on its intended baseline assertion. See docs/CHUNK_4_VERIFICATION.md for measured samples and limitations.

Chunk 5 (ALI-15, ALI-16) has 59 passing checks and a real Crusoe repair in an isolated copy. The protected regression fails on baseline and passes on candidate with controls and syntax passing; originals are unchanged. The proposed patch and proof are available locally. See docs/CHUNK_5_VERIFICATION.md.

The six chunks are implemented as native Linear project milestones containing 14 issues. Complete chunks 1–4 for the reproduction MVP; chunk 5 adds repair; chunk 6 prepares delivery. Dependencies are recorded in ticket descriptions using the stable R01–R14 planning references; native blocking relationships have not been added.

| Planning reference | Linear issue |
|---|---|
| R01 | ALI-5 |
| R02 | ALI-6 |
| R03 | ALI-7 |
| R04 | ALI-8 |
| R05 | ALI-10 |
| R06 | ALI-9 |
| R07 | ALI-11 |
| R08 | ALI-12 |
| R09 | ALI-13 |
| R10 | ALI-14 |
| R11 | ALI-15 |
| R12 | ALI-16 |
| R13 | ALI-17 |
| R14 | ALI-18 |

## Chunk 1 — Working store and report intake

### R01 — Scaffold the local application and document store rules

**Priority:** High. **Depends on:** None.

Build a FastAPI application with plain frontend assets and a README. Define SAVE10 eligibility, address changes, shipping/tax, and synthetic fixture/reset behavior. Add environment examples and secret/run-data ignore rules.

**Acceptance:** A fresh setup can start the application using documented commands; product rules are versioned; real credentials are absent from tracked files.

### R02 — Build the store and real browser checkout path

**Priority:** High. **Depends on:** R01.

Implement product/cart, coupon, shipping address, and checkout. Add a disclosed seeded discount-state defect and a correct coupon-ineligibility control. Keep the hidden trigger/evaluator separate from agent-visible rules. Provide deterministic fixture reset.

**Acceptance:** Playwright can complete checkout and read actual prices; reset restores known state; screenshots show real application behavior; agents cannot read hidden scenario answers.

### R03 — Submit a complaint and persist a case

**Priority:** High. **Depends on:** R01, R02.

Build the report modal and POST /api/reports. Collect complaint, expected behavior, optional steps, and sanitized current URL. Validate the configured target and save a case before returning 202.

**Acceptance:** A submitted report has a stable case ID and status URL; invalid targets/inputs are rejected; the saved complaint survives a process restart.

## Chunk 2 — Real Crusoe investigation

### R04 — Connect Crusoe and record model usage

**Priority:** High. **Depends on:** R01 and local API key.

Build a server-side provider adapter. Discover exact model IDs, validate tool-call support, configure the chosen model, preserve tool-call/result ordering, and add bounded retries/timeouts. Record actual usage/provenance. Label mock mode persistently.

**Acceptance:** A real authenticated call and tool round trip succeed; model/run IDs and usage are recorded; keys never appear in client assets or logs; missing-key/mock mode cannot claim live execution.

### R05 — Add a limited waiting list and safe browser tools

**Priority:** High. **Depends on:** R02, R03.

Run one active case with a configured maximum waiting count. Expose typed browser actions for allowed navigation, inspection, click, fill, back, value reads, and evidence capture. Apply origin restrictions to redirects/requests. Do not execute model-written JavaScript.

**Acceptance:** HTTP status requests stay responsive during a run; a full queue rejects intake clearly; disallowed origins/invalid arguments are rejected; real tool observations and errors are saved.

### R06 — Implement the case manager and hypothesis loop

**Priority:** High. **Depends on:** R04, R05.

Create frozen observable acceptance checks from product rules and complaints. Have the model propose experiments, inspect results, and revise hypotheses. Enforce transitions with ordinary code. Detect repeated action/state signatures and support essential clarification.

**Acceptance:** A real run explores without a hardcoded trigger sequence; each experiment has observations and a decision; no-progress repetition causes a changed experiment or honest stop; criteria revisions have explicit reasons and invalidate old verification.

## Chunk 3 — Independent verification and honest stopping

### R07 — Replay candidates in a fresh context

**Priority:** High. **Depends on:** R06.

Give a separate verifier frozen criteria, candidate steps, and declared fixtures. Create a fresh browser context and independently reset/namespace server state. Return structured pass/fail/inconclusive results and actual values.

**Acceptance:** Browser storage and server fixtures do not leak from exploration; an incorrect candidate is rejected; only an observed documented-rule violation permits confirmed status.

### R08 — Enforce budgets, cancellation, and terminal outcomes

**Priority:** High. **Depends on:** R06, R07.

Enforce action, hypothesis, model-call/token, patch, clarification, and time limits. Add idempotent cancellation and explicit restart interruption handling. Distinguish missing information, no reproduction, tool/provider blockers, and successful confirmation.

**Acceptance:** No dispatch begins after budget/cancellation stops the run; evidence survives errors; a later repair failure preserves a previously confirmed defect; unsuccessful runs state the actual reason.

## Chunk 4 — Engineer handoff and reproduction MVP

### R09 — Show evidence and export runnable artifacts

**Priority:** High. **Depends on:** R07, R08.

Build the case view with criteria, stages, actual experiment timeline, observed values, and terminal outcome. Export report Markdown/JSON, replay/fixture specification, reproduction test, regression test, screenshots, and trace. Use registered artifact IDs with containment checks.

**Acceptance:** A second engineer can run the replay from the documented setup; reproduction and regression assertions are clearly distinguished; downloads match recorded evidence; missing outputs are labelled; no fabricated activity appears.

### R10 — Evaluate a defect, control, and genuine recovery

**Priority:** High. **Depends on:** R09.

Run the seeded defect and correct-behavior control with real inference. Exercise an incorrect candidate or unsuccessful hypothesis and capture actual re-planning. Measure attempts, verification results, calls, tokens, elapsed time, and supported cost estimates.

**Acceptance:** At least one real defect is independently confirmed; the control is not falsely confirmed; one actual recovery is evidenced; results name sample counts and limitations. Failure of any gate is reported honestly rather than staged.

## Chunk 5 — Optional tested repair

### R11 — Diagnose and patch an isolated source copy

**Priority:** Normal. **Depends on:** R07, R08.

Record baseline identity, create a per-case source copy, and provide bounded source read/search and constrained patch tools. Protect baseline, criteria, fixtures, logs, and evaluation files. Run only registered check commands with sanitized environments and timeouts.

**Acceptance:** The proposed cause cites relevant files and evidence; patch writes cannot escape the copy or modify protected files; an invalid path/edit is rejected; the original store remains intact.

### R12 — Prove the patch with protected before/after checks

**Priority:** Normal. **Depends on:** R09, R11.

Freeze the regression test/hash outside repairer-writable paths. Run it against baseline and candidate, then run relevant existing tests. Capture trusted process outputs and return verified or rejected patch results.

**Acceptance:** Baseline fails on the intended behavior assertion, candidate passes the identical test, and existing required checks pass before fixed_verified is allowed. Setup errors do not count as baseline proof. Rejected repair keeps confirmed status with its repair failure reason.

## Chunk 6 — Reviewable delivery and demo

### R13 — Prepare setup, measured results, and demo materials

**Priority:** Normal. **Depends on:** R10; include R12 only if verified.

Write the README, architecture overview, environment/setup/test instructions, model discovery steps, limitations, seeded-defect disclosure, and new-contribution statement. Prepare one-minute video and three-minute live-demo runbooks plus a labelled backup evidence bundle.

**Acceptance:** Another person can follow setup/run instructions; claims match saved results; demo materials distinguish live, recorded, mocked, and proposed work; verified repair is shown only if R12 passed.

### R14 — Link the selected GitHub repository and prepare submission

**Priority:** Normal. **Depends on:** R13 and a chosen repository/destination.

Associate the selected repository with the Linear project where supported. Check repository visibility, secret hygiene, licenses, artifact accessibility, and current submission requirements. Prepare a clean reviewable change and a submission checklist. Publication/submission follows explicit user direction.

**Acceptance:** Repository destination/access are confirmed; relevant tickets reference code changes; no secrets/run data are published; remaining publication/submission actions are explicit. Do not create a guessed repository or claim a native Linear–GitHub integration is installed without verifying it.
