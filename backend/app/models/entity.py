from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Entity(Base):
    __tablename__ = "entities"

    entity_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    sector = Column(String, nullable=False)
    claimed_tier = Column(String, default="Tier-1 Critical Sector Entity")
    monitored_asset_count = Column(Integer, default=0)
    soc_model = Column(String, default="In-house 24/7 SOC")
    contact_email = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assets = relationship("Asset", back_populates="entity", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="entity", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="entity", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    asset_id = Column(String, primary_key=True, index=True)
    entity_id = Column(String, ForeignKey("entities.entity_id"), nullable=False, index=True)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    criticality = Column(String, default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    asset_type = Column(String, nullable=False)   # SCADA, CORE_ROUTER, PAYMENT_GW, etc.
    expected_monitoring = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("Entity", back_populates="assets")
