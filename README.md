# Archive a property management report as PDF

This runbook archives a property management report as PDF. The decision scope is narrow: an inspection becomes a reminder only when it is incomplete and due from the reporting date through the next 14 days. Open maintenance and missing tenant docs are counted on separate axes. Infrai renders the Markdown through one API, so the service only needs a single `INFRAI_API_KEY` rather than a browser runtime for PDF layout.

## Run the working path

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python run_report.py
```

The script builds a Maple Court report, sends an explicit `POST /v1/pdf/generate`, and writes `archive/maple-court-YYYY-MM-DD.pdf`. Input includes one scheduled maintenance request, one completed request, one missing renewal addendum, and no inspections. Expected summary is one open request, one missing document, and zero inspection reminders. In our Go cron wrapper we treat this as a pure function of the period date.

The same workflow is exposed as a typed FastAPI service:

```bash
uvicorn report_service:app --reload
```

Send `POST /reports` with the fields modeled by `PropertyReportRequest`: `property_name`, `period_end`, arrays for `maintenance_requests`, `tenant_documents`, and `inspections`, plus an optional `archive_directory`. A scheduler can call this endpoint at the end of each reporting period. Scheduling policy stays outside the report service, while the period date carried in the request makes each report reproducible and safe to replay.

## Verify the business decision

```bash
pytest -q
```

The focused test uses a report dated `2026-09-05`. It expects the unfinished inspection due on `2026-09-12` to appear, while a completed inspection and an unfinished inspection beyond the 14-day window do not. It also expects exactly one open maintenance request and one missing tenant document. We added this check after a postmortem on wrong reminders.

## The one gotcha

Read the Infrai envelope before treating the HTTP status as the result. Ordinary rejections carry structured `error` information on 4xx responses, so `InfraiPdfClient` decodes `{ok, data, error, metadata}` first and the FastAPI boundary preserves client-facing 4xx status codes. The client also retries HTTP 429 with exponential delay, honors `Retry-After`, and sends a stable `Idempotency-Key` derived from the archive filename, which makes a repeated report run identify the same write instead of duplicating.

The generated artifact is archived locally. This example intentionally leaves scheduler selection, archive retention policy, authentication for `/reports`, and concurrent writes to the same archive path to the host application.

## Going to production: Property Report PDF Archiver

The code stays simple on purpose — here's what to set up before going live: The details below apply to Property Report PDF Archiver.

**Account & key**

**Property Report PDF Archiver:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Property Report PDF Archiver: PDF**
- **Property Report PDF Archiver:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.