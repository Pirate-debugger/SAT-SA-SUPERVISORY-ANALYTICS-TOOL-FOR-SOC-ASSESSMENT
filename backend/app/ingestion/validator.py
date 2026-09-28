from typing import List, Dict, Any, Tuple, Optional, Set
from pydantic import ValidationError
from app.schemas.canonical import AlertCanonical, CaseCanonical
from app.ingestion.normalizer import (
    parse_datetime, normalize_severity, normalize_status,
    normalize_disposition, normalize_boolean, normalize_category
)


REQUIRED_ALERT_FIELDS = ["entity_id", "alert_id", "alert_timestamp", "severity", "category"]
REQUIRED_CASE_FIELDS = ["entity_id", "case_id", "created_at"]


def validate_and_normalize_alert(
    raw_dict: Dict[str, Any],
    row_idx: int,
    seen_alert_ids: Set[str]
) -> Tuple[Optional[AlertCanonical], Optional[Dict[str, Any]], List[str]]:
    """
    Returns (canonical_alert, error_dict, warnings)
    """
    warnings: List[str] = []

    # Check required fields
    entity_id = raw_dict.get("entity_id")
    if not entity_id or str(entity_id).strip() == "":
        return None, {
            "row_index": row_idx,
            "error_type": "MISSING_REQUIRED_FIELD",
            "field": "entity_id",
            "raw": raw_dict
        }, warnings

    alert_id = raw_dict.get("alert_id")
    if not alert_id or str(alert_id).strip() == "":
        return None, {
            "row_index": row_idx,
            "error_type": "MISSING_REQUIRED_FIELD",
            "field": "alert_id",
            "raw": raw_dict
        }, warnings

    alert_id_str = str(alert_id).strip()
    if alert_id_str in seen_alert_ids:
        return None, {
            "row_index": row_idx,
            "error_type": "DUPLICATE_ID",
            "field": "alert_id",
            "value": alert_id_str,
            "raw": raw_dict
        }, warnings
    seen_alert_ids.add(alert_id_str)

    # Date parsing
    alert_timestamp = parse_datetime(raw_dict.get("alert_timestamp"))
    if not alert_timestamp:
        return None, {
            "row_index": row_idx,
            "error_type": "INVALID_TIMESTAMP",
            "field": "alert_timestamp",
            "value": str(raw_dict.get("alert_timestamp")),
            "raw": raw_dict
        }, warnings

    # Optional dates
    ack_ts = parse_datetime(raw_dict.get("acknowledged_timestamp"))
    inv_ts = parse_datetime(raw_dict.get("investigation_started_timestamp"))
    closed_ts = parse_datetime(raw_dict.get("closed_timestamp"))
    esc_ts = parse_datetime(raw_dict.get("escalation_timestamp"))

    # Logic date order warnings
    if ack_ts and alert_timestamp and ack_ts < alert_timestamp:
        warnings.append(f"Row {row_idx}: acknowledged_timestamp is earlier than alert_timestamp.")
    if closed_ts and alert_timestamp and closed_ts < alert_timestamp:
        warnings.append(f"Row {row_idx}: closed_timestamp is earlier than alert_timestamp.")

    # Categorical normalization
    severity = normalize_severity(raw_dict.get("severity"))
    category = normalize_category(raw_dict.get("category"))
    status = normalize_status(raw_dict.get("status"))
    disposition = normalize_disposition(raw_dict.get("disposition"))

    # Booleans
    escalated = normalize_boolean(raw_dict.get("escalated"))
    root_cause = normalize_boolean(raw_dict.get("root_cause_recorded")) or False
    remediation = normalize_boolean(raw_dict.get("remediation_recorded")) or False
    evidence = normalize_boolean(raw_dict.get("evidence_present")) or False

    try:
        canonical = AlertCanonical(
            entity_id=str(entity_id).strip(),
            alert_id=alert_id_str,
            alert_timestamp=alert_timestamp,
            severity=severity,
            category=category,
            source_system=str(raw_dict.get("source_system")).strip() if raw_dict.get("source_system") else None,
            asset_id=str(raw_dict.get("asset_id")).strip() if raw_dict.get("asset_id") else None,
            acknowledged_timestamp=ack_ts,
            investigation_started_timestamp=inv_ts,
            closed_timestamp=closed_ts,
            disposition=disposition,
            escalated=escalated,
            escalation_timestamp=esc_ts,
            investigator_id=str(raw_dict.get("investigator_id")).strip() if raw_dict.get("investigator_id") else None,
            root_cause_recorded=root_cause,
            remediation_recorded=remediation,
            evidence_present=evidence,
            status=status,
            raw_data=raw_dict.get("raw_data")
        )
        return canonical, None, warnings
    except ValidationError as e:
        return None, {
            "row_index": row_idx,
            "error_type": "SCHEMA_VALIDATION_ERROR",
            "details": e.errors(),
            "raw": raw_dict
        }, warnings


def validate_and_normalize_case(
    raw_dict: Dict[str, Any],
    row_idx: int,
    seen_case_ids: Set[str]
) -> Tuple[Optional[CaseCanonical], Optional[Dict[str, Any]], List[str]]:
    """
    Returns (canonical_case, error_dict, warnings)
    """
    warnings: List[str] = []

    entity_id = raw_dict.get("entity_id")
    if not entity_id or str(entity_id).strip() == "":
        return None, {
            "row_index": row_idx,
            "error_type": "MISSING_REQUIRED_FIELD",
            "field": "entity_id",
            "raw": raw_dict
        }, warnings

    case_id = raw_dict.get("case_id")
    if not case_id or str(case_id).strip() == "":
        return None, {
            "row_index": row_idx,
            "error_type": "MISSING_REQUIRED_FIELD",
            "field": "case_id",
            "raw": raw_dict
        }, warnings

    case_id_str = str(case_id).strip()
    if case_id_str in seen_case_ids:
        return None, {
            "row_index": row_idx,
            "error_type": "DUPLICATE_ID",
            "field": "case_id",
            "value": case_id_str,
            "raw": raw_dict
        }, warnings
    seen_case_ids.add(case_id_str)

    created_at = parse_datetime(raw_dict.get("created_at"))
    if not created_at:
        return None, {
            "row_index": row_idx,
            "error_type": "INVALID_TIMESTAMP",
            "field": "created_at",
            "value": str(raw_dict.get("created_at")),
            "raw": raw_dict
        }, warnings

    assigned_at = parse_datetime(raw_dict.get("assigned_at"))
    inv_start = parse_datetime(raw_dict.get("investigation_started_at"))
    closed_at = parse_datetime(raw_dict.get("closed_at"))
    esc_ts = parse_datetime(raw_dict.get("escalation_timestamp"))

    disposition = normalize_disposition(raw_dict.get("disposition"))

    try:
        canonical = CaseCanonical(
            entity_id=str(entity_id).strip(),
            case_id=case_id_str,
            alert_id=str(raw_dict.get("alert_id")).strip() if raw_dict.get("alert_id") else None,
            created_at=created_at,
            assigned_at=assigned_at,
            investigation_started_at=inv_start,
            escalation_status=str(raw_dict.get("escalation_status")).strip() if raw_dict.get("escalation_status") else None,
            escalation_timestamp=esc_ts,
            closed_at=closed_at,
            disposition=disposition,
            root_cause=str(raw_dict.get("root_cause")).strip() if raw_dict.get("root_cause") else None,
            remediation=str(raw_dict.get("remediation")).strip() if raw_dict.get("remediation") else None,
            evidence=str(raw_dict.get("evidence")).strip() if raw_dict.get("evidence") else None,
            investigator=str(raw_dict.get("investigator")).strip() if raw_dict.get("investigator") else None,
            closure_reason=str(raw_dict.get("closure_reason")).strip() if raw_dict.get("closure_reason") else None
        )
        return canonical, None, warnings
    except ValidationError as e:
        return None, {
            "row_index": row_idx,
            "error_type": "SCHEMA_VALIDATION_ERROR",
            "details": e.errors(),
            "raw": raw_dict
        }, warnings
