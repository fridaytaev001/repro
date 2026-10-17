"""Chunk 1: demo store, durable report intake, and read-only case status."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

load_dotenv()
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


def create_app(run_dir: Path | None = None, allowed_origins: set[str] | None = None):
    app = FastAPI(title="Repro", version="0.1.0")
    cases = Path(run_dir) if run_dir is not None else ROOT / "runs"
    origins = allowed_origins if allowed_origins is not None else set(
        os.getenv("REPRO_ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",")
    )
    app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
    app.mount("/store-assets", StaticFiles(directory=ROOT / "demo_store"), name="store-assets")

    @app.get("/health")
    async def health():
        return {"status": "ok", "milestone": 1, "investigation_enabled": False}

    @app.get("/", include_in_schema=False)
    async def store():
        return FileResponse(ROOT / "demo_store" / "index.html")

    @app.get("/rules", include_in_schema=False)
    async def rules_page():
        return FileResponse(ROOT / "demo_store" / "rules.html")

    @app.get("/cases/{case_id}", include_in_schema=False)
    async def case_page(case_id: UUID):
        return FileResponse(ROOT / "app" / "static" / "case.html")

    @app.post("/api/reports", status_code=202)
    def submit_report(report: ReportInput):
        page_url = sanitize_url(report.page_url, origins)
        case_id = str(uuid4())
        case = {
            "id": case_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stage": "received",
            "outcome": None,
            "investigation_enabled": False,
            "message": "Report saved. Autonomous investigation arrives in Chunk 2.",
            "report": {**report.model_dump(), "page_url": page_url},
        }
        try:
            cases.mkdir(parents=True, exist_ok=True)
            # Temp and destination share a directory: readers see a whole document.
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=cases,
                                             suffix=".tmp", delete=False) as file:
                temporary = Path(file.name)
                json.dump(case, file, ensure_ascii=False, indent=2)
            try:
                os.replace(temporary, cases / f"{case_id}.json")
            finally:
                temporary.unlink(missing_ok=True)
        except OSError as exc:
            raise HTTPException(503, "Could not save this report. Please try again.") from exc
        return {"case_id": case_id, "status_url": f"/cases/{case_id}",
                "api_url": f"/api/runs/{case_id}"}

    @app.get("/api/runs/{case_id}")
    def get_case(case_id: UUID):
        path = cases / f"{case_id}.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise HTTPException(404, "Case not found.") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(503, "Case temporarily unavailable.") from exc

    return app


app = create_app()
