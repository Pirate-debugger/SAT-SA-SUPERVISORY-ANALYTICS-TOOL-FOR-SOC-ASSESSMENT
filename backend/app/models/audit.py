import hashlib
import json
from datetime import timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.database import Base
from app.time_utils import utc_now


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, index=True)
    action = Column(String, nullable=False, index=True)  # INGESTION, ANALYSIS_RUN, REVIEW_ACTION, REPORT_GENERATE, CONFIG_CHANGE
    entity_id = Column(String, nullable=True, index=True)
    actor = Column(String, default="SUPERVISOR")
    details_json = Column(Text, nullable=True)
    previous_event_hash = Column(String, default="GENESIS_HASH", nullable=False)
    event_hash = Column(String, nullable=False, index=True)

    @classmethod
    def calculate_hash(cls, prev_hash: str, timestamp, action: str, actor: str, details_str: str, force_tz: bool = False) -> str:
        if not timestamp:
            ts_str = ""
        else:
            if force_tz and hasattr(timestamp, "replace") and (not hasattr(timestamp, "tzinfo") or timestamp.tzinfo is None):
                ts_str = timestamp.replace(tzinfo=timezone.utc).isoformat()
            else:
                ts_str = timestamp.isoformat()
        payload = f"{prev_hash}|{ts_str}|{action}|{actor}|{details_str or ''}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


    @classmethod
    def create_entry(cls, db, action: str, actor: str = "SUPERVISOR", entity_id: str = None, details: dict = None):
        last_audit = db.query(cls).order_by(cls.id.desc()).first()
        prev_hash = last_audit.event_hash if last_audit else "GENESIS_HASH_SAT_SA_2026"
        ts = utc_now()
        details_str = json.dumps(details, sort_keys=True) if details is not None else ""
        ev_hash = cls.calculate_hash(prev_hash, ts, action, actor, details_str)

        entry = cls(
            timestamp=ts,
            action=action,
            entity_id=entity_id,
            actor=actor,
            details_json=details_str,
            previous_event_hash=prev_hash,
            event_hash=ev_hash
        )
        db.add(entry)
        db.flush()
        return entry


    @classmethod
    def verify_chain(cls, db) -> dict:
        logs = db.query(cls).order_by(cls.id.asc()).all()
        if not logs:
            return {
                "verified": True,
                "total_events": 0,
                "tampered_events": [],
                "root_hash": None,
                "latest_hash": None,
                "status": "EMPTY_CHAIN"
            }

        tampered_ids = []
        for idx, entry in enumerate(logs):
            if idx > 0:
                expected_prev = logs[idx - 1].event_hash
                if entry.previous_event_hash != expected_prev:
                    tampered_ids.append(entry.id)
                    continue

            recalc = cls.calculate_hash(
                entry.previous_event_hash,
                entry.timestamp,
                entry.action,
                entry.actor,
                entry.details_json or ""
            )
            if entry.event_hash != recalc:
                # SQLite can strip tzinfo when loading DateTime; check with UTC tzinfo if needed
                recalc_tz = cls.calculate_hash(
                    entry.previous_event_hash,
                    entry.timestamp,
                    entry.action,
                    entry.actor,
                    entry.details_json or "",
                    force_tz=True
                )
                if entry.event_hash != recalc_tz:
                    tampered_ids.append(entry.id)

        return {
            "verified": len(tampered_ids) == 0,
            "total_events": len(logs),
            "tampered_events": tampered_ids,
            "root_hash": logs[0].event_hash if logs else None,
            "latest_hash": logs[-1].event_hash if logs else None,
            "status": "VALID" if len(tampered_ids) == 0 else "INTEGRITY_COMPROMISED"
        }


class ReviewItem(Base):
    __tablename__ = "review_items"

    review_id = Column(String, primary_key=True, index=True)
    finding_id = Column(String, ForeignKey("findings.finding_id"), nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    assessment_period_id = Column(String, default="2026-Q2", index=True)
    run_id = Column(String, nullable=True, index=True)
    priority = Column(String, default="HIGH")            # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String, default="OPEN")              # OPEN, UNDER_REVIEW, CONFIRMED, REJECTED, DEFERRED, REQUEST_EVIDENCE
    assigned_reviewer = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    actions_history_json = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ExpertReviewLabel(Base):
    """
    Schema for authorized human cybersecurity experts to annotate cases and findings (Section 21).
    """
    __tablename__ = "expert_review_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_type = Column(String, default="FINDING", index=True)  # FINDING, CASE, ALERT
    target_id = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    assessment_period_id = Column(String, default="2026-Q2", index=True)
    expert_label = Column(String, nullable=False)                # TRUE_POSITIVE, FALSE_POSITIVE, BENIGN_ANOMALY, CONFIRMED_GAP, INSUFFICIENT_EVIDENCE
    severity = Column(String, default="HIGH")                    # CRITICAL, HIGH, MEDIUM, LOW
    evidence_notes = Column(Text, nullable=True)
    reviewer_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        Index("ix_expert_label_target", "target_type", "target_id"),
    )
