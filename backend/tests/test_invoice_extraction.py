import pytest
from app.graph.nodes import _fallback_extract_fields
from app.schemas.draft import DynamicLogDraft
from app.services.draft_service import DraftService
from app.tools.save_log import SaveLogTool
from app.tools.context import ToolExecutionContext
from loguru import logger
from app.core.config import settings


def test_invoice_fallback_extraction():
    invoice_text = """Process this uploaded document (sample_invoice_INV-8492.txt):

ACME INDUSTRIAL SUPPLY CORP
1044 Innovation Way, Suite 300, Austin, TX 78701
Phone: (512) 555-0199 | Email: billing@acmesupply.com

INVOICE
Invoice Number: INV-2026-8492
Invoice Date: August 14, 2026
Due Date: September 13, 2026
Payment Terms: Net 30

BILLED TO:
Apex Logistics & Freight Inc.
Attn: Accounts Payable
450 Harbor Blvd, Long Beach, CA 90802
Customer ID: CUST-99214

DESCRIPTION OF SERVICES & MATERIALS:
1. Heavy Duty Conveyor Roller 400mm (Qty: 24) @ $125.00 = $3,000.00
2. Industrial High-Torque Drive Motor 5HP (Qty: 2) @ $1,450.00 = $2,900.00
3. Installation, Calibration & Onsite Testing (Qty: 12 hrs) @ $150.00/hr = $1,800.00
4. Freight & Hazardous Material Handling = $350.00

SUBTOTAL: $8,050.00
TAX (8.25%): $664.13
TOTAL AMOUNT DUE: $8,714.13

Wire Instructions:
Bank: First National Commercial Bank
Routing: 121000358
Account: 948201948201
Remit To: payments@acmesupply.com"""

    extracted, corrections = _fallback_extract_fields(invoice_text)

    assert extracted.get("schema_name") == "Invoice"
    assert extracted.get("domain") == "Finance"
    assert extracted.get("invoice_number") == "INV-2026-8492"
    assert "ACME INDUSTRIAL SUPPLY CORP" in (extracted.get("vendor") or extracted.get("vendor_name") or "")
    assert extracted.get("customer_name") == "Apex Logistics & Freight Inc."
    assert "$8,714.13" in extracted.get("total_amount", "")
    assert extracted.get("subtotal") == "$8,050.00"
    assert extracted.get("due_date") == "2026-09-13"


def test_medical_record_fallback_extraction():
    medical_text = """CLINICAL INTAKE & MEDICAL RECORD
Patient Name: Sarah Connor
Patient ID: PAT-88219
Date of Visit: August 18, 2026
Attending Physician: Dr. Marcus Vance
Department: Cardiology

CHIEF COMPLAINT:
Patient presents with persistent shortness of breath.

DIAGNOSIS:
Diagnosis: Mild Sinus Tachycardia and Stage 1 Hypertension"""

    extracted, corrections = _fallback_extract_fields(medical_text)

    assert extracted.get("schema_name") == "Medical Record"
    assert extracted.get("domain") == "Healthcare"
    assert extracted.get("patient_name") == "Sarah Connor"
    assert extracted.get("doctor_name") == "Dr. Marcus Vance"
    assert "Mild Sinus Tachycardia" in extracted.get("diagnosis", "")


def test_resume_fallback_extraction():
    resume_text = """CANDIDATE PROFILE:
Candidate Name: Alexander Morgan
Position Applied: Lead Systems Architect
Years of Experience: 8 years
Highest Education: M.S. in Computer Science, Stanford University

CORE SKILLS:
Python, TypeScript, React, PostgreSQL, LangGraph"""

    extracted, corrections = _fallback_extract_fields(resume_text)

    assert extracted.get("schema_name") == "Resume"
    assert extracted.get("domain") == "HR"
    assert extracted.get("candidate_name") == "Alexander Morgan"


def test_complaint_fallback_extraction():
    complaint_text = """INCIDENT / COMPLAINT REPORT
Complaint ID: QC-2026-1092
Customer Name: St. Jude Medical Center
Product Name: Precision IV Infusion Pump Pro
Batch Number: LOT-2026-88B

DESCRIPTION OF ISSUE:
Pump stopped delivering fluid and triggered error code ERR-402."""

    extracted, corrections = _fallback_extract_fields(complaint_text)

    assert extracted.get("schema_name") == "Complaint"
    assert extracted.get("domain") == "Quality Management"
    assert extracted.get("product_name") == "Precision IV Infusion Pump Pro"
    assert extracted.get("batch_number") == "LOT-2026-88B"
    assert extracted.get("customer_name") == "St. Jude Medical Center"


def test_draft_service_alias_validation():
    draft_service = DraftService()
    draft = DynamicLogDraft(
        schema_name="Invoice",
        domain="Finance",
        fields={
            "invoice_number": "INV-2026-8492",
            "invoice_date": "2026-08-14",
            "vendor_name": "ACME INDUSTRIAL SUPPLY CORP",  # alias for vendor
            "total_amount_due": "$8,714.13",             # alias for total_amount
        }
    )

    required = ["invoice_number", "invoice_date", "vendor", "total_amount"]
    validation = draft_service.validate_against_schema(draft, required, [])

    assert validation["is_ready"] is True
    assert len(validation["required_missing"]) == 0


def test_empty_draft_not_ready():
    draft_service = DraftService()
    draft = DynamicLogDraft(
        schema_name="General Document",
        domain="General",
        fields={}
    )

    validation = draft_service.validate_against_schema(draft, [], [])
    assert validation["is_ready"] is False
    assert draft_service.is_ready(draft) is False


@pytest.mark.asyncio
async def test_save_log_tool_rejects_empty_fields():
    tool = SaveLogTool()
    context = ToolExecutionContext(
        db=None,
        request_id="test-req",
        conversation_id="test-conv",
        logger=logger,
        settings=settings,
        current_user=None,
        llm_provider=None,
    )

    result = await tool.execute(
        context,
        schema_name="General Document",
        domain="General",
        fields={},
        field_metadata={}
    )

    assert result["status"] == "error"
    assert "No extracted data fields found" in result["message"]
