from datetime import datetime
from typing import Optional, Any
from dateutil import parser as date_parser


SEVERITY_MAP = {
    "1": "CRITICAL",
    "sev1": "CRITICAL",
    "sev-1": "CRITICAL",
    "p1": "CRITICAL",
    "crit": "CRITICAL",
    "critical": "CRITICAL",
    "emergency": "CRITICAL",
    "urgent": "CRITICAL",

    "2": "HIGH",
    "sev2": "HIGH",
    "sev-2": "HIGH",
    "p2": "HIGH",
    "high": "HIGH",

    "3": "MEDIUM",
    "sev3": "MEDIUM",
    "sev-3": "MEDIUM",
    "p3": "MEDIUM",
    "med": "MEDIUM",
    "medium": "MEDIUM",

    "4": "LOW",
    "sev4": "LOW",
    "sev-4": "LOW",
    "p4": "LOW",
    "low": "LOW",

    "5": "INFORMATIONAL",
    "sev5": "INFORMATIONAL",
    "sev-5": "INFORMATIONAL",
    "p5": "INFORMATIONAL",
    "info": "INFORMATIONAL",
    "informational": "INFORMATIONAL",
}

STATUS_MAP = {
    "open": "OPEN",
    "new": "OPEN",
    "pending": "OPEN",
    "in_progress": "IN_PROGRESS",
    "in-progress": "IN_PROGRESS",
    "investigating": "IN_PROGRESS",
    "active": "IN_PROGRESS",
    "closed": "CLOSED",
    "resolved": "CLOSED",
    "completed": "CLOSED",
    "dismissed": "CLOSED",
    "escalated": "ESCALATED",
}

DISPOSITION_MAP = {
    "true_positive": "TRUE_POSITIVE",
    "tp": "TRUE_POSITIVE",
    "confirmed": "TRUE_POSITIVE",
    "malicious": "TRUE_POSITIVE",
    "incident": "TRUE_POSITIVE",
    "false_positive": "FALSE_POSITIVE",
    "fp": "FALSE_POSITIVE",
    "benign": "BENIGN",
    "harmless": "BENIGN",
    "expected": "BENIGN",
    "resolved": "RESOLVED",
    "unknown": "UNKNOWN",
    "undetermined": "UNKNOWN",
}


def parse_datetime(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    if not s or s.lower() in ["none", "null", "n/a", "nat", "nan", ""]:
        return None
    # Handle unix epoch integer/float
    if s.isdigit():
        epoch = int(s)
        # If milliseconds epoch
        if epoch > 10_000_000_000:
            return datetime.utcfromtimestamp(epoch / 1000.0)
        return datetime.utcfromtimestamp(epoch)
    try:
        return date_parser.parse(s)
    except Exception:
        return None


def normalize_severity(val: Any) -> str:
    if val is None:
        return "MEDIUM"
    s = str(val).strip().lower()
    return SEVERITY_MAP.get(s, "MEDIUM")


def normalize_status(val: Any) -> str:
    if val is None:
        return "CLOSED"
    s = str(val).strip().lower()
    return STATUS_MAP.get(s, "CLOSED")


def normalize_disposition(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip().lower().replace(" ", "_")
    if not s or s in ["none", "null", "n/a"]:
        return None
    return DISPOSITION_MAP.get(s, s.upper())


def normalize_boolean(val: Any) -> Optional[bool]:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ["true", "yes", "1", "t", "y"]:
        return True
    if s in ["false", "no", "0", "f", "n"]:
        return False
    return None


def normalize_category(val: Any) -> str:
    if val is None:
        return "UNKNOWN_ALERT"
    s = str(val).strip().upper().replace(" ", "_").replace("-", "_")
    return s if s else "UNKNOWN_ALERT"
