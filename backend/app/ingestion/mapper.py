from typing import Dict, Any, Optional
from app.ingestion.detector import FIELD_ALIASES, CANONICAL_ALERT_FIELDS, CANONICAL_CASE_FIELDS


def map_row_to_canonical(
    raw_row: Dict[str, Any],
    column_mapping: Optional[Dict[str, str]] = None,
    target_category: str = "ALERT",
    default_entity_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Translates raw keys in raw_row into canonical schema keys.
    column_mapping: {raw_col_name: canonical_field_name}
    """
    canonical_row: Dict[str, Any] = {}
    target_fields = CANONICAL_ALERT_FIELDS if target_category == "ALERT" else CANONICAL_CASE_FIELDS

    # Clean raw row keys
    clean_raw = {k.strip(): v for k, v in raw_row.items() if k is not None}

    # First, use explicit column_mapping if provided
    mapped_targets = set()
    if column_mapping:
        for src_col, target_field in column_mapping.items():
            if src_col in clean_raw and target_field in target_fields:
                canonical_row[target_field] = clean_raw[src_col]
                mapped_targets.add(target_field)

    # For any unmapped target fields, look through FIELD_ALIASES
    for target in target_fields:
        if target in mapped_targets:
            continue
        aliases = FIELD_ALIASES.get(target, [target])
        for alias in aliases:
            # Check direct match or lowercase match
            for raw_k, raw_v in clean_raw.items():
                if raw_k.lower().strip().replace(" ", "_") == alias:
                    canonical_row[target] = raw_v
                    mapped_targets.add(target)
                    break
            if target in mapped_targets:
                break

    # If entity_id is missing and default_entity_id is provided, assign it
    if not canonical_row.get("entity_id") and default_entity_id:
        canonical_row["entity_id"] = default_entity_id

    # Preserve remaining raw fields as raw_data
    canonical_row["raw_data"] = {k: v for k, v in clean_raw.items() if k not in canonical_row}

    return canonical_row
