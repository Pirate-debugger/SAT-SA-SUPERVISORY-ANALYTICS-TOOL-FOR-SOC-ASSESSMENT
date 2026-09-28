from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import APP_NAME, APP_VERSION, RULESET_VERSION
from app.models.entity import Entity
from app.models.alert import Alert
from app.models.case import Case
from app.models.finding import Finding
from app.models.analysis_run import AnalysisRun
from app.schemas.response import DashboardSummary
from app.analytics.engine import calculate_entity_supervisory_risk

from app.api.entities import router as entities_router
from app.api.ingestion import router as ingestion_router
from app.api.analysis import router as analysis_router
from app.api.findings import router as findings_router
from app.api.reviews import router as reviews_router
from app.api.synthetic import router as synthetic_router

api_router = APIRouter()

api_router.include_router(entities_router)
api_router.include_router(ingestion_router)
api_router.include_router(analysis_router)
api_router.include_router(findings_router)
api_router.include_router(reviews_router)
api_router.include_router(synthetic_router)


@api_router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    entities_cnt = db.query(Entity).count()
    alerts_cnt = db.query(Alert).count()
    cases_cnt = db.query(Case).count()
    findings_cnt = db.query(Finding).count()
    runs_cnt = db.query(AnalysisRun).count()

    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "ruleset_version": RULESET_VERSION,
        "mode": "AIR_GAPPED_OFFLINE_LOCAL",
        "external_ai_apis_connected": False,
        "cloud_services_connected": False,
        "database_connected": True,
        "counts": {
            "entities": entities_cnt,
            "alerts": alerts_cnt,
            "cases": cases_cnt,
            "findings": findings_cnt,
            "analysis_runs": runs_cnt
        }
    }


@api_router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    entities = db.query(Entity).all()
    total_entities = len(entities)

    findings = db.query(Finding).all()
    high_risk_findings = sum(1 for f in findings if f.severity in ["CRITICAL", "HIGH"])
    execution_gaps = sum(1 for f in findings if f.category == "EXECUTION_GAP")
    negative_space = sum(1 for f in findings if f.category == "NEGATIVE_SPACE")
    anomalies = sum(1 for f in findings if f.category == "ANOMALY")

    total_alerts = db.query(Alert).count()
    total_cases = db.query(Case).count()

    # Determine entities requiring attention (risk >= HIGH or score >= 40)
    entities_requiring_attention = 0
    for ent in entities:
        ent_findings = [f for f in findings if f.entity_id == ent.entity_id]
        level, score = calculate_entity_supervisory_risk(ent_findings)
        if level in ["CRITICAL", "HIGH"]:
            entities_requiring_attention += 1

    latest_run = db.query(AnalysisRun).order_by(AnalysisRun.timestamp.desc()).first()

    return DashboardSummary(
        total_entities=total_entities,
        entities_requiring_attention=entities_requiring_attention,
        high_risk_findings=high_risk_findings,
        execution_gaps_count=execution_gaps,
        negative_space_count=negative_space,
        anomalies_count=anomalies,
        total_alerts_ingested=total_alerts,
        total_cases_ingested=total_cases,
        latest_run_id=latest_run.run_id if latest_run else None,
        latest_run_timestamp=latest_run.timestamp if latest_run else None
    )
