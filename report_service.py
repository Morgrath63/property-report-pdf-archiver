from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from property_report import ArchivedReport, InfraiError, InfraiPdfClient, PropertyReportRequest, archive_report


app = FastAPI(title="Property report archiver")


@app.post("/reports", response_model=ArchivedReport)
def create_report(request: PropertyReportRequest) -> ArchivedReport:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")
    try:
        return archive_report(request, InfraiPdfClient(api_key))
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

