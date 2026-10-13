from __future__ import annotations

import os
from datetime import date

from property_report import InfraiPdfClient, PropertyReportRequest, archive_report


def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("Set INFRAI_API_KEY before running the report")

    report = PropertyReportRequest.model_validate(
        {
            "property_name": "Maple Court",
            "period_end": date.today().isoformat(),
            "maintenance_requests": [
                {"request_id": "MR-104", "unit": "2B", "summary": "Kitchen tap leak", "status": "scheduled"},
                {"request_id": "MR-099", "unit": "1A", "summary": "Replace hallway bulb", "status": "completed"},
            ],
            "tenant_documents": [
                {"tenant": "A. Rivera", "document_name": "renewal addendum", "received": False}
            ],
            "inspections": [],
            "archive_directory": "archive",
        }
    )
    archived = archive_report(report, InfraiPdfClient(api_key))
    print(f"Archived {archived.archive_path}")
    print(archived.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

