from datetime import datetime
from app.ingestion.normalizer import (
    parse_datetime, normalize_severity, normalize_status,
    normalize_boolean, normalize_category
)
from app.ingestion.validator import validate_and_normalize_alert, validate_and_normalize_case


def test_normalizer_date_parsing():
    dt1 = parse_datetime("2026-02-14T15:30:00")
    assert dt1 == datetime(2026, 2, 14, 15, 30, 0)

    dt2 = parse_datetime("2026-03-01 10:20:30")
    assert dt2 == datetime(2026, 3, 1, 10, 20, 30)

    dt3 = parse_datetime("invalid-date-string")
    assert dt3 is None

    dt4 = parse_datetime(None)
    assert dt4 is None


def test_normalizer_severity_mapping():
    assert normalize_severity("crit") == "CRITICAL"
    assert normalize_severity("1") == "CRITICAL"
    assert normalize_severity("sev1") == "CRITICAL"
    assert normalize_severity("high") == "HIGH"
    assert normalize_severity("p2") == "HIGH"
    assert normalize_severity("unknown-sev") == "UNKNOWN"


def test_normalizer_booleans():
    assert normalize_boolean("true") is True
    assert normalize_boolean("1") is True
    assert normalize_boolean("yes") is True
    assert normalize_boolean("false") is False
    assert normalize_boolean("0") is False
    assert normalize_boolean("no") is False
    assert normalize_boolean(None) is None


def test_alert_validator_duplicate_detection():
    seen_ids = set()
    raw_row_1 = {
        "entity_id": "CSE-POWER-01",
        "alert_id": "ALT-DUP-01",
        "alert_timestamp": "2026-01-10T12:00:00",
        "severity": "CRITICAL",
        "category": "SCADA_ANOMALY"
    }

    alert_obj_1, err_1, warn_1 = validate_and_normalize_alert(raw_row_1, 1, seen_ids)
    assert alert_obj_1 is not None
    assert err_1 is None

    # Ingesting the same ID must trigger DUPLICATE_ID error
    alert_obj_2, err_2, warn_2 = validate_and_normalize_alert(raw_row_1, 2, seen_ids)
    assert alert_obj_2 is None
    assert err_2 is not None
    assert err_2["error_type"] == "DUPLICATE_ID"
    assert err_2["value"] == "ALT-DUP-01"


def test_alert_validator_missing_required_field():
    seen_ids = set()
    raw_row = {
        "alert_id": "ALT-MISSING-01",
        "alert_timestamp": "2026-01-10T12:00:00",
        "severity": "LOW",
        "category": "BRUTE_FORCE"
        # entity_id is missing!
    }
    alert_obj, err, warn = validate_and_normalize_alert(raw_row, 1, seen_ids)
    assert alert_obj is None
    assert err["error_type"] == "MISSING_REQUIRED_FIELD"
    assert err["field"] == "entity_id"
