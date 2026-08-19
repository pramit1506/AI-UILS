import copy
from typing import Dict, Any, List, Tuple, Optional
from app.schemas.draft import DynamicLogDraft, DraftUpdateResult, FieldMetadata
from app.shared.enums import DraftStatus


FIELD_ALIASES: Dict[str, List[str]] = {
    "vendor": ["vendor_name", "company", "vendor", "billed_by", "supplier", "issuer"],
    "vendor_name": ["vendor", "company", "vendor_name", "billed_by", "supplier", "issuer"],
    "total_amount": ["total", "total_amount_due", "total_due", "amount_due", "total_price", "amount", "grand_total"],
    "total": ["total_amount", "total_amount_due", "total_due", "amount_due", "total_price", "amount", "grand_total"],
    "invoice_number": ["invoice_no", "inv_number", "inv_no", "invoice_#", "reference_number", "bill_number"],
    "invoice_date": ["date", "issue_date", "billed_date", "bill_date"],
    "customer_name": ["customer", "client", "billed_to", "client_name", "customer_id"],
    "customer": ["customer_name", "client", "billed_to", "client_name"],
    "patient_name": ["patient", "name", "full_name", "patient_id"],
    "doctor_name": ["doctor", "physician", "provider", "dr_name"],
    "candidate_name": ["name", "full_name", "applicant_name"],
    "product_name": ["product", "item", "item_name", "device_name"],
    "batch_number": ["batch_no", "lot_number", "lot_no", "batch"],
    "effective_date": ["start_date", "agreement_date", "date"],
    "parties": ["party_a", "party_b", "contractor", "client", "parties_involved"],
}


class DraftService:
    """
    Service for managing a DynamicLogDraft lifecycle.
    Works with any schema — fields are stored as a flat key-value dict.
    """

    def _is_empty_value(self, val: Any) -> bool:
        if val is None:
            return True
        if isinstance(val, str) and not val.strip():
            return True
        if isinstance(val, list) and len(val) == 0:
            return True
        return False

    def required_missing_fields(self, draft: DynamicLogDraft, required: List[str] = None) -> List[str]:
        """Return list of required fields missing from the draft's fields dict."""
        fields = draft.fields or {}
        check = required if required is not None else []
        
        def _get_val(f: str) -> Any:
            if hasattr(draft, f) and f in ("schema_name", "domain", "source", "fields"):
                val = getattr(draft, f)
                if not self._is_empty_value(val):
                    return val
            if not self._is_empty_value(fields.get(f)):
                return fields.get(f)
            aliases = FIELD_ALIASES.get(f, [])
            for alias in aliases:
                if not self._is_empty_value(fields.get(alias)):
                    return fields.get(alias)
            return None
            
        return [f for f in check if self._is_empty_value(_get_val(f))]

    def has_any_data(self, draft: DynamicLogDraft) -> bool:
        fields = draft.fields or {}
        return any(not self._is_empty_value(v) for k, v in fields.items() if not k.startswith("_"))

    def is_ready(self, draft: DynamicLogDraft, required: List[str] = None) -> bool:
        """A draft is ready if schema_name is set, has actual data fields, and all required fields are filled."""
        if not draft.schema_name or not self.has_any_data(draft):
            return False
        return len(self.required_missing_fields(draft, required or [])) == 0

    def calculate_status(self, draft: DynamicLogDraft, required: List[str] = None) -> DraftStatus:
        if not self.has_any_data(draft):
            return DraftStatus.EMPTY
        if self.is_ready(draft, required):
            return DraftStatus.READY
        return DraftStatus.PARTIAL

    def validate(self, draft: DynamicLogDraft, required: List[str] = None) -> Dict[str, Any]:
        """Returns a validation summary for the current draft."""
        required = required or []
        req_missing = self.required_missing_fields(draft, required)
        status = self.calculate_status(draft, required)
        return {
            "is_ready": len(req_missing) == 0 and bool(draft.schema_name) and self.has_any_data(draft),
            "status": status,
            "required_missing": req_missing,
            "optional_missing": [],
        }

    def validate_against_schema(self, draft: DynamicLogDraft, required_fields: List[str], optional_fields: List[str]) -> Dict[str, Any]:
        """Validates the draft against explicitly provided required/optional field lists."""
        fields = draft.fields or {}
        
        def _get_val(f: str) -> Any:
            if hasattr(draft, f) and f in ("schema_name", "domain", "source", "fields"):
                val = getattr(draft, f)
                if not self._is_empty_value(val):
                    return val
            if not self._is_empty_value(fields.get(f)):
                return fields.get(f)
            aliases = FIELD_ALIASES.get(f, [])
            for alias in aliases:
                if not self._is_empty_value(fields.get(alias)):
                    return fields.get(alias)
            return None

        req_missing = [f for f in required_fields if self._is_empty_value(_get_val(f))]
        opt_missing = [f for f in optional_fields if self._is_empty_value(_get_val(f))]

        has_data = self.has_any_data(draft)
        if not has_data:
            status = DraftStatus.EMPTY
        elif len(req_missing) == 0:
            status = DraftStatus.READY
        else:
            status = DraftStatus.PARTIAL

        return {
            "is_ready": len(req_missing) == 0 and has_data,
            "status": status,
            "required_missing": req_missing,
            "optional_missing": opt_missing,
        }

    # --------------------------------------------------------------------------
    # Core mutation methods — all return a new DynamicLogDraft (immutable style)
    # --------------------------------------------------------------------------

    def merge(
        self,
        draft: DynamicLogDraft,
        extracted_fields: Dict[str, Any],
        metadata: Optional[Dict[str, FieldMetadata]] = None,
    ) -> DraftUpdateResult:
        """
        Merge newly extracted fields into the draft.
        Top-level keys (schema_name, domain, source) are handled separately.
        All other keys go into draft.fields.
        """
        updated = copy.deepcopy(draft)
        changed_fields: List[str] = []

        # Handle top-level schema keys
        for top_key in ("schema_name", "domain", "source"):
            new_val = extracted_fields.get(top_key)
            if new_val is not None and new_val != getattr(updated, top_key):
                setattr(updated, top_key, new_val)
                changed_fields.append(top_key)

        # All other extracted keys go into the flexible fields dict
        for key, value in extracted_fields.items():
            if key in ("schema_name", "domain", "source", "field_metadata"):
                continue
            if self._is_empty_value(value):
                continue
            current = updated.fields.get(key)
            if isinstance(current, list) and isinstance(value, list):
                added = [v for v in value if v not in current]
                if added:
                    updated.fields[key] = current + added
                    changed_fields.append(key)
            else:
                if current != value:
                    updated.fields[key] = value
                    changed_fields.append(key)

        # Merge metadata
        if metadata:
            for field, meta in metadata.items():
                if isinstance(meta, FieldMetadata):
                    updated.field_metadata[field] = meta
                elif isinstance(meta, dict):
                    updated.field_metadata[field] = FieldMetadata(**meta)

        return DraftUpdateResult(
            updated_draft=updated,
            changed_fields=list(set(changed_fields)),
            merge_summary=f"Merged {len(set(changed_fields))} fields.",
        )

    def update_field(
        self,
        draft: DynamicLogDraft,
        field_name: str,
        value: Any,
        metadata: Optional[FieldMetadata] = None,
    ) -> DraftUpdateResult:
        """Explicitly overwrite a single field."""
        updated = copy.deepcopy(draft)
        changed_fields = []

        # Handle top-level schema keys
        if field_name in ("schema_name", "domain", "source"):
            if getattr(updated, field_name) != value:
                setattr(updated, field_name, value)
                changed_fields.append(field_name)
        else:
            if updated.fields.get(field_name) != value:
                updated.fields[field_name] = value
                changed_fields.append(field_name)

        if metadata and changed_fields:
            updated.field_metadata[field_name] = metadata

        return DraftUpdateResult(
            updated_draft=updated,
            changed_fields=changed_fields,
            merge_summary=f"Updated field '{field_name}'.",
        )

    def correct_field(
        self,
        draft: DynamicLogDraft,
        field_name: str,
        value: Any,
        metadata: Optional[FieldMetadata] = None,
    ) -> DraftUpdateResult:
        """Alias for update_field used for conversational corrections."""
        return self.update_field(draft, field_name, value, metadata)

    def remove_field(self, draft: DynamicLogDraft, field_name: str) -> DraftUpdateResult:
        """Clear a field's value from the draft."""
        updated = copy.deepcopy(draft)
        changed_fields = []

        if field_name in ("schema_name", "domain", "source"):
            if getattr(updated, field_name) is not None:
                setattr(updated, field_name, None)
                changed_fields.append(field_name)
        elif field_name in updated.fields:
            del updated.fields[field_name]
            changed_fields.append(field_name)
            updated.field_metadata.pop(field_name, None)

        return DraftUpdateResult(
            updated_draft=updated,
            changed_fields=changed_fields,
            merge_summary=f"Removed field '{field_name}'.",
        )

    # --------------------------------
    # Convenience accessors
    # --------------------------------

    # For backward compatibility with decision_service validation calls
    REQUIRED_FIELDS: List[str] = []
    OPTIONAL_FIELDS: List[str] = []
