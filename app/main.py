"""Demo store, durable case API, and one bounded investigation worker."""

import json
import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4

from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.agents.coordinator import RunManager
from app.providers.crusoe import CrusoeClient, ProviderError
from app.runs import CaseStore
from app.settings import Settings
from app.tools.browser import BrowserSession

ROOT = Path(__file__).resolve().parent.parent


class ReportInput(BaseModel):
    complaint: str = Field(min_length=5, max_length=4000)
    expected_behavior: str = Field(min_length=5, max_length=4000)
    steps: str = Field(default="", max_length=4000)
    target_id: Literal["demo-store"] = "demo-store"
    page_url: str = Field(max_length=2048)

    @field_validator("complaint", "expected_behavior", "steps", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


def sanitize_url(value: str, allowed_origins: set[str]) -> str:
    try:
        url = urlsplit(value)
        origin = f"{url.scheme}://{url.netloc}"
        if (url.scheme not in {"http", "https"} or origin not in allowed_origins
                or url.username or url.password or url.path not in {"", "/", "/rules"}):
            raise ValueError("Unsupported demo page")
        return urlunsplit((url.scheme, url.netloc, url.path or "/", "", ""))
    except ValueError as exc:
        raise HTTPException(422, "Report URL must be a configured demo-store page.") from exc


def create_app(run_dir: Path | None = None, allowed_origins: set[str] | None = None,
               enable_investigation=True, settings_factory=Settings.read,
               provider_factory=CrusoeClient, browser_factory=BrowserSession):
    cases = Path(run_dir) if run_dir is not None else ROOT / "runs"
    store = CaseStore(cases)
    manager = RunManager(store, settings_factory, provider_factory, browser_factory)

    @asynccontextmanager
    async def lifespan(app):
        if enable_investigation:
            await manager.start()
        yield
        if enable_investigation:
            await manager.close()

    app = FastAPI(title="Repro", version="0.2.0", lifespan=lifespan)
    app.state.manager = manager
    local = dotenv_values(ROOT / '.env', interpolate=False)
    configured_origins = os.environ.get('REPRO_ALLOWED_ORIGINS') or local.get('REPRO_ALLOWED_ORIGINS') or 'http://127.0.0.1:8000,http://localhost:8000'
    origins = allowed_origins if allowed_origins is not None else {origin.strip() for origin in configured_origins.split(',')}
    app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
    app.mount("/store-assets", StaticFiles(directory=ROOT / "demo_store"), name="store-assets")

    @app.get("/health")
    async def health():
        return {"status": "ok", "milestone": 2, "investigation_enabled": enable_investigation,
                "provider": settings_factory().public(), "queued_cases": manager.queue.qsize(),
                "active_case": manager.active_id}

    @app.get("/", include_in_schema=False)
    async def storefront():
        return FileResponse(ROOT / "demo_store" / "index.html")

    @app.get("/rules", include_in_schema=False)
    async def rules_page():
        return FileResponse(ROOT / "demo_store" / "rules.html")

    @app.get("/cases/{case_id}", include_in_schema=False)
    async def case_page(case_id: UUID):
        return FileResponse(ROOT / "app" / "static" / "case.html")

    @app.post("/api/reports", status_code=202)
    async def submit_report(report: ReportInput):
        if enable_investigation and manager.queue.full():
            raise HTTPException(429, 'The local waiting list is full. Please try again shortly.')
        page_url = sanitize_url(report.page_url, origins)
        case_id = str(uuid4())
        case = {
            "id": case_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stage": "received",
            "outcome": None,
            "investigation_enabled": enable_investigation,
            "message": "Report saved. Investigations are disabled in this local profile.",
            "execution_mode": "disabled" if not enable_investigation else "unavailable",
            "report": {**report.model_dump(), "page_url": page_url},
        }
        try:
            store.save(case)
            if enable_investigation:
                manager.enqueue(case)
        except OSError as exc:
            raise HTTPException(503, "Could not save this report. Please try again.") from exc
        return {"case_id": case_id, "status_url": f"/cases/{case_id}",
                "api_url": f"/api/runs/{case_id}"}

    @app.get("/api/runs/{case_id}")
    def get_case(case_id: UUID):
        try:
            return store.read(case_id)
        except FileNotFoundError as exc:
            raise HTTPException(404, "Case not found.") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(503, "Case temporarily unavailable.") from exc

    @app.post('/api/runs/{case_id}/start', status_code=202)
    async def start_case(case_id: UUID):
        if not enable_investigation:
            raise HTTPException(409, 'Investigations are disabled in this profile.')
        case = get_case(case_id)
        try:
            manager.enqueue(case)
        except asyncio.QueueFull:
            raise HTTPException(429, 'The local waiting list is full.') from None
        except ValueError as error:
            raise HTTPException(409, str(error)) from None
        return {'case_id': str(case_id), 'stage': case['stage']}

    @app.post('/api/runs/{case_id}/cancel', status_code=202)
    async def cancel_case(case_id: UUID):
        case = get_case(case_id)
        manager.cancel(case)
        return {'case_id': str(case_id), 'cancellation_requested': True}

    @app.post('/api/runs/{case_id}/verify', status_code=202)
    async def verify_case(case_id: UUID):
        if not enable_investigation:
            raise HTTPException(409, 'Investigations are disabled in this profile.')
        case = get_case(case_id)
        try:
            manager.enqueue(case, verification_only=True)
        except asyncio.QueueFull:
            raise HTTPException(429, 'The local waiting list is full.') from None
        except ValueError as error:
            raise HTTPException(409, str(error)) from None
        return {'case_id': str(case_id), 'stage': case['stage']}

    @app.get('/api/runs/{case_id}/events')
    async def events(case_id: UUID, after: int = 0):
        get_case(case_id)
        rows = store.events(case_id, max(after, 0))
        return {'events': rows, 'next_cursor': rows[-1]['seq'] if rows else max(after, 0)}

    @app.get('/api/runs/{case_id}/artifacts/{artifact_id}')
    async def artifact(case_id: UUID, artifact_id: str):
        case = get_case(case_id)
        try:
            path, media_type = store.artifact_path(case, artifact_id)
        except FileNotFoundError:
            raise HTTPException(404, 'Artifact not found.') from None
        return FileResponse(path, media_type=media_type, filename=path.name)

    @app.post('/api/provider/check')
    async def provider_check():
        provider = provider_factory(settings_factory())
        try:
            return await provider.smoke_test()
        except ProviderError as error:
            raise HTTPException(503, {'code': error.code, 'message': str(error)}) from None
        finally:
            await provider.close()

    return app


app = create_app()
