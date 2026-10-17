# Repro

Turn a vague website complaint into an independently reproduced bug, a runnable regression test, and an optional tested patch for engineer review.

**Track:** Done Means Done. **Current branch:** Chunk 6 — delivery and demo. Chunks 1–4 are merged; repair and delivery PRs await owner review. Real Crusoe discovery, independent replay, control/recovery, and a protected before/after repair have been recorded. A labelled one-minute recorded walkthrough and backup evidence bundle are prepared locally.

## What works now

- Original FIELD storefront with cart, quantity, coupons, shipping address, review, and synthetic checkout.
- A real intentionally seeded discount-state defect, plus a correct coupon-ineligibility control.
- Report widget that validates and saves complaints locally, then displays a persistent case receipt.
- API and real Chromium tests for the store, defect, negative control, and report path.
- A single background worker and bounded waiting list, typed browser operations, frozen checks, hypothesis changes, actual screenshots/traces, independent verification, and downloadable runnable evidence.
- Crusoe source repair restricted to an isolated `store.js` copy, with a frozen baseline/candidate regression, controls, syntax check, receipts, and patch download. The original demo retains its bug.
- Explicit missing-key/provider failures, cancellation, request/action/token/time limits, and restart interruption records.

No real payments or shipments occur. Use synthetic customer data. This local prototype has no authentication; run on loopback only.

## Run locally

Requires Python 3.12+. Repair syntax uses Node.js from PATH or the pinned Playwright package's bundled Node.

```sh
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m playwright install chromium
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. Report files live in ignored `runs/`. A report is only acknowledged after it is saved. The store and report intake work without an API key; an unconfigured investigation is saved as `blocked` with a specific reason.

On the prepared Windows workspace, double-click **Start_Repro.cmd**. It uses the existing `.venv` and workspace browser cache. Cross-platform: `python -m scripts.run_local --open`. It reuses an already running Repro server.

If opening `.env` is inconvenient, run `python -m scripts.configure` in your terminal. Its masked prompt saves the key only in the ignored local file; no chat paste or commit is needed.

## Enable a real investigation

1. Copy `.env.example` to `.env` and set `CRUSOE_API_KEY` locally. The ignored `.env` is read on each new attempt; keys containing dollar signs are preserved without interpolation.
2. Set `REPRO_TARGET_URL` if the demo runs on another loopback port, and include that origin in `REPRO_ALLOWED_ORIGINS`.
3. Run `python -m scripts.check_crusoe`. It discovers the exact Nemotron 3 Super ID from the live catalog and checks a real tool-call/result round trip. Alternatively set `CRUSOE_MODEL` to an exact available tool-calling ID. This check makes small billed inference requests.
4. Submit a vague complaint through the store, or open an existing blocked receipt and click **Start investigation**.

The default runtime sends inference only to Crusoe's fixed serverless endpoint. It reads public store rules and real visible browser observations; source code, evaluator tests, and the operator guide are not included in model input. Browser requests are limited to the configured demo origin/assets; service writes and other origins are blocked. There is no shell, arbitrary JavaScript, or source-edit tool.

The case page shows real events, criteria, usage provenance, and actual screenshot links. A found sequence becomes a candidate, then the worker independently replays it in a fresh browser. Only a registered documented-rule violation permits **confirmed**. A saved candidate can use **Verify saved candidate** without another model call. Incomplete replay is blocked/inconclusive; a completed replay without a supported violation is not reproduced.

A confirmed case offers **Try an isolated repair**. The repairer can read/search/patch only its source copy; protected baseline, frozen checks and fixture remain outside its writable tools. Only the identical regression failing on baseline and passing on candidate, plus required controls and syntax, permits **fixed_verified**. Rejected repair preserves confirmation. Download the proposed patch for review; the original seeded target is preserved.

Stopped cases include an **Engineer handoff** section with report Markdown/JSON and a ZIP containing actual evidence, replay/fixture JSON, hashes, and separate runnable reproduction/regression tests. Extract it inside this checkout and follow its README. Replaying uses no inference or credentials:

```sh
python -m scripts.replay_case .local/handoff/replay.json --expect reproduce
python -m pytest .local/handoff/test_reproduce.py -q
python -m pytest .local/handoff/test_regression.py -q
```

The reproduction test passes on the seeded buggy target. The regression test deliberately fails until a later verified repair. Both fail on inconclusive replay. Missing candidate/evidence outputs are explicitly labelled in the bundle manifest.

## Test

```sh
python -m pytest -m "not browser" -q
python -m pytest -m browser -q
```

Browser tests start their own temporary server, cases directory, and fresh browser contexts. The seeded-defect reproduction test **passes when it observes the bug**. It is not a passing regression test for the intended behavior. A protected before/after regression gate arrives in the repair chunk.

`requirements-lock.txt` pins the tested environment. `requirements.txt` expresses allowed top-level dependency ranges for deliberate upgrades.

## Store rules and demo

- [Product rules v1](docs/STORE_RULES.md) — also visible at `/rules`.
- [Operator-only demo guide](docs/DEMO.md) — contains the trigger; exclude from investigator input.
- [Chunk 1 verification](docs/CHUNK_1_VERIFICATION.md) — 18 passing checks and known limits.
- [Chunk 2 verification](docs/CHUNK_2_VERIFICATION.md) — protocol/integration results and measured live Crusoe candidate discovery.
- [Chunk 3 verification](docs/CHUNK_3_VERIFICATION.md) — independent policy, measured confirmation, controls, bounds, and limits.
- [Chunk 4 verification](docs/CHUNK_4_VERIFICATION.md) — actual downloaded-test results, live control/recovery, measured usage, and supported cost estimates.
- [Chunk 5 verification](docs/CHUNK_5_VERIFICATION.md) — actual live isolated repair and protected baseline/candidate results.
- [Chunk 6 delivery](docs/CHUNK_6_VERIFICATION.md) — checked media, backup package, startup and final limits.
- [Architecture](docs/ARCHITECTURE.md) — coordinator, trusted policy check and bounded queue in plain language.
- [Demo runbooks](docs/DEMO_RUNBOOK.md), [submission package](docs/SUBMISSION.md), and [dependency attribution](docs/DEPENDENCIES.md).
- [Technical design](Repro_Design_Doc.md).
- [Implementation plan and Linear mapping](Repro_Tickets.md).
- [Linear project](https://linear.app/ali-madinovich/project/repro-308900fec3ae/issues).

The investigator must discover the sequence through browser tools. Do not include demo source, evaluation tests, or operator instructions in its exploration prompt.

## API

- `POST /api/reports`: complaint, expected_behavior, optional steps, target_id=`demo-store`, page_url. Returns 202 with case/status URLs.
- `GET /api/runs/{uuid}`: read saved case; unknown case returns 404.
- `GET /health`: health and implemented milestone.
- `POST /api/runs/{uuid}/start`: queue or retry a saved case.
- `POST /api/runs/{uuid}/cancel`: request bounded cancellation.
- `GET /api/runs/{uuid}/events?after={seq}`: incremental saved events.
- `GET /api/runs/{uuid}/artifacts/{id}`: registered evidence only.
- `POST /api/provider/check`: catalog discovery and small billed tool-call smoke check.

Only configured demo origins/pages are accepted; URL query strings and fragments are discarded. Change `REPRO_ALLOWED_ORIGINS` if using a different local port. API docs: `/docs`.

## Crusoe configuration

Copy `.env.example` to `.env` and enter `CRUSOE_API_KEY` locally. Never paste keys into reports or commit them. The adapter uses `https://api.inference.crusoecloud.com/v1`, discovers exact model IDs, then optionally uses `CRUSOE_MODEL`. No third-party inference fallback exists. Test providers are dependency-injected only in tests and display `test`, never `live`, execution mode.

## Delivery workflow

Each completed chunk gets its own feature branch and PR. The owner explicitly approves merging into `main`. Chunks 1–4 (Linear ALI-5 through ALI-14) are merged. Chunk 5 (ALI-15, ALI-16) is PR #5; final delivery (ALI-17, ALI-18) is stacked on it until that merge. Local media are in ignored `.local/delivery/`. Public video hosting and the organizer form are separate final actions; neither is claimed complete.

## Architecture and limits

FastAPI serves the HTML/CSS/JS target and report API. Browser-local state isolates demo carts; atomic JSON snapshots and JSONL events preserve cases. One worker owns the bounded model/browser loop. Defaults: one active case, five waiting, 30 exploration actions, three hypotheses, 24 provider requests including retries, 160,000 budget tokens, five minutes per attempt. Verification permits up to 30 replay actions with its own 60-second limit inside the worker deadline. Isolated repair permits three edits, ten provider requests, 50,000 tokens and 180 seconds; child check deadlines are also bounded. Returned token usage is tracked; missing usage uses a conservative estimate for budgeting, not a measured billing claim. Cancellation and restart preserve evidence and established confirmation. The deterministic verifier covers the demo's versioned coupon-preservation policy. No multi-tenant hosting or arbitrary-site/repository access is included.

Built here: store artwork/UI, synthetic checkout state, seeded defect/control, report API, case receipt, docs, and tests. Libraries: FastAPI, Uvicorn, Pydantic, Playwright, HTTPX, pytest, and python-dotenv; their respective licenses apply. The product illustration is original inline SVG and uses no external assets.
