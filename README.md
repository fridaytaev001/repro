# Repro

Turn a vague website complaint into an independently reproduced bug, a runnable regression test, and an optional tested patch for engineer review.

**Track:** Done Means Done. **Current branch:** Chunk 2 — bounded Crusoe/browser investigation, with live provider validation pending local credentials. Chunk 1 is a separate review gate. No live Crusoe run is claimed until the readiness check and a real case succeed.

## What works now

- Original FIELD storefront with cart, quantity, coupons, shipping address, review, and synthetic checkout.
- A real intentionally seeded discount-state defect, plus a correct coupon-ineligibility control.
- Report widget that validates and saves complaints locally, then displays a persistent case receipt.
- API and real Chromium tests for the store, defect, negative control, and report path.
- A single background worker and bounded waiting list, typed browser operations, frozen checks, hypothesis changes, saved observations/screenshots/traces, and candidate-only results.
- Explicit missing-key/provider failures, cancellation, request/action/token/time limits, and restart interruption records.

No real payments or shipments occur. Use synthetic customer data. This local prototype has no authentication; run on loopback only.

## Run locally

Requires Python 3.12+.

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

## Enable a real investigation

1. Copy `.env.example` to `.env` and set `CRUSOE_API_KEY` locally. The ignored `.env` is read on each new attempt; keys containing dollar signs are preserved without interpolation.
2. Set `REPRO_TARGET_URL` if the demo runs on another loopback port, and include that origin in `REPRO_ALLOWED_ORIGINS`.
3. Run `python -m scripts.check_crusoe`. It discovers the exact Nemotron 3 Super ID from the live catalog and checks a real tool-call/result round trip. Alternatively set `CRUSOE_MODEL` to an exact available tool-calling ID. This check makes small billed inference requests.
4. Submit a vague complaint through the store, or open an existing blocked receipt and click **Start investigation**.

The default runtime sends inference only to Crusoe's fixed serverless endpoint. It reads public store rules and real visible browser observations; source code, evaluator tests, and the operator guide are not included in model input. Browser requests are limited to the configured demo origin/assets; service writes and other origins are blocked. There is no shell, arbitrary JavaScript, or source-edit tool.

The case page shows real events, criteria, usage provenance, and actual screenshot links. A found sequence stops at **awaiting_verification**, with no confirmed/fixed outcome. Independent verification belongs to Chunk 3.

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
- [Chunk 2 verification](docs/CHUNK_2_VERIFICATION.md) — offline protocol/integration results and live-validation blocker.
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

Each completed chunk gets its own feature branch and PR. The owner explicitly approves merging into `main`. Chunk 1 implements Linear ALI-5, ALI-6, ALI-7. Chunk 2 addresses ALI-8, ALI-10, ALI-9 and remains incomplete until a live connection and investigation are verified. If the preceding PR remains open, the next PR is stacked on its feature branch and must be retargeted after that merge.

## Architecture and limits

FastAPI serves the HTML/CSS/JS target and report API. Browser-local state isolates demo carts; atomic JSON snapshots and JSONL events preserve cases. One worker owns the bounded model/browser loop. Defaults: one active case, five waiting, 30 browser actions, three hypotheses, 24 provider requests including retries, 80,000 budget tokens, five minutes per attempt. Returned token usage is tracked; missing usage uses a conservative estimate for budgeting, not a measured billing claim. Cancellation/startup recovery controls were brought forward from Chunk 3 because the worker needs them. No automated confirmation, repair, multi-tenant hosting, or arbitrary-site access is included.

Built here: store artwork/UI, synthetic checkout state, seeded defect/control, report API, case receipt, docs, and tests. Libraries: FastAPI, Uvicorn, Pydantic, Playwright, HTTPX, pytest, and python-dotenv; their respective licenses apply. The product illustration is original inline SVG and uses no external assets.
