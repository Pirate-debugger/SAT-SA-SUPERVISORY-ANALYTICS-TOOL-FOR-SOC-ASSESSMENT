from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import APP_NAME, APP_VERSION, RULESET_VERSION
from app.models.entity import Entity, AssessmentPeriod, DatasetProvenance
from app.models.alert import Alert
from app.models.case import Case
from app.models.finding import Finding
from app.models.analysis_run import AnalysisRun
from app.schemas.response import DashboardSummary
from app.analytics.engine import calculate_entity_supervisory_risk, get_authoritative_entity_metrics

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


@api_router.get("/periods")
def get_assessment_periods(db: Session = Depends(get_db)):
    """Returns all assessment periods with alert, case, and run counts."""
    periods = db.query(AssessmentPeriod).order_by(AssessmentPeriod.start_date.desc()).all()
    results = []
    
    if not periods:
        # Fallback to standard periods if none seeded in DB table
        period_ids = ["2026-Q2", "2026-Q1", "2025-Q4"]
    else:
        period_ids = [p.period_id for p in periods]

    for pid in period_ids:
        p_obj = next((p for p in periods if p.period_id == pid), None)
        alert_cnt = db.query(Alert).filter(Alert.assessment_period_id == pid).count()
        case_cnt = db.query(Case).filter(Case.assessment_period_id == pid).count()
        run = db.query(AnalysisRun).filter(
            AnalysisRun.assessment_period_id == pid,
            AnalysisRun.is_latest.is_(True)
        ).first()

        results.append({
            "period_id": pid,
            "name": p_obj.name if p_obj else f"Assessment Period {pid}",
            "is_active": p_obj.is_active if p_obj else (pid == "2026-Q2"),
            "alert_count": alert_cnt,
            "case_count": case_cnt,
            "latest_run_id": run.run_id if run else None,
            "latest_run_timestamp": run.timestamp if run else None
        })
    return results


@api_router.get("/provenances")
def get_dataset_provenances(db: Session = Depends(get_db)):
    """Returns dataset provenance records with SHA-256 hashes and data quality percentage."""
    provenances = db.query(DatasetProvenance).order_by(DatasetProvenance.import_timestamp.desc()).all()
    return [
        {
            "provenance_id": p.provenance_id,
            "filename": p.filename,
            "file_hash": p.file_hash,
            "source_name": p.source_name,
            "assessment_period_id": p.assessment_period_id,
            "record_count": p.record_count,
            "data_quality_pct": p.data_quality_pct,
            "import_timestamp": p.import_timestamp
        }
        for p in provenances
    ]


@api_router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    assessment_period_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    entities = db.query(Entity).all()
    total_entities = len(entities)

    # Isolated Run Selection: ALWAYS isolate to the latest completed run
    run_q = db.query(AnalysisRun).filter(AnalysisRun.is_latest.is_(True))
    if assessment_period_id:
        run_q = run_q.filter(AnalysisRun.assessment_period_id == assessment_period_id)
    latest_run = run_q.order_by(AnalysisRun.timestamp.desc()).first()

    if not latest_run:
        # Fallback to absolute latest run
        latest_run = db.query(AnalysisRun).order_by(AnalysisRun.timestamp.desc()).first()

    if latest_run:
        findings = db.query(Finding).filter(Finding.run_id == latest_run.run_id).all()
    else:
        findings = []

    high_risk_findings = sum(1 for f in findings if f.severity in ["CRITICAL", "HIGH"])
    execution_gaps = sum(1 for f in findings if f.category == "EXECUTION_GAP")
    negative_space = sum(1 for f in findings if f.category == "NEGATIVE_SPACE")
    anomalies = sum(1 for f in findings if f.category == "ANOMALY")

    # Ingested counts
    alert_q = db.query(Alert)
    case_q = db.query(Case)
    if assessment_period_id:
        alert_q = alert_q.filter(Alert.assessment_period_id == assessment_period_id)
        case_q = case_q.filter(Case.assessment_period_id == assessment_period_id)
    total_alerts = alert_q.count()
    total_cases = case_q.count()

    # Authoritative determination of entities requiring attention (Section 5)
    entities_requiring_attention = 0
    eff_period = assessment_period_id or (latest_run.assessment_period_id if latest_run else "2026-Q2")
    for ent in entities:
        m = get_authoritative_entity_metrics(
            db,
            ent.entity_id,
            run_id=latest_run.run_id if latest_run else None,
            assessment_period_id=eff_period
        )
        if m.get("supervisory_attention_level") in ["CRITICAL", "HIGH"]:
            entities_requiring_attention += 1

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
