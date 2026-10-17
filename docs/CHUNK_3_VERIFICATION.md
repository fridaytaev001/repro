# Chunk 3: independent verification and honest stopping

The independent verifier replays a candidate in a separate Chromium instance and new context. It resolves semantic controls afresh for each action; model-supplied JavaScript, selectors, assertions, and claimed totals are never executed. A registered read-only DOM adapter measures the demo's visible totals and coupon state.

The declared fixture is a browser-local cart with one item, no coupon, the details step, and no server cart. The verifier checks the visible initial checkout, empty session storage, and no cookies before establishing proof. Exploration and verification have separate screenshot directories and trace archives.

The deterministic policy is narrowly registered as `store-rules:v1/coupon-preservation`. Only an observed successful SAVE10 discount arms the persistence check. A later observed loss or incorrect discounted total establishes a rule violation. Correct VIP20 rejection and initial address submission without loss do not. Other rule families need their own registered verifier policies; absence of a supported violation does not prove the website has no bugs.

Frozen criteria and candidate hashes/versions must match before any browser launch. Changed criteria, missing/ambiguous controls, unsupported actions, malformed money, timeout, or browser errors cannot confirm a bug. Completed replay without a supported violation is `fail` / `not_reproduced`; incomplete replay is `inconclusive` / `blocked`. Only an actual independent violation produces `confirmed`. This does not diagnose or repair source.

## Measured replay of the live Crusoe candidate

October 17, 2026: the saved live candidate from Chunk 2 was submitted through **Verify saved candidate** in the case UI.

- Case: `36847863-3e9a-4fe9-8868-99dedeb50bce`.
- Independent verification: `d11da77c-f340-49f5-af04-b38d46900026`.
- Criteria hash: `e5f0025dcdfee7ad760b912364316daf6f4a0e3e4b5a8f9f271195b05e280b32`.
- Result: `pass` / `confirmed`, 11 replay actions, 9.52 seconds, zero provider requests for verification.
- Visible initial checkout: $100.00, quantity one, no coupon. Actual SAVE10 application changed it to $90.00; review retained that amount. After Edit address, a street change, and Save address, the total became $100.00 and the coupon row disappeared.
- The independent violation screenshot is `b6a9ab3dafdfc4ff.png`. Evidence and traces remain in ignored local runs and are available through registered case artifact URLs.

The original live discovery provenance stays labelled live Crusoe; independent verification is separately labelled real browser. Test discoveries stay labelled test even when real browser verification succeeds.

## Bounds and lifecycle

One worker and the same bounded waiting list own investigation and verification. Newly discovered candidates automatically proceed to independent replay; saved candidates can be queued for replay without a provider key. Duplicate admissions are rejected. Verification admits at most 30 candidate actions and has its own 60-second timeout within the worker's overall five-minute attempt limit. Investigation retains three hypotheses, 24 provider requests including retries, and 160,000 budget tokens. No source writes, patch dispatch, or clarification request loop is exposed in this chunk.

Cancellation is idempotent, stops active dispatch, closes the browser, and preserves receipts. Terminal cancellation cannot overwrite confirmation. Restart marks queued, investigating, and verifying cases explicitly interrupted instead of silently resuming. A confirmed case cannot be accidentally requeued; future repair work must preserve this established evidence.

## Validation

The full suite passed: **48 checks** (36 non-browser and 12 real Chromium), 48.12 seconds, one existing Starlette/HTTPX deprecation warning. JavaScript syntax validation passed.

The suite covers real defect confirmation, incorrect candidate rejection, the VIP20 control, changed criteria before browser launch, missing targets, cancellation, timeout, action-limit admission, key-free saved replay, and the automatic investigate-to-verify worker path. Existing store, provider, queue, and artifact checks remain required. The synchronous Playwright test fixture is module-scoped so it closes before later asynchronous verification tests start.

Reproduction artifacts and repair proof remain Chunk 4/5 work. The generic registered policy intentionally covers coupon persistence, not arbitrary prose assertions or arbitrary sites.
