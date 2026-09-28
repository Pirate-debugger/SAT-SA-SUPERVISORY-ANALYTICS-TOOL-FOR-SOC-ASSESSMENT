import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any


ALERT_SIGNALS = {
    "alert_id": 5, "alertid": 5, "id": 1,
    "severity": 4, "priority": 3, "sev": 4,
    "category": 3, "signature": 3, "rule_name": 3, "alert_type": 3,
    "asset_id": 3, "hostname": 2, "source_system": 2, "device_ip": 2,
    "acknowledged_timestamp": 3, "ack_time": 3,
    "closed_timestamp": 3, "close_time": 3,
}

CASE_SIGNALS = {
    "case_id": 5, "ticket_id": 5, "incident_id": 5,
    "investigation_started_at": 4, "assigned_at": 3,
    "escalation_status": 4, "root_cause": 4, "remediation": 4,
    "closure_reason": 4, "investigator": 3,
}

CANONICAL_ALERT_FIELDS = [
    "entity_id", "alert_id", "alert_timestamp", "severity", "category",
    "source_system", "asset_id", "acknowledged_timestamp",
    "investigation_started_timestamp", "closed_timestamp", "disposition",
    "escalated", "escalation_timestamp", "investigator_id",
    "root_cause_recorded", "remediation_recorded", "evidence_present", "status"
]

CANONICAL_CASE_FIELDS = [
    "entity_id", "case_id", "alert_id", "created_at", "assigned_at",
    "investigation_started_at", "escalation_status", "escalation_timestamp",
    "closed_at", "disposition", "root_cause", "remediation", "evidence",
    "investigator", "closure_reason"
]

# Common aliases mapping to canonical field names
FIELD_ALIASES: Dict[str, List[str]] = {
    "entity_id": ["entity_id", "entity", "cse_id", "org_id", "tenant", "organization"],
    "alert_id": ["alert_id", "alertid", "event_id", "id", "alert_number"],
    "case_id": ["case_id", "caseid", "ticket_id", "incident_id", "case_number"],
    "alert_timestamp": ["alert_timestamp", "timestamp", "time", "event_time", "created_time", "alert_time", "detected_at"],
    "created_at": ["created_at", "created_date", "creation_time", "open_time", "opened_at"],
    "severity": ["severity", "sev", "priority", "threat_level", "urgency"],
    "category": ["category", "alert_category", "rule_name", "signature", "threat_type", "attack_type", "type"],
    "source_system": ["source_system", "source", "sensor", "tool", "detection_engine", "siem_source"],
    "asset_id": ["asset_id", "asset", "hostname", "host", "device_id", "target_system", "endpoint_id"],
    "acknowledged_timestamp": ["acknowledged_timestamp", "ack_timestamp", "ack_time", "acknowledged_at"],
    "investigation_started_timestamp": ["investigation_started_timestamp", "investigation_start", "triaged_at"],
    "investigation_started_at": ["investigation_started_at", "investigation_started", "investigation_start_time"],
    "closed_timestamp": ["closed_timestamp", "closed_at", "close_time", "resolved_at", "closure_timestamp"],
    "closed_at": ["closed_at", "close_time", "resolved_time", "resolution_timestamp"],
    "disposition": ["disposition", "verdict", "outcome", "classification", "finding"],
    "escalated": ["escalated", "is_escalated", "escalation_flag", "tier2_escalation"],
    "escalation_timestamp": ["escalation_timestamp", "escalated_at", "escalated_time"],
    "escalation_status": ["escalation_status", "escalation_level", "escalation_state"],
    "investigator_id": ["investigator_id", "investigator", "analyst", "analyst_id", "assigned_to", "owner"],
    "investigator": ["investigator", "investigator_name", "analyst", "assigned_analyst"],
    "root_cause_recorded": ["root_cause_recorded", "has_root_cause", "root_cause_documented"],
    "root_cause": ["root_cause", "rootcause", "cause_analysis", "problem_description"],
    "remediation_recorded": ["remediation_recorded", "remediated", "has_remediation"],
    "remediation": ["remediation", "remediation_action", "mitigation_steps", "fix_action"],
    "evidence_present": ["evidence_present", "has_evidence", "evidence_attached", "artifacts_present"],
    "evidence": ["evidence", "evidence_notes", "artifacts", "investigation_notes", "proof"],
    "status": ["status", "alert_status", "state", "lifecycle_state"],
    "closure_reason": ["closure_reason", "resolution_notes", "close_notes", "disposition_reason"]
}


def detect_file_type(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext == ".csv":
        return "CSV"
    elif ext in [".json", ".jsonl"]:
        return "JSON"
    elif ext in [".sqlite", ".db", ".sqlite3"]:
        return "SQLITE"
    return "UNKNOWN"


def inspect_csv_columns_and_sample(file_path: Path) -> Tuple[List[str], List[Dict[str, Any]], int]:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        # Sniff delimiter
        sample_text = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample_text)
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ","

        reader = csv.DictReader(f, delimiter=delimiter)
        columns = [c.strip() for c in (reader.fieldnames or []) if c]
        sample_rows = []
        row_count = 0
        for row in reader:
            row_count += 1
            if len(sample_rows) < 5:
                sample_rows.append({k.strip(): (v.strip() if v else "") for k, v in row.items() if k})
        return columns, sample_rows, row_count


def inspect_json_columns_and_sample(file_path: Path) -> Tuple[List[str], List[Dict[str, Any]], int]:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = json.load(f)
    if isinstance(content, dict):
        if "records" in content and isinstance(content["records"], list):
            rows = content["records"]
        elif "alerts" in content and isinstance(content["alerts"], list):
            rows = content["alerts"]
        elif "cases" in content and isinstance(content["cases"], list):
            rows = content["cases"]
        else:
            rows = [content]
    elif isinstance(content, list):
        rows = content
    else:
        rows = []

    columns = []
    if rows and isinstance(rows[0], dict):
        columns = list(rows[0].keys())

    return columns, rows[:5], len(rows)


def suggest_mapping(columns: List[str], target_category: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    normalized_cols = {c.lower().strip().replace(" ", "_"): c for c in columns}

    target_fields = CANONICAL_ALERT_FIELDS if target_category == "ALERT" else CANONICAL_CASE_FIELDS

    for target in target_fields:
        aliases = FIELD_ALIASES.get(target, [target])
        for alias in aliases:
            if alias in normalized_cols:
                mapping[normalized_cols[alias]] = target
                break

    return mapping


def detect_schema_category(columns: List[str]) -> Tuple[str, float]:
    col_set = {c.lower().strip().replace(" ", "_") for c in columns}
    alert_score = sum(weight for sig, weight in ALERT_SIGNALS.items() if sig in col_set)
    case_score = sum(weight for sig, weight in CASE_SIGNALS.items() if sig in col_set)

    if case_score > alert_score:
        confidence = min(0.99, case_score / (case_score + max(alert_score, 1) + 2))
        return "CASE", confidence
    else:
        confidence = min(0.99, alert_score / (alert_score + max(case_score, 1) + 2))
        return "ALERT", confidence
