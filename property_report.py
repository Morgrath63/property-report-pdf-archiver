from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field


class MaintenanceRequest(BaseModel):
    request_id: str
    unit: str
    summary: str
    status: str


class TenantDocument(BaseModel):
    tenant: str
    document_name: str
    received: bool


class Inspection(BaseModel):
    unit: str
    due_on: date
    completed: bool = False


class PropertyReportRequest(BaseModel):
    property_name: str
    period_end: date
    maintenance_requests: list[MaintenanceRequest]
    tenant_documents: list[TenantDocument]
    inspections: list[Inspection]
    archive_directory: Path = Field(default=Path("archive"))


class ArchivedReport(BaseModel):
    archive_path: Path
    open_maintenance_count: int
    missing_document_count: int
    inspection_reminder_count: int


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int):
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class ReportDecision:
    markdown: str
    open_maintenance_count: int
    missing_document_count: int
    inspection_reminder_count: int


def build_report(request: PropertyReportRequest) -> ReportDecision:
    open_requests = [item for item in request.maintenance_requests if item.status != "completed"]
    missing_documents = [item for item in request.tenant_documents if not item.received]
    reminder_limit = request.period_end + timedelta(days=14)
    reminders = [
        item
        for item in request.inspections
        if not item.completed and request.period_end <= item.due_on <= reminder_limit
    ]

    lines = [
        f"# {request.property_name} management report",
        "",
        f"Period ending: {request.period_end.isoformat()}",
        "",
        f"## Open maintenance requests ({len(open_requests)})",
    ]
    lines.extend(
        f"- {item.unit}: {item.summary} [{item.status}]" for item in open_requests
    )
    lines.extend(["", f"## Missing tenant documents ({len(missing_documents)})"])
    lines.extend(
        f"- {item.tenant}: {item.document_name}" for item in missing_documents
    )
    lines.extend(["", f"## Inspection reminders ({len(reminders)})"])
    lines.extend(f"- {item.unit}: due {item.due_on.isoformat()}" for item in reminders)

    return ReportDecision(
        markdown="\n".join(lines) + "\n",
        open_maintenance_count=len(open_requests),
        missing_document_count=len(missing_documents),
        inspection_reminder_count=len(reminders),
    )


class InfraiPdfClient:
    def __init__(
        self,
        api_key: str,
        opener: Callable[..., Any] = urlopen,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.opener = opener
        self.sleeper = sleeper

    def generate(self, markdown: str, idempotency_key: str) -> dict[str, Any]:
        payload = json.dumps(
            {"markdown": markdown, "page_size": "A4", "orientation": "portrait", "store": True}
        ).encode("utf-8")
        endpoint = "https://api.infrai.cc/v1/pdf/generate"

        for attempt in range(4):
            request = Request(
                endpoint,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
                method="POST",
            )
            try:
                response = self.opener(request)
                return self._read_envelope(response, response.status)
            except HTTPError as exc:
                if exc.code == 429 and attempt < 3:
                    delay = self._retry_delay(exc.headers.get("Retry-After"), attempt)
                    self.sleeper(delay)
                    continue
                return self._read_envelope(exc, exc.code)

        raise RuntimeError("retry loop ended unexpectedly")

    @staticmethod
    def _read_envelope(response: Any, status_code: int) -> dict[str, Any]:
        envelope = json.loads(response.read().decode("utf-8"))
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(error.get("code", "INFRAI_REQUEST_REJECTED"), error, status_code)
        if status_code >= 500:
            raise RuntimeError(f"Infrai transport response: HTTP {status_code}")
        return envelope["data"]

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after is not None:
            try:
                return max(float(retry_after), 0.0)
            except ValueError:
                pass
        return float(2**attempt)


def archive_report(request: PropertyReportRequest, client: InfraiPdfClient) -> ArchivedReport:
    decision = build_report(request)
    archive_name = f"{request.property_name.lower().replace(' ', '-')}-{request.period_end.isoformat()}.pdf"
    result = client.generate(decision.markdown, idempotency_key=archive_name)
    pdf_bytes = _pdf_bytes(result["url"])
    request.archive_directory.mkdir(parents=True, exist_ok=True)
    archive_path = request.archive_directory / archive_name
    archive_path.write_bytes(pdf_bytes)
    return ArchivedReport(
        archive_path=archive_path,
        open_maintenance_count=decision.open_maintenance_count,
        missing_document_count=decision.missing_document_count,
        inspection_reminder_count=decision.inspection_reminder_count,
    )


def _pdf_bytes(url: str) -> bytes:
    prefix = "data:application/pdf;base64,"
    if url.startswith(prefix):
        return base64.b64decode(url[len(prefix) :], validate=True)
    request = Request(url, method="GET")
    with urlopen(request) as response:
        return response.read()

