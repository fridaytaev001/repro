# Repro

Turn a vague website complaint into an independently reproduced bug, a runnable regression test, and an optional tested patch for engineer review.

**Track:** Done Means Done. **Current implementation:** Chunk 1 — demo store and durable report intake. Autonomous investigation is planned for Chunk 2; no live Crusoe execution is claimed yet.

## What works now

- Original FIELD storefront with cart, quantity, coupons, shipping address, review, and synthetic checkout.
- A real intentionally seeded discount-state defect, plus a correct coupon-ineligibility control.
- Report widget that validates and saves complaints locally, then displays a persistent case receipt.
- API and real Chromium tests for the store, defect, negative control, and report path.

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

Open **http://127.0.0.1:8000**. Report files live in ignored `runs/`. A report is only acknowledged after it is saved. No API key is needed for Chunk 1.

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
- [Technical design](Repro_Design_Doc.md).
- [Implementation plan and Linear mapping](Repro_Tickets.md).
- [Linear project](https://linear.app/ali-madinovich/project/repro-308900fec3ae/issues).

The investigator must discover the sequence through browser tools. Do not include demo source, evaluation tests, or operator instructions in its exploration prompt.

## API

- `POST /api/reports`: complaint, expected_behavior, optional steps, target_id=`demo-store`, page_url. Returns 202 with case/status URLs.
- `GET /api/runs/{uuid}`: read saved case; unknown case returns 404.
- `GET /health`: health and implemented milestone.

Only configured demo origins/pages are accepted; URL query strings and fragments are discarded. Change `REPRO_ALLOWED_ORIGINS` if using a different local port. API docs: `/docs`.

## Crusoe configuration (next chunk)

Copy `.env.example` to `.env` and enter `CRUSOE_API_KEY` locally. Never paste keys into reports or commit them. The future adapter uses `https://api.inference.crusoecloud.com/v1`, discovers exact model IDs, then configures `CRUSOE_MODEL`. No third-party inference fallback may claim to be Crusoe.

## Delivery workflow

Each completed chunk gets its own feature branch and PR. The owner reviews and approves merging into `main` before the next chunk lands. Chunk 1 implements Linear ALI-5, ALI-6, ALI-7. Next: ALI-8, ALI-10, ALI-9 (Crusoe and real investigation).

## Architecture and limits

FastAPI serves the HTML/CSS/JS target and report API. Browser-local state isolates demo carts; atomic JSON files preserve reports. A future worker owns the bounded model/browser loop. The first milestone intentionally does not include an agent activity feed, inference calls, automated confirmation, repair, multi-tenant hosting, or arbitrary-site access.

Built here: store artwork/UI, synthetic checkout state, seeded defect/control, report API, case receipt, docs, and tests. Libraries: FastAPI, Uvicorn, Pydantic, Playwright, HTTPX, pytest, and python-dotenv; their respective licenses apply. The product illustration is original inline SVG and uses no external assets.
