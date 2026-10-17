# Chunk 1 verification

Tested October 17, 2026 on Windows with Python 3.12 and Playwright Chromium 156.0.8078.4. The tested Python package versions are in `requirements-lock.txt`.

## Result

`python -m pytest -q`: **18 passed**, one dependency deprecation warning, 5.13 seconds. The warning comes from Starlette's HTTPX TestClient compatibility layer; it does not prevent these tests from running.

- 13 API checks: durable receipt across application instances, whitespace/length validation, configured target restrictions, URL query/fragment removal, UUID-bound lookup, explicit storage-failure response, and corrupt-record handling.
- 5 Chromium checks: actual seeded state loss and completed checkout; correct ineligible-coupon behavior and quantity math; new-session isolation/reset; report submission from checkout with safely rendered complaint text and reload persistence; mobile layout/report access.
- JavaScript syntax checks completed for store, report, and case scripts.
- Visible browser replay observed $90 after SAVE10 and initial review, then $100 after an address edit from review. Synthetic values only.
- Review UI follow-up: coupon entry and Apply are hidden on review, including after address edits; both remain available on the details step. The full suite passed again (18 tests, 6.37 seconds).

On this workstation, the browser cache and pytest temp directories were explicitly set inside ignored `.local/`; normal installs may use their default locations.

## Interpretation

The reproduction test passes because it observes the intentional defect. No passing intended-behavior regression is claimed. The target remains defective for the future investigator to discover.

These are developer/evaluator tests. This milestone does not execute Crusoe inference, independently verify agent findings, generate repairs, or simulate any agent actions. The case receipt says investigation is not yet enabled.

## Review gate

Implements Linear ALI-5, ALI-6, and ALI-7. The implementation stays on the Chunk 1 feature branch pending owner approval to merge. The public main branch initially contains the project overview, design, ticket plan, and configuration template.
