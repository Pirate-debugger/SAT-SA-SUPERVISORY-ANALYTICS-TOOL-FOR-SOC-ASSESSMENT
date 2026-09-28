import os
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.config import SYNTHETIC_DIR
from app.models.entity import Entity, Asset, AssessmentPeriod
from app.models.alert import Alert
from app.models.case import Case

random.seed(42)

DISCLAIMER = "DEMO/SYNTHETIC - NOT REAL GOVERNMENT DATA"

PERIODS = [
    {"period_id": "2025-Q4", "name": "Q4 2025 Periodic Assessment", "start": datetime(2025, 10, 1), "end": datetime(2025, 12, 31)},
    {"period_id": "2026-Q1", "name": "Q1 2026 Periodic Assessment", "start": datetime(2026, 1, 1), "end": datetime(2026, 3, 31)},
    {"period_id": "2026-Q2", "name": "Q2 2026 Periodic Assessment", "start": datetime(2026, 4, 1), "end": datetime(2026, 6, 30)},
]

ENTITIES_DATA = [
    {
        "entity_id": "CSE-POWER-01",
        "name": "National Power Dispatch Grid Authority",
        "sector": "Energy & Power",
        "claimed_tier": "Tier-1 Critical Sector Entity",
        "monitored_asset_count": 85,
        "soc_model": "In-house 24/7 Hybrid SOC",
        "contact_email": "soc-supervision@grid-energy.demo.gov"
    },
    {
        "entity_id": "CSE-BANK-02",
        "name": "Apex Interbank Settlement & Clearing System",
        "sector": "Financial Services",
        "claimed_tier": "Tier-1 Critical Sector Entity",
        "monitored_asset_count": 120,
        "soc_model": "Outsourced 24/7 Managed SOC",
        "contact_email": "sec-ops@apexbank.demo.fin"
    },
    {
        "entity_id": "CSE-HEALTH-03",
        "name": "National Hospital & Healthcare Information Network",
        "sector": "Healthcare",
        "claimed_tier": "Tier-2 Critical Sector Entity",
        "monitored_asset_count": 65,
        "soc_model": "Internal Dedicated SOC",
        "contact_email": "cyber-safety@healthnet.demo.gov"
    },
    {
        "entity_id": "CSE-TRANS-04",
        "name": "Central Railway Operations & Signaling Network",
        "sector": "Transportation",
        "claimed_tier": "Tier-1 Critical Sector Entity",
        "monitored_asset_count": 95,
        "soc_model": "24/7 Integrated Transit SOC",
        "contact_email": "soc-lead@trans-rail.demo.gov"
    },
    {
        "entity_id": "CSE-TELECOM-05",
        "name": "State Telecommunication Backbone & Fiber Infrastructure",
        "sector": "Telecommunications",
        "claimed_tier": "Tier-1 Critical Sector Entity",
        "monitored_asset_count": 140,
        "soc_model": "Shared Regional SOC",
        "contact_email": "telecom-ops@statecom.demo.net"
    }
]

ALERT_CATEGORIES = [
    "UNAUTHORIZED_ACCESS", "BRUTE_FORCE", "MALWARE", "RANSOMWARE",
    "DATA_EXFILTRATION", "PRIVILEGE_ESCALATION", "DDOS_ATTACK",
    "POLICY_VIOLATION", "SCADA_COMMAND_ANOMALY"
]

INVESTIGATORS = ["ANALYST_SHARMA", "ANALYST_VERMA", "ANALYST_RAO", "ANALYST_SINGH", "ANALYST_PATEL"]


def generate_synthetic_assets(entity_id: str, count: int, prefix: str) -> List[Dict[str, Any]]:
    assets = []
    types = ["DATABASE_SERVER", "CORE_ROUTER", "SCADA_CONTROLLER", "APPLICATION_GATEWAY", "ACTIVE_DIRECTORY_DC", "FIREWALL"]
    for i in range(1, count + 1):
        assets.append({
            "asset_id": f"AST-{prefix}-{i:03d}",
            "entity_id": entity_id,
            "hostname": f"{prefix.lower()}-srv-{i:03d}.internal.net",
            "ip_address": f"10.{random.randint(10, 80)}.{random.randint(1, 254)}.{i}",
            "criticality": "CRITICAL" if i <= int(count * 0.4) else ("HIGH" if i <= int(count * 0.8) else "MEDIUM"),
            "asset_type": random.choice(types),
            "expected_monitoring": True
        })
    return assets


def generate_multi_period_records() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    all_assets: List[Dict[str, Any]] = []
    all_alerts: List[Dict[str, Any]] = []
    all_cases: List[Dict[str, Any]] = []

    alert_global_idx = 1000
    case_global_idx = 500

    # Build assets
    entity_asset_map = {}
    for ent in ENTITIES_DATA:
        eid = ent["entity_id"]
        short = eid.split("-")[1]
        ast_list = generate_synthetic_assets(eid, ent["monitored_asset_count"], short)
        all_assets.extend(ast_list)
        entity_asset_map[eid] = ast_list

    for period in PERIODS:
        pid = period["period_id"]
        p_start = period["start"]

        # Base distribution per period
        entity_counts = {
            "CSE-POWER-01": 250,
            "CSE-BANK-02": 350,
            "CSE-HEALTH-03": 220,
            "CSE-TRANS-04": 260,
            "CSE-TELECOM-05": 140 if pid == "2025-Q4" else (80 if pid == "2026-Q1" else 40)  # Planted Coverage Deterioration!
        }

        for eid, target_count in entity_counts.items():
            assets = entity_asset_map[eid]
            short = eid.split("-")[1]

            # Telemetry deterioration for CSE-TELECOM-05
            if eid == "CSE-TELECOM-05":
                if pid == "2025-Q4":
                    reporting_assets = assets[:130]  # Normal in Q4
                elif pid == "2026-Q1":
                    reporting_assets = assets[:60]   # Deteriorating in Q1
                else:
                    reporting_assets = assets[:10]   # Severe Negative Space in Q2 (only 10 of 140)
            else:
                reporting_assets = assets

            health_repeat_asset = assets[0]["asset_id"] if eid == "CSE-HEALTH-03" else None

            for i in range(target_count):
                alert_global_idx += 1
                alert_id = f"ALT-{short}-{pid[:4]}-{alert_global_idx:05d}"
                offset_days = random.randint(0, 80)
                alert_time = p_start + timedelta(days=offset_days, hours=random.randint(0, 23), minutes=random.randint(0, 59))

                # Severity
                if eid == "CSE-BANK-02":
                    severity = random.choices(["CRITICAL", "HIGH", "MEDIUM", "LOW"], weights=[0.30, 0.40, 0.20, 0.10])[0]
                elif eid == "CSE-POWER-01":
                    severity = random.choices(["CRITICAL", "HIGH", "MEDIUM", "LOW"], weights=[0.25, 0.35, 0.25, 0.15])[0]
                else:
                    severity = random.choices(["CRITICAL", "HIGH", "MEDIUM", "LOW"], weights=[0.10, 0.25, 0.45, 0.20])[0]

                # Category
                if eid == "CSE-TELECOM-05" and pid == "2026-Q2":
                    available_cats = [c for c in ALERT_CATEGORIES if c not in ["RANSOMWARE", "DATA_EXFILTRATION", "MALWARE"]]
                    category = random.choice(available_cats)
                elif eid == "CSE-HEALTH-03" and i < 25:
                    category = "BRUTE_FORCE"
                elif eid == "CSE-POWER-01" and severity == "CRITICAL" and random.random() < 0.6:
                    category = "SCADA_COMMAND_ANOMALY"
                else:
                    category = random.choice(ALERT_CATEGORIES)

                asset_id = health_repeat_asset if (eid == "CSE-HEALTH-03" and category == "BRUTE_FORCE" and i < 25) else random.choice(reporting_assets)["asset_id"]
                investigator = random.choice(INVESTIGATORS)

                ack_time = alert_time + timedelta(minutes=random.randint(2, 20))

                # Planted behavioral characteristics
                if eid == "CSE-BANK-02":
                    # Rapid closure (2-5 mins) + template closure note
                    inv_time = ack_time + timedelta(minutes=1)
                    closed_time = inv_time + timedelta(minutes=random.randint(1, 4))
                    escalated = False
                    esc_time = None
                    root_cause = False
                    remediation = False
                    evidence = False
                    disposition = "BENIGN"
                    closure_note = "Standard automated alert - verified benign by analyst"
                elif eid == "CSE-POWER-01":
                    # Critical without escalation
                    inv_time = ack_time + timedelta(minutes=random.randint(15, 45))
                    closed_time = inv_time + timedelta(hours=random.randint(2, 6))
                    escalated = False if severity == "CRITICAL" else (random.random() < 0.25)
                    esc_time = inv_time + timedelta(minutes=30) if escalated else None
                    root_cause = True
                    remediation = True
                    evidence = True
                    disposition = "TRUE_POSITIVE" if severity == "CRITICAL" else "FALSE_POSITIVE"
                    closure_note = "SCADA command validated and boundary firewall rule confirmed."
                elif eid == "CSE-HEALTH-03":
                    # Repeated alerts without remediation on same asset
                    inv_time = ack_time + timedelta(minutes=random.randint(10, 40))
                    closed_time = inv_time + timedelta(hours=random.randint(1, 5))
                    escalated = random.random() < 0.2
                    esc_time = inv_time + timedelta(minutes=20) if escalated else None
                    if asset_id == health_repeat_asset:
                        root_cause = False
                        remediation = False
                        evidence = True
                        closure_note = "Recurring authentication failure; account unlocked without firewall IP block."
                    else:
                        root_cause = random.random() < 0.6
                        remediation = random.random() < 0.5
                        evidence = True
                        closure_note = "Resolved via standard hygiene."
                    disposition = "TRUE_POSITIVE"
                elif eid == "CSE-TRANS-04":
                    # Investigation evidence missing (85%+ zero evidence)
                    inv_time = ack_time + timedelta(minutes=random.randint(10, 30))
                    closed_time = inv_time + timedelta(hours=random.randint(1, 4))
                    escalated = random.random() < 0.1
                    esc_time = inv_time + timedelta(minutes=20) if escalated else None
                    root_cause = False
                    remediation = False
                    evidence = False
                    disposition = "RESOLVED"
                    closure_note = "Ticket closed."
                else: # CSE-TELECOM-05
                    inv_time = ack_time + timedelta(minutes=random.randint(20, 60))
                    closed_time = inv_time + timedelta(hours=random.randint(2, 8))
                    escalated = random.random() < 0.2
                    esc_time = inv_time + timedelta(minutes=30) if escalated else None
                    root_cause = True
                    remediation = True
                    evidence = True
                    disposition = "FALSE_POSITIVE"
                    closure_note = "Core routing filter verified."

                alert_record = {
                    "entity_id": eid,
                    "alert_id": alert_id,
                    "assessment_period_id": pid,
                    "alert_timestamp": alert_time.isoformat(),
                    "severity": severity,
                    "category": category,
                    "source_system": f"SIEM-SENSOR-{short}",
                    "asset_id": asset_id,
                    "acknowledged_timestamp": ack_time.isoformat(),
                    "investigation_started_timestamp": inv_time.isoformat(),
                    "closed_timestamp": closed_time.isoformat(),
                    "disposition": disposition,
                    "escalated": escalated,
                    "escalation_timestamp": esc_time.isoformat() if esc_time else None,
                    "investigator_id": investigator,
                    "root_cause_recorded": root_cause,
                    "remediation_recorded": remediation,
                    "evidence_present": evidence,
                    "status": "CLOSED",
                    "_meta_disclaimer": DISCLAIMER
                }
                all_alerts.append(alert_record)

                if severity in ["CRITICAL", "HIGH"] or random.random() < 0.3:
                    case_global_idx += 1
                    case_id = f"CAS-{short}-{pid[:4]}-{case_global_idx:05d}"
                    case_record = {
                        "entity_id": eid,
                        "case_id": case_id,
                        "assessment_period_id": pid,
                        "alert_id": alert_id,
                        "created_at": alert_time.isoformat(),
                        "assigned_at": ack_time.isoformat(),
                        "investigation_started_at": inv_time.isoformat(),
                        "escalation_status": "ESCALATED_LEAD" if escalated else "LOCAL_RESOLUTION",
                        "escalation_timestamp": esc_time.isoformat() if esc_time else None,
                        "closed_at": closed_time.isoformat(),
                        "disposition": disposition,
                        "root_cause": "Detailed root-cause recorded" if root_cause else None,
                        "remediation": "Permanent firewall fix implemented" if remediation else None,
                        "evidence": "PCAP dump and host logs attached" if evidence else None,
                        "investigator": investigator,
                        "closure_reason": closure_note,
                        "_meta_disclaimer": DISCLAIMER
                    }
                    all_cases.append(case_record)

    return all_assets, all_alerts, all_cases


def generate_dataset_records(target_alert_count: int = 500) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compatibility wrapper returning multi-period synthetic records."""
    return generate_multi_period_records()


def save_synthetic_csvs_and_seed_db(db: Session, target_alert_count: int = 3500) -> Dict[str, Any]:
    SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Seed Periods
    for p in PERIODS:
        existing_p = db.query(AssessmentPeriod).filter(AssessmentPeriod.period_id == p["period_id"]).first()
        if not existing_p:
            db.add(AssessmentPeriod(
                period_id=p["period_id"],
                name=p["name"],
                start_date=p["start"],
                end_date=p["end"],
                is_active=(p["period_id"] == "2026-Q2")
            ))
    db.commit()

    all_assets, all_alerts, all_cases = generate_multi_period_records()

    # 2. Write CSV / JSON files
    entities_csv_path = SYNTHETIC_DIR / "synthetic_entities.csv"
    with open(entities_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(ENTITIES_DATA[0].keys()))
        writer.writeheader()
        writer.writerows(ENTITIES_DATA)

    assets_csv_path = SYNTHETIC_DIR / "synthetic_assets.csv"
    with open(assets_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_assets[0].keys()))
        writer.writeheader()
        writer.writerows(all_assets)

    alerts_csv_path = SYNTHETIC_DIR / "synthetic_alerts.csv"
    with open(alerts_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_alerts[0].keys()))
        writer.writeheader()
        writer.writerows(all_alerts)

    cases_csv_path = SYNTHETIC_DIR / "synthetic_cases.csv"
    with open(cases_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_cases[0].keys()))
        writer.writeheader()
        writer.writerows(all_cases)

    # 3. Seed Entities & Assets
    for ent in ENTITIES_DATA:
        existing = db.query(Entity).filter(Entity.entity_id == ent["entity_id"]).first()
        if not existing:
            db.add(Entity(**ent))

    for ast in all_assets:
        existing = db.query(Asset).filter(Asset.asset_id == ast["asset_id"]).first()
        if not existing:
            db.add(Asset(**ast))
    db.commit()

    # 4. Bulk insert alerts
    alert_objs = []
    for a in all_alerts:
        existing = db.query(Alert.id).filter(Alert.alert_id == a["alert_id"]).first()
        if not existing:
            alert_objs.append(Alert(
                entity_id=a["entity_id"],
                alert_id=a["alert_id"],
                assessment_period_id=a["assessment_period_id"],
                alert_timestamp=datetime.fromisoformat(a["alert_timestamp"]),
                severity=a["severity"],
                category=a["category"],
                source_system=a["source_system"],
                asset_id=a["asset_id"],
                acknowledged_timestamp=datetime.fromisoformat(a["acknowledged_timestamp"]) if a.get("acknowledged_timestamp") else None,
                investigation_started_timestamp=datetime.fromisoformat(a["investigation_started_timestamp"]) if a.get("investigation_started_timestamp") else None,
                closed_timestamp=datetime.fromisoformat(a["closed_timestamp"]) if a.get("closed_timestamp") else None,
                disposition=a["disposition"],
                escalated=a["escalated"],
                escalation_timestamp=datetime.fromisoformat(a["escalation_timestamp"]) if a.get("escalation_timestamp") else None,
                investigator_id=a["investigator_id"],
                root_cause_recorded=a["root_cause_recorded"],
                remediation_recorded=a["remediation_recorded"],
                evidence_present=a["evidence_present"],
                status=a["status"],
                ingestion_batch_id="SYNTHETIC-MULTI-PERIOD",
                raw_data_json=json.dumps({"_disclaimer": DISCLAIMER})
            ))

    if alert_objs:
        for i in range(0, len(alert_objs), 500):
            db.bulk_save_objects(alert_objs[i:i + 500])

    # 5. Bulk insert cases
    case_objs = []
    for c in all_cases:
        existing = db.query(Case.id).filter(Case.case_id == c["case_id"]).first()
        if not existing:
            case_objs.append(Case(
                entity_id=c["entity_id"],
                case_id=c["case_id"],
                assessment_period_id=c["assessment_period_id"],
                alert_id=c.get("alert_id"),
                created_at=datetime.fromisoformat(c["created_at"]),
                assigned_at=datetime.fromisoformat(c["assigned_at"]) if c.get("assigned_at") else None,
                investigation_started_at=datetime.fromisoformat(c["investigation_started_at"]) if c.get("investigation_started_at") else None,
                escalation_status=c.get("escalation_status"),
                escalation_timestamp=datetime.fromisoformat(c["escalation_timestamp"]) if c.get("escalation_timestamp") else None,
                closed_at=datetime.fromisoformat(c["closed_at"]) if c.get("closed_at") else None,
                disposition=c.get("disposition"),
                root_cause=c.get("root_cause"),
                remediation=c.get("remediation"),
                evidence=c.get("evidence"),
                investigator=c.get("investigator"),
                closure_reason=c.get("closure_reason"),
                ingestion_batch_id="SYNTHETIC-MULTI-PERIOD"
            ))

    if case_objs:
        for i in range(0, len(case_objs), 500):
            db.bulk_save_objects(case_objs[i:i + 500])

    db.commit()

    return {
        "status": "SUCCESS",
        "disclaimer": DISCLAIMER,
        "periods": [p["period_id"] for p in PERIODS],
        "entities_count": len(ENTITIES_DATA),
        "assets_count": len(all_assets),
        "alerts_count": len(all_alerts),
        "cases_count": len(all_cases),
        "csv_files": {
            "entities": str(entities_csv_path),
            "assets": str(assets_csv_path),
            "alerts": str(alerts_csv_path),
            "cases": str(cases_csv_path)
        },
        "planted_scenarios": [
            "CSE-BANK-02: Rapid closure (<5 min) of critical alerts with identical boilerplate notes",
            "CSE-POWER-01: Critical SCADA unauthorized command alerts closed without supervisory escalation",
            "CSE-HEALTH-03: Repeated brute force attacks on same critical asset without permanent remediation",
            "CSE-TRANS-04: High alert volume with 85%+ zero investigative evidence attached",
            "CSE-TELECOM-05: Temporal Deterioration: Coverage erodes from 93% in 2025-Q4 down to 7% in 2026-Q2",
            "CSE-TELECOM-05: Expected Core Categories (Ransomware, Data Exfiltration) completely absent in 2026-Q2"
        ]
    }
