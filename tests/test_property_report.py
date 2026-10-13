from datetime import date

from property_report import PropertyReportRequest, build_report


def test_report_selects_open_work_missing_documents_and_near_inspections() -> None:
    request = PropertyReportRequest.model_validate(
        {
            "property_name": "Maple Court",
            "period_end": "2026-09-05",
            "maintenance_requests": [
                {"request_id": "MR-1", "unit": "2B", "summary": "Tap leak", "status": "scheduled"},
                {"request_id": "MR-2", "unit": "3C", "summary": "Door latch", "status": "completed"},
            ],
            "tenant_documents": [
                {"tenant": "A. Rivera", "document_name": "renewal addendum", "received": False},
                {"tenant": "J. Chen", "document_name": "insurance certificate", "received": True},
            ],
            "inspections": [
                {"unit": "2B", "due_on": "2026-09-12", "completed": False},
                {"unit": "4D", "due_on": "2026-09-25", "completed": False},
                {"unit": "1A", "due_on": "2026-09-09", "completed": True},
            ],
        }
    )

    decision = build_report(request)

    assert decision.open_maintenance_count == 1
    assert decision.missing_document_count == 1
    assert decision.inspection_reminder_count == 1
    assert "2B: Tap leak [scheduled]" in decision.markdown
    assert "A. Rivera: renewal addendum" in decision.markdown
    assert "2B: due 2026-09-12" in decision.markdown
    assert "4D: due" not in decision.markdown
    assert date.fromisoformat("2026-09-05") == request.period_end

