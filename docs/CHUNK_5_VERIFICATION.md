# Chunk 5: isolated source repair with protected proof

Only independently confirmed cases can queue source repair. The single worker preserves the established confirmation while repair runs, fails, is cancelled, or is interrupted by restart. `fixed_verified` means the isolated candidate passed protected checks; it never means the original demo was silently changed.

## Boundaries and checks

Each job copies the synthetic target into separate baseline and candidate directories. The repair model can read/search only candidate `store.js` and replace at most three exact, unique source spans in that file. Absolute paths, traversal, HTML, tests, fixtures, baseline files, environment files, logs, and arbitrary commands are unavailable. A diagnosis must cite actual baseline line numbers. Requests, tokens, edits, child checks, and overall time are bounded: ten provider requests including catalog/retries, 50,000 tokens, three edits, 60 seconds per browser-check process, ten seconds for syntax, and 180 seconds overall.

The host freezes and hashes a copy of the regression fixture and registered check script outside model-writable paths. Baseline files, originals, and imported verifier/browser/replay implementations are checked for unchanged hashes around writes and execution. Child processes receive a restricted environment without the API key and run only the registered checker or JavaScript syntax command; no shell or model-generated command runs.

The identical protected checker starts a local static fixture server for each source copy, replays the frozen candidate in a clean browser, then checks guest VIP20 rejection, SAVE10 application, preservation after invalid-code attempts, quantity-three discount, ordinary review, hidden review coupon entry, and reset. Setup/runtime errors return inconclusive (exit 2), never baseline proof. Required baseline result: intended regression failure (exit 1) with passing controls. Required candidate result: regression and controls pass (exit 0), plus syntax success. Actual process outputs, observed values, screenshot/trace archives and the proposed diff are registered local artifacts.

Temporary browser evidence uses short OS temporary paths to avoid Windows path-length failures, then is archived under the protected job. Originals and case proof remain available after child cleanup.

## Actual live repair

October 17, 2026; case `1f9a01f6-33eb-495a-8f45-fedbb3b045b6`; repair `a002584a-738c-4126-b4d1-c4527130e021`.

- Provider/model: live Crusoe, `deepseek-ai/Deepseek-V4-Flash`.
- Five provider requests (catalog plus four completions), 13,745 returned tokens, one patch, 49.39 seconds overall.
- First/last completion IDs: `5e7ef0e699264207aa572af1fdca05c2` / `7e69e6c7252845ffbb41f771d5e833d3`.
- Diagnosis cited `demo_store/store.js` lines 55–57: the address-save handler clears a valid coupon when returning from review.
- The proposed patch guards coupon clearing so a valid SAVE10 survives the edit. It is a constrained source change, not fixed totals or a changed test.
- Baseline: intended regression failure, return code 1, required controls pass.
- Candidate: identical regression passes, return code 0, required controls pass, JavaScript syntax passes.
- Case outcome: `fixed_verified` **in the isolated copy**. Original seeded target unchanged, still covered by the original defect-reproduction check.
- Proposed diff artifact: `8971ab1948b614e9.diff`. Check receipts and evidence ZIPs are available through case artifacts and handoff export.

The target source labels its seeded fault in a comment. Diagnosis can therefore benefit from that comment once source access is explicitly allowed; this is not a benchmark of root-cause finding in unlabelled production code. Independent before/after behavior remains measured. Generalized repository repair and arbitrary commands are out of scope.

## Tests

Full suite: **59 passed** (45 non-browser, 14 real Chromium), 92.09 seconds, one existing Starlette/HTTPX deprecation warning. Python compilation and case JavaScript syntax validation also passed.

Checks cover source-path confinement, unchanged original source, protected-fixture tampering, sanitized environments, real before/after proof with a labelled scripted test repair provider, rejection of baseline setup errors, rejected-candidate confirmation preservation, and idempotent queued repair cancellation. Live repair above is separate from test-provider coverage.
