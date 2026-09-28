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
        analysis_run = execute_supervisory_analysis_run(
            db=db,
            dataset_version="demo-synthetic-v1.0",
            note="Initial Baseline Supervisory Assessment on Planted Demo Dataset"
        )
        result["initial_analysis_run_id"] = analysis_run.run_id
        result["initial_findings_count"] = analysis_run.findings_count

    return result
