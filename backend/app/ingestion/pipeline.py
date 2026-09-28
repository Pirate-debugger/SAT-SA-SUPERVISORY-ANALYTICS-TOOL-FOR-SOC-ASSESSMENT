import csv
import json
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from sqlalchemy.orm import Session

from app.models.entity import Entity, Asset, AssessmentPeriod, DatasetProvenance
from app.models.alert import Alert
from app.models.case import Case
from app.models.ingestion import IngestionBatch
from app.models.audit import AuditLog
from app.schemas.ingestion import IngestionValidationReport
from app.ingestion.detector import (
    detect_file_type, inspect_csv_columns_and_sample,
    inspect_json_columns_and_sample, detect_schema_category,
    suggest_mapping
)
from app.ingestion.mapper import map_row_to_canonical
from app.ingestion.validator import (
    validate_and_normalize_alert, validate_and_normalize_case,
    REQUIRED_ALERT_FIELDS, REQUIRED_CASE_FIELDS
)


CHUNK_SIZE = 500


def calculate_file_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def append_audit_event(
    db: Session,
    action: str,
    actor: str,
    entity_id: Optional[str],
    details: Dict[str, Any]
) -> AuditLog:
    last_audit = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    prev_hash = last_audit.event_hash if last_audit else "GENESIS_HASH_SAT_SA_2026"
    ts = datetime.utcnow()
    details_str = json.dumps(details)
    ev_hash = AuditLog.calculate_hash(prev_hash, ts, action, actor, details_str)

    entry = AuditLog(
        timestamp=ts,
        action=action,
        entity_id=entity_id,
        actor=actor,
        details_json=details_str,
        previous_event_hash=prev_hash,
        event_hash=ev_hash
    )
    db.add(entry)
    return entry


def run_ingestion_pipeline(
    file_path: Path,
    db: Session,
    target_category: Optional[str] = None,
    column_mapping: Optional[Dict[str, str]] = None,
    default_entity_id: Optional[str] = None,
    assessment_period_id: str = "2026-Q2"
) -> IngestionValidationReport:
    batch_id = f"BATCH-{uuid.uuid4().hex[:10].upper()}"
    file_type = detect_file_type(file_path)
    file_hash = calculate_file_sha256(file_path)

    # Ensure period exists
    period = db.query(AssessmentPeriod).filter(AssessmentPeriod.period_id == assessment_period_id).first()
    if not period:
        db.add(AssessmentPeriod(
            period_id=assessment_period_id,
            name=f"Assessment Period {assessment_period_id}",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 6, 30),
            is_active=True
        ))
        db.flush()

    if file_type not in ["CSV", "JSON"]:
        report = IngestionValidationReport(
            batch_id=batch_id,
            filename=file_path.name,
            file_type=file_type,
            status="FAILED",
            message=f"Unsupported file type: {file_type}. Supported formats: CSV, JSON."
        )
        return report

    # 1. Read Raw Records & Columns
    raw_records: List[Dict[str, Any]] = []
    columns: List[str] = []

    try:
        if file_type == "CSV":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                sample_text = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample_text)
                    delimiter = dialect.delimiter
                except Exception:
                    delimiter = ","
                reader = csv.DictReader(f, delimiter=delimiter)
                columns = [c.strip() for c in (reader.fieldnames or []) if c]
                for r in reader:
                    raw_records.append({k.strip(): (v.strip() if v is not None else "") for k, v in r.items() if k})
        elif file_type == "JSON":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = json.load(f)
            if isinstance(content, dict):
                if "records" in content and isinstance(content["records"], list):
                    raw_records = content["records"]
                elif "alerts" in content and isinstance(content["alerts"], list):
                    raw_records = content["alerts"]
                elif "cases" in content and isinstance(content["cases"], list):
                    raw_records = content["cases"]
                else:
                    raw_records = [content]
            elif isinstance(content, list):
                raw_records = content
            if raw_records and isinstance(raw_records[0], dict):
                columns = list(raw_records[0].keys())
    except Exception as e:
        report = IngestionValidationReport(
            batch_id=batch_id,
            filename=file_path.name,
            file_type=file_type,
            status="FAILED",
            message=f"Failed to read/parse input file: {str(e)}"
        )
        return report

    total_records = len(raw_records)
    if total_records == 0:
        report = IngestionValidationReport(
            batch_id=batch_id,
            filename=file_path.name,
            file_type=file_type,
            status="FAILED",
            message="Input file contains no records."
        )
        return report

    # 2. Determine target category (ALERT or CASE)
    if not target_category:
        detected_cat, _ = detect_schema_category(columns)
        target_category = detected_cat

    # 3. Check for missing columns against canonical requirement
    auto_mapping = suggest_mapping(columns, target_category)
    effective_mapping = {**auto_mapping, **(column_mapping or {})}
    mapped_target_fields = set(effective_mapping.values())

    required_fields = REQUIRED_ALERT_FIELDS if target_category == "ALERT" else REQUIRED_CASE_FIELDS
    missing_fields = [rf for rf in required_fields if rf not in mapped_target_fields and rf != "entity_id"]
    if not default_entity_id and "entity_id" not in mapped_target_fields:
        missing_fields.append("entity_id")

    # 4. Fetch existing IDs from DB to prevent collisions
    seen_ids: Set[str] = set()
    if target_category == "ALERT":
        existing_alerts = db.query(Alert.alert_id).all()
        seen_ids = {r[0] for r in existing_alerts}
    else:
        existing_cases = db.query(Case.case_id).all()
        seen_ids = {r[0] for r in existing_cases}

    # 5. Process & Validate Records
    valid_alert_models: List[Alert] = []
    valid_case_models: List[Case] = []
    invalid_samples: List[Dict[str, Any]] = []
    all_warnings: List[str] = []
    valid_count = 0
    invalid_count = 0
    duplicate_count = 0
    unknown_values_count = 0

    known_entities: Set[str] = {e[0] for e in db.query(Entity.entity_id).all()}

    for idx, raw_row in enumerate(raw_records, start=1):
        canonical_dict = map_row_to_canonical(
            raw_row,
            column_mapping=effective_mapping,
            target_category=target_category,
            default_entity_id=default_entity_id
        )

        row_period = raw_row.get("assessment_period_id") or assessment_period_id

        if target_category == "ALERT":
            canonical_obj, error_dict, row_warnings = validate_and_normalize_alert(
                canonical_dict, idx, seen_ids, default_period_id=row_period
            )
            if canonical_obj and (canonical_obj.severity == "UNKNOWN" or canonical_obj.status == "UNKNOWN"):
                unknown_values_count += 1
        else:
            canonical_obj, error_dict, row_warnings = validate_and_normalize_case(
                canonical_dict, idx, seen_ids, default_period_id=row_period
            )
            if canonical_obj and canonical_obj.disposition == "UNKNOWN":
                unknown_values_count += 1

        if row_warnings:
            all_warnings.extend(row_warnings[:2])

        if error_dict:
            invalid_count += 1
            if error_dict.get("error_type") == "DUPLICATE_ID":
                duplicate_count += 1
            if len(invalid_samples) < 25:
                invalid_samples.append(error_dict)
        elif canonical_obj:
            valid_count += 1
            eid = canonical_obj.entity_id
            if eid not in known_entities:
                new_ent = Entity(
                    entity_id=eid,
                    name=f"Entity {eid}",
                    sector="Critical Infrastructure",
                    claimed_tier="Tier-1 Critical Sector Entity"
                )
                db.add(new_ent)
                known_entities.add(eid)

            if target_category == "ALERT":
                alert_db = Alert(
                    entity_id=canonical_obj.entity_id,
                    alert_id=canonical_obj.alert_id,
                    assessment_period_id=canonical_obj.assessment_period_id,
                    alert_timestamp=canonical_obj.alert_timestamp,
                    severity=canonical_obj.severity,
                    category=canonical_obj.category,
                    source_system=canonical_obj.source_system,
                    asset_id=canonical_obj.asset_id,
                    acknowledged_timestamp=canonical_obj.acknowledged_timestamp,
                    investigation_started_timestamp=canonical_obj.investigation_started_timestamp,
                    closed_timestamp=canonical_obj.closed_timestamp,
                    disposition=canonical_obj.disposition,
                    escalated=canonical_obj.escalated,
                    escalation_timestamp=canonical_obj.escalation_timestamp,
                    investigator_id=canonical_obj.investigator_id,
                    root_cause_recorded=canonical_obj.root_cause_recorded,
                    remediation_recorded=canonical_obj.remediation_recorded,
                    evidence_present=canonical_obj.evidence_present,
                    status=canonical_obj.status,
                    ingestion_batch_id=batch_id,
                    provenance_id=file_hash[:16],
                    raw_data_json=json.dumps(canonical_obj.raw_data) if canonical_obj.raw_data else None
                )
                valid_alert_models.append(alert_db)
            else:
                case_db = Case(
                    entity_id=canonical_obj.entity_id,
                    case_id=canonical_obj.case_id,
                    assessment_period_id=canonical_obj.assessment_period_id,
                    alert_id=canonical_obj.alert_id,
                    created_at=canonical_obj.created_at,
                    assigned_at=canonical_obj.assigned_at,
                    investigation_started_at=canonical_obj.investigation_started_at,
                    escalation_status=canonical_obj.escalation_status,
                    escalation_timestamp=canonical_obj.escalation_timestamp,
                    closed_at=canonical_obj.closed_at,
                    disposition=canonical_obj.disposition,
                    root_cause=canonical_obj.root_cause,
                    remediation=canonical_obj.remediation,
                    evidence=canonical_obj.evidence,
                    investigator=canonical_obj.investigator,
                    closure_reason=canonical_obj.closure_reason,
                    ingestion_batch_id=batch_id,
                    provenance_id=file_hash[:16]
                )
                valid_case_models.append(case_db)

    # 6. Bulk Insert Valid Records in chunks
    if valid_alert_models:
        for i in range(0, len(valid_alert_models), CHUNK_SIZE):
            db.bulk_save_objects(valid_alert_models[i:i + CHUNK_SIZE])
    if valid_case_models:
        for i in range(0, len(valid_case_models), CHUNK_SIZE):
            db.bulk_save_objects(valid_case_models[i:i + CHUNK_SIZE])

    # 7. Compute Data Quality Percentage
    penalty = (invalid_count * 1.0) + (unknown_values_count * 0.5)
    data_quality_pct = max(0.0, round(((total_records - penalty) / max(total_records, 1)) * 100.0, 1))

    # 8. Record Dataset Provenance
    prov = DatasetProvenance(
        provenance_id=file_hash[:16],
        filename=file_path.name,
        file_hash=file_hash,
        source_name=default_entity_id or "Multi-Entity-Submission",
        assessment_period_id=assessment_period_id,
        record_count=valid_count,
        data_quality_pct=data_quality_pct,
        unknown_fields_summary_json=json.dumps({"unknown_values": unknown_values_count, "missing_fields": missing_fields})
    )
    db.add(prov)

    # 9. Record Ingestion Batch
    status = "SUCCESS" if invalid_count == 0 else ("PARTIAL_SUCCESS" if valid_count > 0 else "FAILED")
    msg = (
        f"Processed {total_records} records: {valid_count} valid, {invalid_count} rejected ({duplicate_count} duplicates). "
        f"Data Quality: {data_quality_pct}% ({unknown_values_count} unknown values)."
    )

    batch_record = IngestionBatch(
        batch_id=batch_id,
        filename=file_path.name,
        file_type=file_type,
        file_hash=file_hash,
        entity_id=default_entity_id,
        assessment_period_id=assessment_period_id,
        status=status,
        total_records=total_records,
        valid_records=valid_count,
        invalid_records=invalid_count,
        duplicate_records=duplicate_count,
        data_quality_pct=data_quality_pct,
        unknown_values_count=unknown_values_count,
        missing_fields_json=json.dumps(missing_fields),
        normalization_warnings_json=json.dumps(all_warnings[:50]),
        invalid_records_sample_json=json.dumps(invalid_samples)
    )
    db.add(batch_record)

    # 10. Audit Log with cryptographic hash chaining
    append_audit_event(
        db=db,
        action="DATA_INGESTION",
        actor="SUPERVISOR",
        entity_id=default_entity_id,
        details={
            "batch_id": batch_id,
            "filename": file_path.name,
            "file_hash": file_hash,
            "status": status,
            "valid_records": valid_count,
            "invalid_records": invalid_count,
            "data_quality_pct": data_quality_pct
        }
    )

    db.commit()

    return IngestionValidationReport(
        batch_id=batch_id,
        filename=file_path.name,
        file_type=file_type,
        total_records=total_records,
        valid_records=valid_count,
        invalid_records=invalid_count,
        duplicate_records=duplicate_count,
        missing_fields=missing_fields,
        normalization_warnings=all_warnings[:50],
        invalid_samples=invalid_samples,
        status=status,
        message=msg
    )
