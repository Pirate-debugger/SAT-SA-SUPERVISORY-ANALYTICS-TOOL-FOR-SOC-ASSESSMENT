import csv
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.alert import Alert
from app.models.entity import Entity
from app.ingestion.pipeline import run_ingestion_pipeline


def test_pipeline_with_valid_and_invalid_csv():
    # Set up in-memory sqlite test database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()

    # Pre-populate entity
    ent = Entity(entity_id="CSE-TEST-01", name="Test Entity", sector="Test Sector")
    db.add(ent)
    db.commit()

    # Create temporary CSV file with 3 rows:
    # 1 valid row, 1 row with bad timestamp, 1 duplicate row
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "entity_id", "alert_id", "alert_timestamp", "severity", "category"
        ])
        writer.writeheader()
        writer.writerow({
            "entity_id": "CSE-TEST-01",
            "alert_id": "ALT-T001",
            "alert_timestamp": "2026-03-01T10:00:00",
            "severity": "CRITICAL",
            "category": "RANSOMWARE"
        })
        writer.writerow({
            "entity_id": "CSE-TEST-01",
            "alert_id": "ALT-T002",
            "alert_timestamp": "NOT_A_VALID_DATE",
            "severity": "HIGH",
            "category": "MALWARE"
        })
        writer.writerow({
            "entity_id": "CSE-TEST-01",
            "alert_id": "ALT-T001",  # Duplicate of first row!
            "alert_timestamp": "2026-03-01T10:05:00",
            "severity": "CRITICAL",
            "category": "RANSOMWARE"
        })
        temp_csv_path = Path(f.name)

    try:
        report = run_ingestion_pipeline(
            file_path=temp_csv_path,
            db=db,
            target_category="ALERT"
        )

        assert report.total_records == 3
        assert report.valid_records == 1
        assert report.invalid_records == 2
        assert report.duplicate_records == 1
        assert report.status == "PARTIAL_SUCCESS"
        assert len(report.invalid_samples) == 2

        # Check DB has only the 1 valid record
        saved_alerts = db.query(Alert).filter(Alert.entity_id == "CSE-TEST-01").all()
        assert len(saved_alerts) == 1
        assert saved_alerts[0].alert_id == "ALT-T001"
    finally:
        if temp_csv_path.exists():
            temp_csv_path.unlink()
        db.close()
