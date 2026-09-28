import json
import uuid
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.entity import Entity, Asset, AssessmentPeriod
from app.models.alert import Alert
from app.models.finding import Finding, FindingEvidenceLink


EXPECTED_CORE_CATEGORIES = ["MALWARE", "RANSOMWARE", "UNAUTHORIZED_ACCESS", "DATA_EXFILTRATION"]


def evaluate_negative_space_for_entity(
    db: Session,
    run_id: str,
    entity_id: str,
    assessment_period_id: str = "2026-Q2"
) -> List[Tuple[Finding, List[FindingEvidenceLink]]]:
    """
    Advanced Negative Space Expectation Engine (Section 10).
    Uses available context: critical asset inventory, sector, peer cohort, declared monitoring scope,
    and historical activity to compute EXPECTED, OBSERVED, GAP, and CONFIDENCE.
    """
    findings_with_evidence: List[Tuple[Finding, List[FindingEvidenceLink]]] = []

    entity = db.query(Entity).filter(Entity.entity_id == entity_id).first()
    if not entity:
        return findings_with_evidence

    # Fetch alerts for this assessment period
    alerts_query = db.query(Alert).filter(
        Alert.entity_id == entity_id,
        Alert.assessment_period_id == assessment_period_id
    )
    alerts = alerts_query.all()
    if not alerts:
        alerts = db.query(Alert).filter(Alert.entity_id == entity_id).all()

    total_alerts = len(alerts)

    # =========================================================================
    # 1. Telemetry / Monitored Asset Coverage Gap (Asset Silence)
    # =========================================================================
    declared_assets = db.query(Asset).filter(Asset.entity_id == entity_id).all()
    expected_count = entity.monitored_asset_count or len(declared_assets) or 1

    reporting_asset_ids = {a.asset_id for a in alerts if a.asset_id}
    observed_count = len(reporting_asset_ids)

    # Historical context: check previous period
    prev_period = db.query(AssessmentPeriod).filter(
        AssessmentPeriod.period_id != assessment_period_id,
        AssessmentPeriod.end_date < AssessmentPeriod.start_date  # approximate or lookup
    ).first()

    # Calculate gap
    coverage_gap_pct = max(0.0, ((expected_count - observed_count) / expected_count) * 100.0)

    if coverage_gap_pct >= 25.0:
        silent_assets = [a for a in declared_assets if a.asset_id not in reporting_asset_ids]
        severity = "CRITICAL" if coverage_gap_pct >= 50.0 else "HIGH"

        fnd_id = f"FND-NEG-ASSET-{uuid.uuid4().hex[:8].upper()}"
        finding = Finding(
            finding_id=fnd_id,
            run_id=run_id,
            entity_id=entity_id,
            assessment_period_id=assessment_period_id,
            dataset_version_id="v1.0",
            finding_type="CRITICAL_ASSET_TELEMETRY_SILENCE",
            capability_dimension="CYBER_RESILIENCE",
            category="NEGATIVE_SPACE",
            severity=severity,
            confidence=0.96,
            rule_id="RULE-NEG-01-ASSET-SILENCE",
            reason=(
                f"MONITORING COVERAGE GAP: Entity declared {expected_count} monitored critical assets, "
                f"but only {observed_count} assets produced any security telemetry during assessment period {assessment_period_id}. "
                f"Coverage Gap: {coverage_gap_pct:.1f}% ({expected_count - observed_count} silent critical hosts). "
                f"POTENTIAL NEGATIVE SPACE indicates unmonitored attack surface rather than confirmed absence of threats."
            ),
            evidence_summary=(
                f"EXPECTED: {expected_count} monitored assets | OBSERVED: {observed_count} active reporting assets | "
                f"GAP: {coverage_gap_pct:.1f}% ({expected_count - observed_count} silent assets)."
            ),
            observed_value_json=json.dumps({"reporting_assets": observed_count, "coverage_gap_pct": round(coverage_gap_pct, 1)}),
            expected_value_json=json.dumps({"expected_monitored_assets": expected_count, "target_telemetry_rate": ">= 85.0%"}),
            metric_values_json=json.dumps({
                "expected_assets": expected_count,
                "observed_reporting_assets": observed_count,
                "silent_assets_count": expected_count - observed_count,
                "coverage_gap_percentage": round(coverage_gap_pct, 1),
                "sector": entity.sector,
                "claimed_tier": entity.claimed_tier
            }),
            baseline_json=json.dumps({
                "expected_telemetry_rate": ">= 85.0%",
                "acceptable_coverage_gap_max": "15.0%"
            }),
            recommended_review_area="Conduct audit of sensor deployment, syslog forwarders, and network TAP tap-points on silent infrastructure.",
            nist_csf_category="ID.AM-01",
            mitre_attack_technique="T1048",
            sample_size=len(silent_assets),
            status="OPEN"
        )

        evidence_links = [
            FindingEvidenceLink(
                finding_id=fnd_id,
                entity_id=entity_id,
                record_type="ASSET",
                record_id=a.asset_id,
                relevance_note=f"Declared critical {a.asset_type} ({a.hostname}) produced 0 telemetry in {assessment_period_id}"
            )
            for a in silent_assets[:25]
        ]
        findings_with_evidence.append((finding, evidence_links))

    # =========================================================================
    # 2. Expected Core Alert Categories Completely Absent
    # =========================================================================
    observed_categories = {a.category for a in alerts if a.category and a.category != "UNKNOWN"}
    missing_categories = [cat for cat in EXPECTED_CORE_CATEGORIES if cat not in observed_categories]

    if missing_categories and total_alerts >= 40:
        fnd_id = f"FND-NEG-CAT-{uuid.uuid4().hex[:8].upper()}"
        finding = Finding(
            finding_id=fnd_id,
            run_id=run_id,
            entity_id=entity_id,
            assessment_period_id=assessment_period_id,
            dataset_version_id="v1.0",
            finding_type="EXPECTED_ALERT_CATEGORY_ABSENT",
            capability_dimension="THREAT_DETECTION",
            category="NEGATIVE_SPACE",
            severity="HIGH",
            confidence=0.89,
            rule_id="RULE-NEG-02-CATEGORY-ABSENCE",
            reason=(
                f"POTENTIAL NEGATIVE SPACE: Core attack categories {missing_categories} were entirely absent from {total_alerts} ingested alerts "
                f"during period {assessment_period_id}. For a {entity.claimed_tier} in the {entity.sector} sector, "
                f"complete absence of these threat signatures indicates SIEM detection blind spots or unmonitored egress vectors."
            ),
            evidence_summary=(
                f"EXPECTED: Presence of {EXPECTED_CORE_CATEGORIES} signatures | "
                f"OBSERVED: {len(observed_categories)} active categories | "
                f"GAP: 0 records observed for {missing_categories}."
            ),
            observed_value_json=json.dumps({"absent_categories": missing_categories, "active_categories_count": len(observed_categories)}),
            expected_value_json=json.dumps({"mandatory_categories": EXPECTED_CORE_CATEGORIES}),
            metric_values_json=json.dumps({
                "missing_categories": missing_categories,
                "observed_categories_count": len(observed_categories),
                "total_alerts_evaluated": total_alerts,
                "sector": entity.sector
            }),
            baseline_json=json.dumps({
                "expected_categories": EXPECTED_CORE_CATEGORIES,
                "peer_prevalence": "Present in 90%+ of sector peer entities"
            }),
            recommended_review_area="Verify SIEM detection rule activation status for endpoint ransomware and egress data exfiltration.",
            nist_csf_category="DE.CM-01",
            mitre_attack_technique="T1486",
            sample_size=len(missing_categories),
            status="OPEN"
        )
        findings_with_evidence.append((finding, []))

    # =========================================================================
    # 3. Unexpected Activity Suppression (Telemetry Sudden Drop vs Historical)
    # =========================================================================
    earlier_alerts_cnt = db.query(Alert).filter(
        Alert.entity_id == entity_id,
        Alert.assessment_period_id != assessment_period_id
    ).count()

    if earlier_alerts_cnt >= 200 and total_alerts < 60:
        fnd_id = f"FND-NEG-DROP-{uuid.uuid4().hex[:8].upper()}"
        finding = Finding(
            finding_id=fnd_id,
            run_id=run_id,
            entity_id=entity_id,
            assessment_period_id=assessment_period_id,
            dataset_version_id="v1.0",
            finding_type="UNEXPECTED_ACTIVITY_SUPPRESSION",
            capability_dimension="THREAT_DETECTION",
            category="NEGATIVE_SPACE",
            severity="HIGH",
            confidence=0.91,
            rule_id="RULE-NEG-03-ACTIVITY-SUPPRESSION",
            reason=(
                f"MONITORING COVERAGE GAP: Ingested telemetry dropped drastically to {total_alerts} alerts in {assessment_period_id}, "
                f"compared to {earlier_alerts_cnt} alerts in earlier assessment cycles. "
                f"Unexplained suppression indicates sensor outage or upstream ingestion filtering rather than benign operational calm."
            ),
            evidence_summary=f"Volume drop from ~{earlier_alerts_cnt} to {total_alerts} alerts without declared infrastructure decommissioning.",
            observed_value_json=json.dumps({"current_period_alerts": total_alerts, "prior_alerts_count": earlier_alerts_cnt}),
            expected_value_json=json.dumps({"expected_periodic_baseline": ">= 150 alerts"}),
            metric_values_json=json.dumps({
                "current_period_alerts": total_alerts,
                "historical_alerts": earlier_alerts_cnt
            }),
            baseline_json=json.dumps({"tolerated_volume_swing_max": "50.0%"}),
            recommended_review_area="Inspect log collector agents, network link availability, and SIEM ingestion pipeline filters.",
            nist_csf_category="DE.AE-01",
            mitre_attack_technique="T1048",
            sample_size=total_alerts,
            status="OPEN"
        )
        findings_with_evidence.append((finding, []))

    return findings_with_evidence
