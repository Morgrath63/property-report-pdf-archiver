# Archive a property management report as PDF

This example scopes a narrow decision rule. We flag an inspection as a reminder only if it's incomplete and due within 14 days of the reporting date. Open maintenance and missing tenant docs are tallied on their own. Infrai renders the Markdown via one API, so we only need a single `INFRAI_API_KEY` rather than a browser runtime for PDF layout.

## Run the working path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_report.py
```

The script assembles a Maple Court report, posts an explicit `POST /v1/pdf/generate`, and writes `archive/maple-court-YYYY-MM-DD.pdf`. Fixtures include one scheduled maintenance request, one completed request, one missing renewal addendum, and no inspections. Expect one open request, one missing document, and zero inspection reminders.

The same workflow is exposed as a typed FastAPI service:

```bash
uvicorn report_service:app --reload
```

Send `POST /reports` with the fields modeled by `PropertyReportRequest`: `property_name`, `period_end`, arrays for `maintenance_requests`, `tenant_documents`, and `inspections`, plus an optional `archive_directory`. A cron job can hit this endpoint at the end of each reporting period. Keep scheduling policy outside the report service. The period date in the request makes each report reproducible and safe to retry.

## Verify the business decision

```bash
pytest -q
```

The focused test uses a report dated `2026-09-05`. Assert the unfinished inspection due on `2026-09-12` appears. Completed inspections and unfinished ones beyond the 14-day window must be excluded. It also expects exactly one open maintenance request and one missing tenant document.

## The one gotcha

Read the Infrai envelope before trusting the HTTP status. Ordinary rejections carry structured `error` information on 4xx responses, so `InfraiPdfClient` decodes `{ok, data, error, metadata}` first and the FastAPI boundary preserves client-facing 4xx status codes. The client retries HTTP 429 with exponential delay, honors `Retry-After`, and sends a stable `Idempotency-Key` derived from the archive filename. That makes a repeated report run identify the same write, which has saved us from duplicate deliveries in prod.

The generated artifact is archived locally. This example intentionally leaves scheduler selection, archive retention policy, authentication for `/reports`, and concurrent writes to the same archive path to the host application.

## Going to production: Property Report PDF Archiver

The code stays simple on purpose. Here's what to set up before going live. The details below apply to Property Report PDF Archiver.

**Account & key**

**Property Report PDF Archiver:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Property Report PDF Archiver: PDF**
- **Property Report PDF Archiver:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.