import os
import shutil
import json
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import UPLOADS_DIR
from app.models.ingestion import IngestionBatch
from app.schemas.ingestion import IngestionValidationReport, DetectedSchema
from app.ingestion.detector import (
    detect_file_type, inspect_csv_columns_and_sample,
    inspect_json_columns_and_sample, detect_schema_category,
    suggest_mapping
)
from app.ingestion.pipeline import run_ingestion_pipeline

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.post("/inspect", response_model=DetectedSchema)
async def inspect_uploaded_file(file: UploadFile = File(...)):
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = UPLOADS_DIR / f"inspect_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_type = detect_file_type(temp_path)
    if file_type not in ["CSV", "JSON"]:
        if temp_path.exists():
            temp_path.unlink()
        raise HTTPException(status_code=400, detail=f"Unsupported format: {file_type}. Supported: CSV, JSON.")

    if file_type == "CSV":
        columns, sample_rows, row_count = inspect_csv_columns_and_sample(temp_path)
    else:
        columns, sample_rows, row_count = inspect_json_columns_and_sample(temp_path)

    category, confidence = detect_schema_category(columns)
    suggested = suggest_mapping(columns, category)

    warnings = []
    if row_count == 0:
        warnings.append("File contains 0 records.")
    if "entity_id" not in suggested.values():
        warnings.append("No entity_id column identified. Will require default entity ID.")

    return DetectedSchema(
        filename=file.filename or "unknown",
        file_type=file_type,
        total_rows_detected=row_count,
        detected_data_category=category,
        columns_detected=columns,
        suggested_mappings=suggested,
        confidence=confidence,
        warnings=warnings
    )


@router.post("/upload", response_model=IngestionValidationReport)
async def upload_and_ingest_file(
    file: UploadFile = File(...),
    target_category: Optional[str] = Form(None),
    default_entity_id: Optional[str] = Form(None),
    column_mapping_json: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    saved_path = UPLOADS_DIR / f"upload_{file.filename}"
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    custom_mapping = None
    if column_mapping_json:
        try:
            custom_mapping = json.loads(column_mapping_json)
        except Exception:
            pass

    report = run_ingestion_pipeline(
        file_path=saved_path,
        db=db,
        target_category=target_category,
        column_mapping=custom_mapping,
        default_entity_id=default_entity_id
    )

    return report


@router.get("/batches")
def list_ingestion_batches(db: Session = Depends(get_db)):
    batches = db.query(IngestionBatch).order_by(IngestionBatch.created_at.desc()).limit(50).all()
    return [
        {
            "batch_id": b.batch_id,
            "filename": b.filename,
            "file_type": b.file_type,
            "entity_id": b.entity_id,
            "status": b.status,
            "total_records": b.total_records,
            "valid_records": b.valid_records,
            "invalid_records": b.invalid_records,
            "duplicate_records": b.duplicate_records,
            "created_at": b.created_at
        } for b in batches
    ]


@router.get("/batches/{batch_id}")
def get_ingestion_batch_detail(batch_id: str, db: Session = Depends(get_db)):
    b = db.query(IngestionBatch).filter(IngestionBatch.batch_id == batch_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Batch not found")

    return {
        "batch_id": b.batch_id,
        "filename": b.filename,
        "file_type": b.file_type,
        "entity_id": b.entity_id,
        "status": b.status,
        "total_records": b.total_records,
        "valid_records": b.valid_records,
        "invalid_records": b.invalid_records,
        "duplicate_records": b.duplicate_records,
        "missing_fields": json.loads(b.missing_fields_json) if b.missing_fields_json else [],
        "normalization_warnings": json.loads(b.normalization_warnings_json) if b.normalization_warnings_json else [],
        "invalid_records_sample": json.loads(b.invalid_records_sample_json) if b.invalid_records_sample_json else [],
        "created_at": b.created_at
    }
