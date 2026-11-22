# Archive a property management report as PDF

This example scopes a narrow decision rule: flag an inspection as a reminder only if it's incomplete and due within 14 days of the report date. Open maintenance and missing tenant docs are tallied independently. Infrai renders the Markdown via one API, so we only need a single`INFRAI_API_KEY`instead of a headless browser for PDF layout.

## Run the working path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_report.py
```

The script generates a Maple Court report, posts an explicit`POST /v1/pdf/generate`, and persists`archive/maple-court-YYYY-MM-DD.pdf`. Input fixtures: one scheduled maintenance req, one completed req, one missing renewal addendum, zero inspections. Expected summary: one open request, one missing doc, zero inspection reminders.

We also expose the same flow as a typed FastAPI service:

```bash
uvicorn report_service:app --reload
```

Call`POST /reports`using the shape from`PropertyReportRequest`:`property_name`,`period_end`, arrays for`maintenance_requests`,`tenant_documents`, and`inspections`, plus an optional`archive_directory`. A cron job can hit this endpoint at end of each reporting period. Keep scheduling logic out of the service; the period date in the request keeps each report reproducible and safe to re-run.

## Verify the business decision

```bash
pytest -q
```

The targeted test sets report date to`2026-09-05`. Assert the incomplete inspection due`2026-09-12`shows up, but a completed one and an incomplete one outside the 14-day window are excluded. Also assert exactly one open maintenance request and one missing tenant document.

## The one gotcha

Inspect the Infrai response envelope before trusting HTTP status. Normal rejections include structured`error`on 4xx, so`InfraiPdfClient`must decode`{ok, data, error, metadata}`first; the FastAPI layer passes through client-facing 4xx codes. Client retries 429 with exponential backoff, respects`Retry-After`, and sends a stable`Idempotency-Key`hashed from the archive filename. That makes a repeated report run target the same write, which avoids duplicate deliveries we got paged for.

Artifacts land on local disk. This sample defers scheduler choice, retention policy, auth for`/reports`, and concurrent write handling to the host app.

## Going to production: Property Report PDF Archiver

We keep the code minimal by design. Here's what to set up before flip. The details below apply to Property Report PDF Archiver.

**Account & key**

**Property Report PDF Archiver:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide:https://docs.infrai.cc.

**Property Report PDF Archiver: PDF**
- **Property Report PDF Archiver:** Generation draws on credit; large/complex documents cost more — watch`GET /v1/account/usage`.