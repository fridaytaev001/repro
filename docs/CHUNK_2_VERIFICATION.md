# Chunk 2 verification and remaining gate

## Tested locally

October 17, 2026: **36 passing checks** (29 non-browser, seven real Chromium), one Starlette/HTTPX dependency deprecation warning, 12.14 seconds. JavaScript syntax check also passed.

The real-browser loop integration test uses an explicitly labelled **scripted test provider**. It executes browser operations against the actual store, records an unsuccessful first hypothesis and a changed experiment, captures screenshots/traces, and reaches `awaiting_verification`. It does not use Crusoe and is not evidence of autonomous live-model discovery.

Coverage includes:

- Catalog validation, output limits, complete assistant/tool message ordering, bounded retries, redacted authentication failures, missing-key and empty-completion errors.
- Immutable checks, rejected invented evidence, no-progress re-planning, and candidate-only completion.
- Queue limits, duplicate admission rejection, active/queued cancellation, and explicit interruption after restart.
- Real browser operations, blocked foreign navigation and service writes, registered screenshot/trace files, and artifact path containment.
- The original store, seeded defect/control, persistent reports, and mobile UI.

## Live gate — not passed yet

At the last configuration check, `CRUSOE_API_KEY` was absent. No real model catalog, tool round trip, inference usage, cost, or autonomous investigation is claimed.

To finish ALI-8 and ALI-9, set the ignored local key, run `python -m scripts.check_crusoe`, then run a vague-complaint case through the UI. Record its actual model ID, provider request IDs where available, usage, hypotheses, browser observations, and candidate/unsuccessful outcome. Adjust request/token/time limits only from those measurements.

A candidate must remain unconfirmed until the separate verifier in Chunk 3 repeats it in a fresh context. Source diagnosis and repair are out of scope here.

## Implementation reference

- `app/providers/crusoe.py`: fixed-endpoint provider adapter and real readiness check.
- `app/tools/browser.py`: validated actions, real DOM observations, request restrictions, screenshots/traces.
- `app/agents/coordinator.py`: frozen checks, hypothesis loop, evidence-backed candidate handoff, bounded worker.
- `app/runs.py`: atomic snapshots, append-only events, contained artifacts.
- `app/static/case.*`: actual investigation progress and evidence view.

Technical references: [Crusoe model features](https://support.crusoecloud.com/hc/en-us/articles/55002524169499-How-To-List-Model-Features-via-curl-and-the-Inference-API), [Crusoe catalog](https://docs.crusoecloud.com/serverless-inference/available-models/index.html), [Playwright network controls](https://playwright.dev/python/docs/network).
