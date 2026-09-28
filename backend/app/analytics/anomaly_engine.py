import numpy as np
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sklearn.ensemble import IsolationForest

from app.models.entity import Entity
from app.models.alert import Alert


MIN_ENTITIES_FOR_ML = 3


def detect_operational_anomalies(
    db: Session,
    assessment_period_id: str = "2026-Q2"
) -> Dict[str, Any]:
    """
    Combines robust Median + MAD statistical deviation with local Isolation Forest.
    Outputs feature-level anomalies with baseline comparisons and plain English explanations.
    """
    entities = db.query(Entity).all()
    if len(entities) < MIN_ENTITIES_FOR_ML:
        return {
            "status": "UNABLE TO ASSESS",
            "reason": f"Sample size ({len(entities)} entities) is below minimum required ({MIN_ENTITIES_FOR_ML}) for statistical confidence.",
            "anomalies_by_entity": {}
        }

    # Extract multi-dimensional feature matrix
    feature_names = [
        "alert_volume",
        "closure_duration_mins",
        "evidence_present_rate",
        "critical_escalation_rate",
        "coverage_gap_pct"
    ]

    entity_ids = []
    matrix = []

    for ent in entities:
        eid = ent.entity_id
        alerts = db.query(Alert).filter(
            Alert.entity_id == eid,
            Alert.assessment_period_id == assessment_period_id
        ).all()

        if not alerts:
            alerts = db.query(Alert).filter(Alert.entity_id == eid).all()

        total = len(alerts)
        durations = []
        for a in alerts:
            if a.closed_timestamp and a.alert_timestamp:
                dur = (a.closed_timestamp - a.alert_timestamp).total_seconds() / 60.0
                if dur > 0:
                    durations.append(dur)

        median_dur = float(np.median(durations)) if durations else 45.0
        ev_rate = (sum(1 for a in alerts if a.evidence_present) / max(total, 1)) * 100.0

        crit_alerts = [a for a in alerts if a.severity == "CRITICAL"]
        crit_esc_rate = (sum(1 for a in crit_alerts if a.escalated) / max(len(crit_alerts), 1)) * 100.0

        declared = ent.monitored_asset_count or 1
        active_assets = len({a.asset_id for a in alerts if a.asset_id})
        coverage_gap = max(0.0, ((declared - active_assets) / declared) * 100.0)

        entity_ids.append(eid)
        matrix.append([
            float(total),
            median_dur,
            ev_rate,
            crit_esc_rate,
            coverage_gap
        ])

    X = np.array(matrix, dtype=float)

    # 1. Local Isolation Forest (deterministic seed)
    iso = IsolationForest(contamination=0.25, random_state=42)
    iso.fit(X)
    ml_scores = iso.decision_function(X)
    ml_preds = iso.predict(X)  # -1 for anomaly, 1 for inlier

    # 2. Robust MAD Feature-Level Deviations
    col_medians = np.median(X, axis=0)
    col_mads = np.median(np.abs(X - col_medians), axis=0)
    # Avoid zero division
    col_mads = np.where(col_mads == 0, 1.0, col_mads)

    anomalies_by_entity: Dict[str, List[Dict[str, Any]]] = {eid: [] for eid in entity_ids}

    for i, eid in enumerate(entity_ids):
        row = X[i]
        is_ml_outlier = (ml_preds[i] == -1)

        for j, feat_name in enumerate(feature_names):
            val = row[j]
            med = col_medians[j]
            mad = col_mads[j]
            # Modified z-score: 0.6745 * (x - median) / MAD
            mod_z = 0.6745 * (val - med) / mad

            if abs(mod_z) >= 2.0:
                direction = "ABNORMALLY_HIGH" if mod_z > 0 else "ABNORMALLY_LOW"
                why = ""
                if feat_name == "closure_duration_mins" and mod_z < 0:
                    why = f"Alert closure time ({val:.1f}m) is significantly faster than peer median ({med:.1f}m), suggesting rapid dismissal."
                elif feat_name == "evidence_present_rate" and mod_z < 0:
                    why = f"Investigation evidence rate ({val:.1f}%) is severely depressed relative to peer median ({med:.1f}%)."
                elif feat_name == "coverage_gap_pct" and mod_z > 0:
                    why = f"Monitored asset coverage gap ({val:.1f}%) significantly exceeds peer norm ({med:.1f}%)."
                elif feat_name == "alert_volume" and mod_z < 0:
                    why = f"Alert volume ({val:.0f}) is unexpectedly depressed for entity profile ({med:.0f} median)."
                else:
                    why = f"Feature {feat_name} deviates by {mod_z:.1f} robust standard deviations from peer baseline."

                anomalies_by_entity[eid].append({
                    "feature": feat_name,
                    "observed": round(float(val), 2),
                    "baseline_median": round(float(med), 2),
                    "mad_deviation": round(float(mod_z), 2),
                    "anomaly_direction": direction,
                    "ml_outlier_confirmed": is_ml_outlier,
                    "why_flagged": why
                })

    return {
        "status": "COMPLETED",
        "sample_size": len(entities),
        "method": "HYBRID_ISOLATION_FOREST_PLUS_MAD",
        "anomalies_by_entity": anomalies_by_entity
    }
