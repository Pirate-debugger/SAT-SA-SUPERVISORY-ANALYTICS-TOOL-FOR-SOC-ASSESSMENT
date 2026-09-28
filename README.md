# SAT-SA — Supervisory Analytics Tool for SOC Assessment
**Smart India Hackathon 2026 Prototype — Problem Statement ID: SIH26157**

## Purpose & Core Principle

**SAT-SA is a SUPERVISORY ANALYTICS PLATFORM.**

It is **NOT** a SIEM, NOT a SOC replacement, NOT a real-time monitoring system, and NOT a continuous telemetry collector.

The purpose is to analyze periodic SOC alert and case-management submissions from multiple Critical Sector Entities (CSEs) to help supervisory authorities identify:
1. **Execution Gaps**: Operational deviations where procedures are bypassed (e.g., high-severity alerts closed in minutes, critical alerts closed without escalation, repeated unmitigated alerts, metric optimization/gaming with weak investigation evidence).
2. **Negative Space**: Absence of evidence that would normally be expected of a competent SOC (e.g., declared critical assets producing 0 telemetry, absent core attack categories, missing investigation logs).
3. **Traceability**: Direct drill-down from **Finding → Metric → Linked Evidence Records (Alerts/Cases/Assets)**.

---

## Architecture & Technology Stack

- **Operating Environment**: Fully local, air-gapped offline environment. **No cloud dependency, no external AI API, no SaaS dependency.**
- **Backend**: Python 3.14 + FastAPI + SQLAlchemy 2.0
- **Database**: SQLite (`backend/sat_sa.db`)
- **Analytics Engine**: Deterministic ruleset + Explainable statistical baseline engine (`v1.0.0-offline`)
- **Frontend**: React + TypeScript + Vite + Vanilla CSS design system
- **Ingestion**: Supports CSV, JSON, and SQLite exports with schema detection, alias mapping, data normalization, and integrity validation.

---

## Quick Start (Offline Local Startup)

### 1. Backend Setup & Startup

```powershell
# From workspace root
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Backend API will be available at: `http://127.0.0.1:8000` (Docs at `http://127.0.0.1:8000/docs`)

### 2. Frontend Setup & Startup

```powershell
# In a separate terminal from workspace root
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
Frontend Web Console will be available at: `http://127.0.0.1:5173`

### 3. Run Automated Tests

```powershell
.\backend\.venv\Scripts\pytest backend/tests -v
```

---

## Synthetic Demo Scenarios (Planted Signals)

SAT-SA includes an automated generator producing multi-entity datasets with 7 planted supervisory signals across 5 CSEs:
1. **CSE-BANK-02**: Rapid closure of Critical/High alerts (avg 3.2 min vs baseline 60 min) with template boilerplate notes (metrics gaming).
2. **CSE-POWER-01**: Critical SCADA unauthorized command alerts closed without required supervisory escalation.
3. **CSE-HEALTH-03**: Repeated brute force attacks on same critical asset (35+ times) with zero remediation or root cause recorded.
4. **CSE-TRANS-04**: High alert volume with 0% attached investigation evidence and zero documented root cause.
5. **CSE-TELECOM-05**: Massive Negative Space — only 10 out of 140 declared critical assets ever report telemetry (92.9% Coverage Gap), with core malware categories completely missing.

*All demo records are explicitly marked with `DEMO/SYNTHETIC - NOT REAL GOVERNMENT DATA`.*
