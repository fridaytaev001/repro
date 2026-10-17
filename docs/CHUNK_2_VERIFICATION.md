# Chunk 2 verification

## Tested locally

October 17, 2026: **36 passing checks** (29 non-browser, seven real Chromium), one Starlette/HTTPX dependency deprecation warning, 12.99 seconds after the live-run adjustment. JavaScript syntax check also passed. GitHub CI passed on the preceding implementation commit.

The real-browser loop integration test uses an explicitly labelled **scripted test provider**. It executes browser operations against the actual store, records an unsuccessful first hypothesis and a changed experiment, captures screenshots/traces, and reaches `awaiting_verification`. It does not use Crusoe and is not evidence of autonomous live-model discovery.

Coverage includes:

- Catalog validation, output limits, complete assistant/tool message ordering, bounded retries, redacted authentication failures, missing-key and empty-completion errors.
- Immutable checks, rejected invented evidence, no-progress re-planning, and candidate-only completion.
- Queue limits, duplicate admission rejection, active/queued cancellation, and explicit interruption after restart.
- Real browser operations, blocked foreign navigation and service writes, registered screenshot/trace files, and artifact path containment.
- The original store, seeded defect/control, persistent reports, and mobile UI.

## Live Crusoe gate — passed

October 17, 2026: the authenticated live catalog and two-call tool/result round trip succeeded using the locally configured exact model ID `deepseek-ai/Deepseek-V4-Flash`. This was an explicit local model selection, rather than the default Nemotron preference. The returned catalog advertised tool calling and output-token limits. Smoke response IDs were `cbc8549f2f1c468ebd024bbdef54a071` and `5b288dea537b452e933ff57672133b38`; total returned usage was 657 tokens. Provider request-ID headers were absent; response IDs were retained instead.

A real autonomous browser attempt then found the seeded discount-state defect from this complaint, with no remembered steps: “My SAVE10 discount disappeared when I changed my address. I don't remember the exact steps.” The investigator received public rules and browser tools, not the defect trigger or target source.

- Local case: `36847863-3e9a-4fe9-8868-99dedeb50bce`; successful attempt: `6110b877-ee1f-4cc4-af78-3a6775cce5ba`.
- Outcome: `awaiting_verification`, with no confirmed outcome set. It applied SAVE10, navigated to review, selected Edit address, changed the street, and saved. Actual screenshots showed $90 before and $100 after, with the SAVE10 row removed.
- Elapsed: 20.89 seconds; 11 browser actions; 13 provider requests (catalog plus 12 completions); 91,819 prompt and 2,334 completion tokens, totaling 94,153 returned usage tokens. These are token measurements, not an invoice or measured dollar charge.
- First/last completion IDs: `3c76ecc703514af4813c0bf9a9af1fb6` / `0e98fb3e900d449db0b07ae9e9be81b0`.
- Candidate screenshot IDs: `5af5deec452b5a44.png` and `7fdc0c1e1e1fba6f.png`. Actual screenshots, trace archives, immutable acceptance hash, replay, and provenance remain in ignored local runs and are available through the case UI.

The first live attempt observed the discount loss but reset rather than submitting its candidate and stopped at the conservative 80,000-token admission limit after 62,076 returned tokens. Its evidence/events were retained. Based on that measurement, the bounded allowance became 160,000 tokens and the instructions explicitly hand off observed violations immediately instead of repeating confirmation. The second attempt above passed. It used one hypothesis; changed-hypothesis behavior is covered by the labelled scripted-provider browser test, not claimed as demonstrated by this successful live attempt.

A candidate must remain unconfirmed until the separate verifier in Chunk 3 repeats it in a fresh context. Source diagnosis and repair are out of scope here.

## Implementation reference

- `app/providers/crusoe.py`: fixed-endpoint provider adapter and real readiness check.
- `app/tools/browser.py`: validated actions, real DOM observations, request restrictions, screenshots/traces.
- `app/agents/coordinator.py`: frozen checks, hypothesis loop, evidence-backed candidate handoff, bounded worker.
- `app/runs.py`: atomic snapshots, append-only events, contained artifacts.
- `app/static/case.*`: actual investigation progress and evidence view.

Technical references: [Crusoe model features](https://support.crusoecloud.com/hc/en-us/articles/55002524169499-How-To-List-Model-Features-via-curl-and-the-Inference-API), [Crusoe catalog](https://docs.crusoecloud.com/serverless-inference/available-models/index.html), [Playwright network controls](https://playwright.dev/python/docs/network).
