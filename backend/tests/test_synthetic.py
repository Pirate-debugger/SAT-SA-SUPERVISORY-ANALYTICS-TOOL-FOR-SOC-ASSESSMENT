from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.entity import Entity, Asset
from app.models.alert import Alert
from app.synthetic.generator import generate_dataset_records, save_synthetic_csvs_and_seed_db, ENTITIES_DATA


def test_synthetic_data_structure():
    assets, alerts, cases = generate_dataset_records(target_alert_count=500)

    # 1. Verify 5 CSE entities represented
    alert_entities = {a["entity_id"] for a in alerts}
    assert len(alert_entities) == 5
    for ent in ENTITIES_DATA:
        assert ent["entity_id"] in alert_entities

    # 2. Check disclaimer presence
    assert alerts[0]["_meta_disclaimer"] == "DEMO/SYNTHETIC - NOT REAL GOVERNMENT DATA"

    # 3. Check planted scenarios
    # CSE-BANK-02 rapid closures
    bank_alerts = [a for a in alerts if a["entity_id"] == "CSE-BANK-02" and a["severity"] in ["CRITICAL", "HIGH"]]
    assert len(bank_alerts) > 0

    # CSE-TELECOM-05 negative space in 2026-Q2
    telecom_alerts = [a for a in alerts if a["entity_id"] == "CSE-TELECOM-05" and a.get("assessment_period_id") == "2026-Q2"]
    telecom_categories = {a["category"] for a in telecom_alerts}
    # RANSOMWARE should be absent (Planted Negative Space)
    assert "RANSOMWARE" not in telecom_categories


def test_synthetic_db_seeding():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()

    try:
        result = save_synthetic_csvs_and_seed_db(db, target_alert_count=300)
        assert result["status"] == "SUCCESS"
        assert result["entities_count"] == 5

        # Check DB counts
        db_entities = db.query(Entity).count()
        db_alerts = db.query(Alert).count()
        assert db_entities == 5
        assert db_alerts > 0
    finally:
        db.close()
