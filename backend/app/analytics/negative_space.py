import json
import uuid
from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.entity import Entity, Asset
from app.models.alert import Alert
from app.models.case import Case
from app.models.finding import Finding, FindingEvidenceLink


EXPECTED_CORE_CATEGORIES = ["MALWARE", "RANSOMWARE", "UNAUTHORIZED_ACCESS", "DATA_EXFILTRATION"]


def evaluate_negative_space_for_entity(
    db: Session,
    run_id: str,
    entity_id: str,
    assessment_period_id: str = "2026-Q2"
) -> List[Tuple[Finding, List[FindingEvidenceLink]]]:
    findings_with_evidence: List[Tuple[Finding, List[FindingEvidenceLink]]] = []

    entity = db.query(Entity).filter(Entity.entity_id == entity_id).first()
    if not entity:
        return findings_with_evidence

    # 1. Telemetry / Monitored Asset Coverage Gap (Asset Silence)
    declared_assets = db.query(Asset).filter(Asset.entity_id == entity_id).all()
    expected_count = entity.monitored_asset_count or len(declared_assets) or 1

    reporting_assets_query = db.query(Alert.asset_id).filter(
        Alert.entity_id == entity_id,
        Alert.asset_id.isnot(None)
    ).distinct().all()
    reporting_asset_ids = {r[0] for r in reporting_assets_query}
    observed_count = len(reporting_asset_ids)

    if expected_count > 0:
        coverage_gap_pct = max(0.0, ((expected_count - observed_count) / expected_count) * 100.0)
        if coverage_gap_pct >= 25.0:
            silent_assets = [a for a in declared_assets if a.asset_id not in reporting_asset_ids]
            fnd_id = f"FND-NEG-ASSET-{uuid.uuid4().hex[:8].upper()}"

            finding = Finding(
                finding_id=fnd_id,
                run_id=run_id,
                entity_id=entity_id,
                assessment_period_id=assessment_period_id,
                finding_type="CRITICAL_ASSET_TELEMETRY_SILENCE",
                capability_dimension="CYBER_RESILIENCE",
                category="NEGATIVE_SPACE",
                severity="CRITICAL" if coverage_gap_pct > 50 else "HIGH",
                confidence=0.96,
                reason=(
                    f"MONITORING COVERAGE GAP: Entity declared {expected_count} monitored critical assets, "
                    f"but only {observed_count} assets produced any security telemetry during the assessment period. "
                    f"Coverage Gap: {coverage_gap_pct:.1f}% ({expected_count - observed_count} silent critical hosts). "
                    f"POTENTIAL NEGATIVE SPACE indicates unmonitored attack surface rather than absence of threats."
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
                    "coverage_gap_percentage": round(coverage_gap_pct, 1)
                }),
                baseline_json=json.dumps({
                    "expected_telemetry_rate": ">= 85.0%",
                    "acceptable_coverage_gap_max": "15.0%"
                }),
                recommended_review_area="Conduct audit of sensor deployment, syslog forwarders, and network TAP tap-points on silent infrastructure.",
                sample_size=len(silent_assets),
                status="NEW"
            )

            evidence_links = [
                FindingEvidenceLink(
                    finding_id=fnd_id,
                    entity_id=entity_id,
                    record_type="ASSET",
                    record_id=a.asset_id,
                    relevance_note=f"Declared critical {a.asset_type} ({a.hostname}) produced 0 telemetry"
                )
                for a in silent_assets[:20]
            ]
            findings_with_evidence.append((finding, evidence_links))

    # 2. Expected Core Alert Categories Completely Absent
    observed_categories_query = db.query(Alert.category).filter(
        Alert.entity_id == entity_id
    ).distinct().all()
    observed_categories = {c[0] for c in observed_categories_query}

    missing_categories = [cat for cat in EXPECTED_CORE_CATEGORIES if cat not in observed_categories]
    total_alerts = db.query(Alert).filter(Alert.entity_id == entity_id).count()

    if missing_categories and total_alerts >= 50:
        fnd_id = f"FND-NEG-CAT-{uuid.uuid4().hex[:8].upper()}"
        finding = Finding(
            finding_id=fnd_id,
            run_id=run_id,
            entity_id=entity_id,
            assessment_period_id=assessment_period_id,
            finding_type="EXPECTED_ALERT_CATEGORY_ABSENT",
            capability_dimension="THREAT_DETECTION",
            category="NEGATIVE_SPACE",
            severity="HIGH",
            confidence=0.88,
            reason=(
                f"POTENTIAL NEGATIVE SPACE: Core attack categories {missing_categories} were entirely absent from {total_alerts} ingested alerts. "
                f"For a {entity.claimed_tier}, absence of these signatures indicates detection blind spots or disabled rulesets."
            ),
            evidence_summary=(
                f"EXPECTED: Presence of {EXPECTED_CORE_CATEGORIES} signatures | "
                f"OBSERVED: {len(observed_categories)} categories active | "
                f"GAP: 0 records observed for {missing_categories}."
            ),
            observed_value_json=json.dumps({"absent_categories": missing_categories, "active_categories_count": len(observed_categories)}),
            expected_value_json=json.dumps({"mandatory_categories": EXPECTED_CORE_CATEGORIES}),
            metric_values_json=json.dumps({
                "missing_categories": missing_categories,
                "observed_categories_count": len(observed_categories),
                "total_alerts_evaluated": total_alerts
            }),
            baseline_json=json.dumps({
                "expected_categories": EXPECTED_CORE_CATEGORIES,
                "peer_prevalence": "Present in 95%+ of peer entities"
            }),
            recommended_review_area="Verify SIEM detection rule activation status for endpoint ransomware and egress data exfiltration.",
            sample_size=len(missing_categories),
            status="NEW"
        )
        evidence_links = []
        findings_with_evidence.append((finding, evidence_links))

    return findings_with_evidence
