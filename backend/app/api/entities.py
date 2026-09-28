import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.entity import Entity, Asset
from app.models.alert import Alert
from app.models.case import Case
from app.models.finding import Finding
from app.schemas.response import EntitySupervisoryCard
from app.analytics.engine import calculate_entity_supervisory_risk

router = APIRouter(prefix="/entities", tags=["Entities"])


@router.get("", response_model=List[EntitySupervisoryCard])
def list_entities(db: Session = Depends(get_db)):
    entities = db.query(Entity).all()
    results = []

    for ent in entities:
        eid = ent.entity_id
        declared_assets = ent.monitored_asset_count or db.query(Asset).filter(Asset.entity_id == eid).count() or 1

        reporting_assets_cnt = db.query(Alert.asset_id).filter(
            Alert.entity_id == eid,
            Alert.asset_id.isnot(None)
        ).distinct().count()

        coverage_gap = max(0.0, ((declared_assets - reporting_assets_cnt) / declared_assets) * 100.0)

        total_alerts = db.query(Alert).filter(Alert.entity_id == eid).count()
        total_cases = db.query(Case).filter(Case.entity_id == eid).count()

        findings = db.query(Finding).filter(Finding.entity_id == eid).all()
        execution_gaps = sum(1 for f in findings if f.category == "EXECUTION_GAP")
        negative_space = sum(1 for f in findings if f.category == "NEGATIVE_SPACE")
        anomalies = sum(1 for f in findings if f.category == "ANOMALY")

        risk_level, risk_score = calculate_entity_supervisory_risk(findings)

        concerns = []
        for f in findings:
            if f.severity in ["CRITICAL", "HIGH"] and len(concerns) < 3:
                concerns.append(f.finding_type.replace("_", " ").title())
        if not concerns:
            concerns = ["No critical operational weaknesses identified"]

        results.append(EntitySupervisoryCard(
            entity_id=eid,
            name=ent.name,
            sector=ent.sector,
            claimed_tier=ent.claimed_tier,
            monitored_asset_count=declared_assets,
            active_reporting_assets=reporting_assets_cnt,
            coverage_gap_pct=round(coverage_gap, 1),
            total_alerts=total_alerts,
            total_cases=total_cases,
            execution_gaps_count=execution_gaps,
            negative_space_count=negative_space,
            anomalies_count=anomalies,
            risk_level=risk_level,
            risk_score=risk_score,
            primary_concerns=concerns
        ))

    # Sort so highest risk entities appear first
    results.sort(key=lambda x: x.risk_score, reverse=True)
    return results


@router.get("/{entity_id}")
def get_entity_detail(entity_id: str, db: Session = Depends(get_db)):
    ent = db.query(Entity).filter(Entity.entity_id == entity_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")

    assets = db.query(Asset).filter(Asset.entity_id == entity_id).all()
    declared_assets = ent.monitored_asset_count or len(assets) or 1
    reporting_assets_cnt = db.query(Alert.asset_id).filter(
        Alert.entity_id == entity_id,
        Alert.asset_id.isnot(None)
    ).distinct().count()

    coverage_gap = max(0.0, ((declared_assets - reporting_assets_cnt) / declared_assets) * 100.0)

    total_alerts = db.query(Alert).filter(Alert.entity_id == entity_id).count()
    total_cases = db.query(Case).filter(Case.entity_id == entity_id).count()

    # Severity distribution
    sev_dist = db.query(
        Alert.severity, func.count(Alert.id)
    ).filter(Alert.entity_id == entity_id).group_by(Alert.severity).all()

    # Category distribution
    cat_dist = db.query(
        Alert.category, func.count(Alert.id)
    ).filter(Alert.entity_id == entity_id).group_by(Alert.category).all()

    findings = db.query(Finding).filter(Finding.entity_id == entity_id).all()
    risk_level, risk_score = calculate_entity_supervisory_risk(findings)

    return {
        "entity_id": ent.entity_id,
        "name": ent.name,
        "sector": ent.sector,
        "claimed_tier": ent.claimed_tier,
        "soc_model": ent.soc_model,
        "contact_email": ent.contact_email,
        "monitored_asset_count": declared_assets,
        "active_reporting_assets": reporting_assets_cnt,
        "coverage_gap_pct": round(coverage_gap, 1),
        "total_alerts": total_alerts,
        "total_cases": total_cases,
        "risk_level": risk_level,
        "risk_score": risk_score,
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
                "category": f.category,
                "severity": f.severity,
                "confidence": f.confidence,
                "reason": f.reason,
                "evidence_summary": f.evidence_summary,
                "status": f.status
            } for f in findings
        ]
    }
