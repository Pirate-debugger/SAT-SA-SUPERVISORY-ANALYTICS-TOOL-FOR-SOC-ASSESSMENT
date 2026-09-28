from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.synthetic.generator import save_synthetic_csvs_and_seed_db
from app.analytics.engine import execute_supervisory_analysis_run

router = APIRouter(prefix="/synthetic", tags=["Synthetic Data"])


@router.post("/generate")
def generate_and_seed_demo_data(target_alerts: int = 3200, run_initial_analysis: bool = True, db: Session = Depends(get_db)):
    result = save_synthetic_csvs_and_seed_db(db, target_alert_count=target_alerts)

    if run_initial_analysis:
        run_ids = []
        for pid in ["2025-Q4", "2026-Q1", "2026-Q2"]:
            analysis_run = execute_supervisory_analysis_run(
                db=db,
                assessment_period_id=pid,
                dataset_version=f"demo-synthetic-{pid}",
                note=f"Baseline Supervisory Assessment for {pid}"
            )
            run_ids.append(analysis_run.run_id)
        result["initial_analysis_run_ids"] = run_ids
        result["latest_run_id"] = run_ids[-1]

    return result
