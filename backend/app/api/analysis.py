import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis_run import AnalysisRun
from app.schemas.analysis import AnalysisRunOut, RunAnalysisRequest
from app.analytics.engine import execute_supervisory_analysis_run

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/run", response_model=AnalysisRunOut)
def trigger_analysis_run(payload: RunAnalysisRequest, db: Session = Depends(get_db)):
    run = execute_supervisory_analysis_run(
        db=db,
        entity_ids=payload.entity_ids,
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
def list_analysis_runs(db: Session = Depends(get_db)):
    runs = db.query(AnalysisRun).order_by(AnalysisRun.timestamp.desc()).limit(30).all()
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
