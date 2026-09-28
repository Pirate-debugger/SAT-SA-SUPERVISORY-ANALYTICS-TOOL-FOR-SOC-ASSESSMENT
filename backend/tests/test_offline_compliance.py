import pytest
import socket
from app.api.router import get_system_status
from app.analytics.engine import get_authoritative_entity_metrics
from app.analytics.report_generator import generate_supervisory_report
from app.database import Base, engine, SessionLocal


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_air_gapped_offline_compliance(db_session, monkeypatch):
    """
    Section 25 Verification:
    Ensures that the entire analytical pipeline, report generation, and system status
    execute 100% locally with all socket network connections blocked.
    """
    # Monkeypatch socket.connect to ensure no external internet calls are made
    def blocked_connect(*args, **kwargs):
        raise ConnectionRefusedError("Air-gapped offline environment: outbound network call blocked!")

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)

    # 1. System status check
    status = get_system_status(db_session)
    assert status["mode"] == "AIR_GAPPED_OFFLINE_LOCAL"
    assert status["external_ai_apis_connected"] is False
    assert status["cloud_services_connected"] is False
    assert status["database_connected"] is True

    # 2. Authoritative analytics calculation offline
    from app.models.entity import Entity
    ent = db_session.query(Entity).first()
    if not ent:
        ent = Entity(entity_id="CSE-FIN-01", name="Test Bank", sector="FINANCIAL", claimed_tier="TIER_1")
        db_session.add(ent)
        db_session.commit()
    metrics = get_authoritative_entity_metrics(db_session, entity_id=ent.entity_id)
    assert "supervisory_attention_indicator" in metrics
    assert "capability_profile" in metrics

    # 3. Report generation offline
    report = generate_supervisory_report(db_session, assessment_period_id="2026-Q2")
    assert report["report_metadata"]["mode"] == "AIR_GAPPED_OFFLINE_LOCAL"
    assert "DEMO / SYNTHETIC DATA" in report["report_metadata"]["classification_banner"]
