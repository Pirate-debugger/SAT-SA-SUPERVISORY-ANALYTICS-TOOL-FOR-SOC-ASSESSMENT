import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis_run import AnalysisRun
from app.schemas.analysis import AnalysisRunOut, RunAnalysisRequest
from app.analytics.engine import execute_supervisory_analysis_run
from app.analytics.peer_benchmarking import evaluate_peer_benchmarking
from app.analytics.anomaly_engine import detect_operational_anomalies
from app.analytics.temporal_drift import evaluate_temporal_drift
from app.analytics.sample_prioritizer import prioritize_alert_review_samples
from app.analytics.validation_harness import run_expert_validation_benchmark
from app.analytics.report_generator import generate_supervisory_report, generate_markdown_supervisory_report

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/run", response_model=AnalysisRunOut)
def trigger_analysis_run(
    payload: RunAnalysisRequest,
    assessment_period_id: str = Query("2026-Q2"),
    db: Session = Depends(get_db)
):
    run = execute_supervisory_analysis_run(
        db=db,
        entity_ids=payload.entity_ids,
        assessment_period_id=assessment_period_id,
        dataset_version=payload.dataset_version or "v1.0-offline",
        note=payload.note or "Periodic Supervisory Assessment"
    )

    return AnalysisRunOut(
        run_id=run.run_id,
        timestamp=run.timestamp,
        dataset_version=run.dataset_version,
        ruleset_version=run.ruleset_version,
        analytics_version=run.analytics_version,
        status=run.status,
        entities_analyzed_count=run.entities_analyzed_count,
        alerts_analyzed_count=run.alerts_analyzed_count,
        cases_analyzed_count=run.cases_analyzed_count,
        findings_count=run.findings_count,
        summary=json.loads(run.summary_json) if run.summary_json else None,
        execution_time_seconds=run.execution_time_seconds
    )


@router.get("/runs", response_model=List[AnalysisRunOut])
def list_analysis_runs(
    assessment_period_id: Optional[str] = Query(None),
    only_latest: bool = Query(False),
    db: Session = Depends(get_db)
):
    q = db.query(AnalysisRun)
    if assessment_period_id:
        q = q.filter(AnalysisRun.assessment_period_id == assessment_period_id)
    if only_latest:
        q = q.filter(AnalysisRun.is_latest.is_(True))

    runs = q.order_by(AnalysisRun.timestamp.desc()).limit(30).all()
    results = []
    for r in runs:
        results.append(AnalysisRunOut(
            run_id=r.run_id,
            timestamp=r.timestamp,
            dataset_version=r.dataset_version,
            ruleset_version=r.ruleset_version,
            analytics_version=r.analytics_version,
            status=r.status,
            entities_analyzed_count=r.entities_analyzed_count,
            alerts_analyzed_count=r.alerts_analyzed_count,
            cases_analyzed_count=r.cases_analyzed_count,
            findings_count=r.findings_count,
            summary=json.loads(r.summary_json) if r.summary_json else None,
            execution_time_seconds=r.execution_time_seconds
        ))
    return results


@router.get("/runs/{run_id}", response_model=AnalysisRunOut)
def get_analysis_run_detail(run_id: str, db: Session = Depends(get_db)):
    r = db.query(AnalysisRun).filter(AnalysisRun.run_id == run_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return AnalysisRunOut(
        run_id=r.run_id,
        timestamp=r.timestamp,
        dataset_version=r.dataset_version,
        ruleset_version=r.ruleset_version,
        analytics_version=r.analytics_version,
        status=r.status,
        entities_analyzed_count=r.entities_analyzed_count,
        alerts_analyzed_count=r.alerts_analyzed_count,
        cases_analyzed_count=r.cases_analyzed_count,
        findings_count=r.findings_count,
        summary=json.loads(r.summary_json) if r.summary_json else None,
        execution_time_seconds=r.execution_time_seconds
    )


@router.get("/peer-benchmarking")
def get_peer_benchmarking(
    assessment_period_id: str = Query("2026-Q2"),
    db: Session = Depends(get_db)
):
    return evaluate_peer_benchmarking(db, assessment_period_id=assessment_period_id)


@router.get("/anomalies")
def get_operational_anomalies(
    assessment_period_id: str = Query("2026-Q2"),
    db: Session = Depends(get_db)
):
    return detect_operational_anomalies(db, assessment_period_id=assessment_period_id)


@router.get("/temporal-drift")
def get_temporal_drift(
    entity_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return evaluate_temporal_drift(db, entity_id=entity_id)


@router.get("/sample-recommendations")
def get_sample_recommendations(
    entity_id: Optional[str] = Query(None),
    assessment_period_id: Optional[str] = Query("2026-Q2"),
    limit: int = Query(15),
    db: Session = Depends(get_db)
):
    return prioritize_alert_review_samples(
        db,
        entity_id=entity_id,
        assessment_period_id=assessment_period_id,
        limit=limit
    )


@router.get("/validation-benchmark")
def get_validation_benchmark(
    run_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    if not run_id:
        latest = db.query(AnalysisRun).filter(AnalysisRun.is_latest.is_(True)).first()
        if not latest:
            latest = db.query(AnalysisRun).order_by(AnalysisRun.timestamp.desc()).first()
        if not latest:
            raise HTTPException(status_code=404, detail="No completed assessment run to validate against.")
        run_id = latest.run_id

    return run_expert_validation_benchmark(db, run_id=run_id)


@router.get("/report")
def get_supervisory_report(
    run_id: Optional[str] = Query(None),
    assessment_period_id: str = Query("2026-Q2"),
    db: Session = Depends(get_db)
):
    return generate_supervisory_report(db, run_id=run_id, assessment_period_id=assessment_period_id)


@router.get("/report/markdown")
def get_supervisory_report_markdown(
    run_id: Optional[str] = Query(None),
    assessment_period_id: str = Query("2026-Q2"),
    db: Session = Depends(get_db)
):
    report_data = generate_supervisory_report(db, run_id=run_id, assessment_period_id=assessment_period_id)
    md_content = generate_markdown_supervisory_report(report_data)
    return Response(content=md_content, media_type="text/markdown")
