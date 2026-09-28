import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.entity import Entity, Asset
from app.models.alert import Alert
from app.models.case import Case
from app.models.finding import Finding
from app.models.analysis_run import AnalysisRun, CapabilityScore
from app.schemas.response import EntitySupervisoryCard
from app.analytics.engine import get_authoritative_entity_metrics

router = APIRouter(prefix="/entities", tags=["Entities"])


@router.get("", response_model=List[EntitySupervisoryCard])
def list_entities(
    period_id: Optional[str] = Query("2026-Q2"),
    db: Session = Depends(get_db)
):
    """Returns authoritative supervisory entity cards sorted by attention score (Section 5)."""
    entities = db.query(Entity).all()
    results = []

    # Get latest completed run for period
    latest_run = db.query(AnalysisRun).filter(
        AnalysisRun.assessment_period_id == period_id,
        AnalysisRun.is_latest.is_(True),
        AnalysisRun.status == "COMPLETED"
    ).first()
    if not latest_run:
        latest_run = db.query(AnalysisRun).filter(AnalysisRun.status == "COMPLETED").order_by(AnalysisRun.timestamp.desc()).first()

    run_id = latest_run.run_id if latest_run else None

    for ent in entities:
        m = get_authoritative_entity_metrics(
            db=db,
            entity_id=ent.entity_id,
            run_id=run_id,
            assessment_period_id=period_id or "2026-Q2"
        )
        if not m:
            continue

        results.append(EntitySupervisoryCard(
            entity_id=m["entity_id"],
            name=m["name"],
            sector=m["sector"],
            claimed_tier=m["claimed_tier"],
            monitored_asset_count=m["monitored_asset_count"],
            active_reporting_assets=m["active_reporting_assets"],
            coverage_gap_pct=m["coverage_gap_pct"],
            total_alerts=m["total_alerts"],
            total_cases=m["total_cases"],
            execution_gaps_count=m["execution_gaps_count"],
            negative_space_count=m["negative_space_count"],
            anomalies_count=m["anomalies_count"],
            risk_level=m["supervisory_attention_level"],
            risk_score=m["supervisory_attention_score"],
            primary_concerns=m["primary_concerns"]
        ))

    # Sort so highest attention entities appear first
    results.sort(key=lambda x: x.risk_score, reverse=True)
    return results


@router.get("/{entity_id}")
def get_entity_detail(
    entity_id: str,
    period_id: Optional[str] = Query("2026-Q2"),
    db: Session = Depends(get_db)
):
    """Returns authoritative detailed supervisory profile for a CSE (Section 18)."""
    ent = db.query(Entity).filter(Entity.entity_id == entity_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")

    # Get latest completed run for this period
    latest_run = db.query(AnalysisRun).filter(
        AnalysisRun.assessment_period_id == period_id,
        AnalysisRun.is_latest.is_(True),
        AnalysisRun.status == "COMPLETED"
    ).first()
    if not latest_run:
        latest_run = db.query(AnalysisRun).filter(AnalysisRun.status == "COMPLETED").order_by(AnalysisRun.timestamp.desc()).first()

    run_id = latest_run.run_id if latest_run else None

    auth_metrics = get_authoritative_entity_metrics(
        db=db,
        entity_id=entity_id,
        run_id=run_id,
        assessment_period_id=period_id or "2026-Q2"
    )

    assets = db.query(Asset).filter(Asset.entity_id == entity_id).all()

    # Severity distribution
    sev_dist = db.query(
        Alert.severity, func.count(Alert.id)
    ).filter(
        Alert.entity_id == entity_id,
        Alert.assessment_period_id == period_id
    ).group_by(Alert.severity).all()

    # Category distribution
    cat_dist = db.query(
        Alert.category, func.count(Alert.id)
    ).filter(
        Alert.entity_id == entity_id,
        Alert.assessment_period_id == period_id
    ).group_by(Alert.category).all()

    # Fetch run-isolated findings and capability scores
    findings = db.query(Finding).filter(
        Finding.entity_id == entity_id,
        Finding.run_id == run_id
    ).all() if run_id else []

    cap_scores = db.query(CapabilityScore).filter(
        CapabilityScore.entity_id == entity_id,
        CapabilityScore.run_id == run_id
    ).all() if run_id else []

    return {
        "entity_id": ent.entity_id,
        "name": ent.name,
        "sector": ent.sector,
        "claimed_tier": ent.claimed_tier,
        "soc_model": ent.soc_model,
        "contact_email": ent.contact_email,
        "assessment_period_id": period_id,
        "active_run_id": run_id,
        "monitored_asset_count": auth_metrics.get("monitored_asset_count", 0),
        "active_reporting_assets": auth_metrics.get("active_reporting_assets", 0),
        "coverage_gap_pct": auth_metrics.get("coverage_gap_pct", 0.0),
        "total_alerts": auth_metrics.get("total_alerts", 0),
        "total_cases": auth_metrics.get("total_cases", 0),
        "supervisory_attention_level": auth_metrics.get("supervisory_attention_level", "LOW"),
        "supervisory_attention_score": auth_metrics.get("supervisory_attention_score", 0.0),
        "attention_breakdown": auth_metrics.get("score_breakdown", {}),
        "capability_dimensions": [
            {
                "dimension": cs.dimension,
                "score": cs.score,
                "status": cs.status,
                "peer_median": cs.peer_median,
                "deviation": cs.deviation,
                "confidence": cs.confidence,
                "trend": cs.trend,
                "observed_metrics": json.loads(cs.observed_metrics_json) if cs.observed_metrics_json else None,
                "baseline": json.loads(cs.baseline_json) if cs.baseline_json else None
            } for cs in cap_scores
        ],
        "severity_distribution": {k: v for k, v in sev_dist},
        "category_distribution": {k: v for k, v in cat_dist},
        "assets_sample": [
            {
                "asset_id": a.asset_id,
                "hostname": a.hostname,
                "ip_address": a.ip_address,
                "criticality": a.criticality,
                "asset_type": a.asset_type
            } for a in assets[:30]
        ],
        "findings": [
            {
                "finding_id": f.finding_id,
                "finding_type": f.finding_type,
                "capability_dimension": f.capability_dimension,
                "category": f.category,
                "severity": f.severity,
                "confidence": f.confidence,
                "rule_id": f.rule_id,
                "reason": f.reason,
                "evidence_summary": f.evidence_summary,
                "observed": json.loads(f.observed_value_json) if f.observed_value_json else None,
                "expected": json.loads(f.expected_value_json) if f.expected_value_json else None,
                "recommended_review_area": f.recommended_review_area,
                "status": f.status,
                "evidence_count": len(f.evidence_links)
            } for f in findings
        ]
    }
