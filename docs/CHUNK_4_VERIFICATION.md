# Chunk 4: engineer handoff and live evaluation

## Handoff

Full validation: **53 passing checks** (40 non-browser, 13 real Chromium), 57.01 seconds, one existing Starlette/HTTPX deprecation warning. JavaScript syntax validation also passed. The exported regression assertion below is deliberately checked separately and is expected to fail against the buggy baseline.

Stopped cases offer Markdown, JSON, and ZIP downloads through `/api/runs/{id}/exports/{markdown|json|bundle}`. Active attempts return 409 so the snapshot cannot race the worker. Downloads use registered, contained artifact IDs. ZIPs include a point-in-time report, append-only events, replay/fixture JSON, separate reproduction and regression pytest files, available screenshots/traces, setup instructions, and a SHA-256 manifest. Missing candidate artifacts/evidence and the 64 MiB evidence limit are explicitly recorded. Previous exports are excluded to prevent recursive archives.

The runnable fixture needs this repository's installed runtime and a running loopback demo; it never reads an API key or makes model calls. `python -m scripts.replay_case path/to/replay.json --expect reproduce` exits 0 on an independently observed violation, 1 on the opposite result, and 2 on inconclusive replay. `--expect regression` reverses only the completed-result assertion. Generated pytest files enforce the same distinction; setup/replay errors cannot establish proof.

An actual bundle was downloaded for recovery case `1f9a01f6-33eb-495a-8f45-fedbb3b045b6`: 34 files, 4,320,355 compressed bytes. Its generated reproduction test passed in 11.39 seconds. The generated regression test failed on the expected policy-status assertion against the buggy store, with actual $90-to-$100 evidence; this is baseline failure, not repair proof. No repaired target is claimed.

## Real Crusoe evaluation

October 17, 2026; locally selected exact model ID `deepseek-ai/Deepseek-V4-Flash`. These are real inference and browser runs, not the scripted-provider integration tests. No defect trigger was inserted in the investigator prompt. The recovery input supplied remembered **non-triggering** initial-details steps and explicitly asked the investigator to try them before alternatives.

| Sample | Final outcome | Exploration actions | Provider requests | Returned tokens | Investigation seconds | Independent verification |
|---|---|---:|---:|---:|---:|---|
| Prior vague defect discovery | confirmed after Chunk 3 replay | 11 | 13 | 94,153 | 20.89 | 11 actions / 9.52 s |
| VIP20 guest control | not reproduced; expected rejection | 6 | 10 | 45,140 | 16.00 | No candidate submitted |
| Failed remembered steps → alternative | confirmed | 12 | 17 | 103,415 | 41.48 | 12 actions / 12.53 s |

Provider request counts include catalog calls. Verification makes no inference requests. Times exclude queue waiting; investigation and verification times are separate, not combined into a misleading latency number. The prior unsuccessful live budget-limited attempt is retained and documented in Chunk 2; it is not included as a successful sample.

### Control

Case `1029c2e0-85f0-4847-b818-6476064a2c06`: actual VIP20 entry displayed the member-only guest-ineligibility message and left the total at $100. The same browser then applied SAVE10 successfully, showing $90. The model stopped with `not_reproduced`, explaining that the stated expectation conflicts with the public eligibility rule. No confirmation or verifier pass was invented.

### Recovery

Case `1f9a01f6-33eb-495a-8f45-fedbb3b045b6`: first hypothesis and remembered initial-details experiment preserved SAVE10 at $90 (browser event 29, evidence `558dcc653f7ed69c.png`). The model explored Edit address from review and observed $100 (event 38). It recorded a second hypothesis with that prior result (event 41), then re-entered editing, reapplied SAVE10, and saved again (events 44/47/50). It submitted its actual sequence and screenshots at event 53.

Independent verification `a58e7b10-926c-4f10-a06a-a26cc8cd63e2` repeated the submitted steps from a fresh context and observed the same documented-rule violation. It produced its own screenshots, including `87fe0c1b17eeed7c.png` at the initial loss and `b477abab46994f41.png` after the later save. First/last model completion IDs: `4b6221a1e372491e957d3457fd8c8308` / `1fefd787c22849b19019c3758e4c31de`.

The second hypothesis was formalized **after** the model had already explored the alternative, then exercised again. This is actual observed recovery, not evidence of perfect prospective experiment annotation. The model was not forced through a scripted trigger. Full factual observations remain in the local event log; only expired control catalogs are removed from older model messages to reduce repeated-token usage.

### Supported cost estimates

Crusoe's [published pricing](https://www.crusoe.ai/cloud/pricing) lists DeepSeek V4 Flash input/output/cached-input rates of $0.14/$0.28/$0.03 per million tokens, checked October 17, 2026. Applying that snapshot to returned usage gives estimates of **$0.00377490** for the control and **$0.00945414** for recovery, not invoice measurements. Known cached tokens are subtracted from ordinary input before pricing. One call per case omitted cache detail and is conservatively priced at ordinary input rate. The estimate excludes other runs, application hosting, taxes, and future price changes.

Run `python -m scripts.evaluate_live` to read saved sample IDs from the ignored local manifest and summarize actual outcomes/provenance. `--submit` creates two new live cases and incurs inference use; it is an explicit opt-in, not part of tests. No credentials are read by this evaluation client.

## Sample limits

This is one control and one recovery sample, plus one previously recorded successful defect discovery; it is not a benchmark, reliability estimate, or proof for arbitrary websites/models. The default seeded target still contains its bug. Source diagnosis, isolated patches, and protected before/after repair checks belong to Chunk 5.
