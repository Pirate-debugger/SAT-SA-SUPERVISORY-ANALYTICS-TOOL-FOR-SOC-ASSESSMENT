# SAT-SA — Supervisory Analytics Tool for SOC Assessment
**Smart India Hackathon Prototype — Problem Statement ID: SIH26157**

> **CLASSIFICATION**: DEMO / SYNTHETIC DATA — NOT FOR OPERATIONAL USE  
> *This platform is an offline-first technical demonstration prototype. It contains synthetic telemetry and planted supervisory test scenarios. Not real government or critical sector operational data.*

---

## 1. Executive Purpose & Problem Statement

**SAT-SA is an Offline-First Supervisory Analytics Platform for Critical Sector Entities (CSEs).**

Under the official SIH26157 specification, supervisory authorities (e.g., sector certs, national regulators) receive periodic operational data submissions from SOCs operating across power grids, financial networks, healthcare infrastructure, transportation grids, and telecommunication backbones.

SAT-SA solves the supervisory blind spot:
- It is **NOT** a SIEM, NOT a SOC replacement, and NOT a real-time log collector.
- It analyzes periodic alert and case-management submissions across multiple CSEs to identify:
  1. **Execution Gaps**: Procedures bypassed (e.g., critical alerts closed in minutes, critical alerts closed without escalation, repeated unmitigated alerts, metric optimization with weak investigation evidence).
  2. **Negative Space**: Absence of evidence expected of a competent SOC (unmonitored critical assets, absent threat categories, unexpected telemetry silence).
  3. **Operational Anomalies**: Hybrid deterministic, statistical, and Isolation Forest detections.
  4. **Peer Deviations**: Robust median and IQR comparison within cohort groups.
  5. **Temporal Drift**: Multi-period regression slope and deterioration tracking.
  6. **Evidence Chain**: Complete, unbroken drill-down from **Supervisory Finding → Rule/Detector → Metric → Baseline → Raw Ingested Record**.
  7. **Prioritized Review Samples**: Distilling thousands of alerts down to top high-value samples for human supervisor review.

The supervisor remains the authoritative final decision-maker.

---

## 2. Air-Gapped Offline-First Architecture

SAT-SA is designed to operate in high-security, air-gapped supervisory enclaves:
- **Zero External Calls**: No cloud APIs, no external LLM services, no SaaS telemetry, no CDN scripts, and no external web fonts.
- **Backend**: Python 3.14 + FastAPI + SQLAlchemy 2.0.
- **Analytics Engine**: Deterministic rulesets + Scikit-Learn local Isolation Forest + Scipy/NumPy robust statistics.
- **Database**: SQLite with automated schema migration and write-ahead locking (`backend/sat_sa.db`).
- **Frontend**: React + TypeScript + Vite + Tailwind CSS/CSS modules.
- **Tamper-Evident Audit Chain**: SHA-256 cryptographic hash chain linking all system events, runs, reviews, and reports.

```
                    +------------------------------------+
                    |  CSE Periodic Data Submissions     |
                    |  (Alerts, Cases, Asset Inventories)|
                    +-----------------+------------------+
                                      |
                                      v
                    +-----------------+------------------+
                    |  Data Ingestion & Normalization    |
                    |  - Data Quality Engine             |
                    |  - SHA-256 File Provenance         |
                    |  - UNKNOWN Preservation            |
                    +-----------------+------------------+
                                      |
                                      v
                    +-----------------+------------------+
                    |  Authoritative Analytics Engine    |
                    |  - Run Isolation & Idempotency     |
                    |  - 8 Capability Dimensions         |
                    |  - Execution Gaps (A-H)            |
                    |  - Negative Space Expectation      |
                    |  - Hybrid Local Anomalies          |
                    |  - Robust Peer Benchmarks (MAD/IQR)|
                    |  - Temporal Multi-Period Drift     |
                    |  - Supervisory Attention Indicator |
                    +-----------------+------------------+
                                      |
                                      v
                    +-----------------+------------------+
                    |  Evidence Chain & Review Workflow  |
                    |  - 6-State Formal Review Queue     |
                    |  - Sample Prioritization Engine    |
                    |  - Direct Source Record Drill-down |
                    +-----------------+------------------+
                                      |
                                      v
                    +-----------------+------------------+
                    |  Supervisory Surfaces              |
                    |  - Interactive Web Console (React) |
                    |  - 18-Section Exportable Report    |
                    |  - Tamper-Evident Audit Verify API |
                    +------------------------------------+
```

---

## 3. Core Analytical Engines

### A. Execution Gap Engine (Rules A–H)
Detects operational compromises and workflow gaming:
- **Rule A (CRITICAL_ALERT_RAPID_CLOSURE)**: Critical alerts closed in < 3 minutes without triage.
- **Rule B (ACKNOWLEDGED_WEAK_INVESTIGATION)**: Acknowledged alerts lacking evidence logs.
- **Rule C (CRITICAL_ALERTS_WITHOUT_ESCALATION)**: Critical alerts closed without Tier-2/supervisory escalation.
- **Rule D (REPEATED_ALERTS_WITHOUT_REMEDIATION)**: Identical asset alert recurring with zero recorded root cause.
- **Rule E (REPETITIVE_TEMPLATE_INVESTIGATIONS)**: Identical boilerplate text repeatedly used for dispositions.
- **Rule F (METRIC_OPTIMIZATION_WEAK_EVIDENCE)**: High closure rate combined with < 40% evidence attachment.
- **Rule G (INVESTIGATION_WORKLOAD_INCONSISTENCY)**: Analyst closing > 80 cases/day without commensurate logs.
- **Rule H (REPORTED_CAPABILITY_INCONSISTENCY)**: Tier-1 claimed capability with Tier-3 operational discipline.

### B. Negative Space Expectation Engine
Calculates what is **missing** rather than merely what triggered:
- Contrasts declared critical asset inventories against active reporting telemetry.
- Detects unmonitored attack surface: `Coverage Gap = (Declared Assets - Active Assets) / Declared Assets`.
- Identifies absent mandatory alert categories (Ransomware, Exfiltration, Privilege Escalation).
- Uses cautious terminology: `POTENTIAL NEGATIVE SPACE`, `MONITORING COVERAGE GAP`, `INSUFFICIENT EVIDENCE`.

### C. Robust Peer Benchmarking Engine
- Groups CSEs by Sector and Claimed Tier.
- Applies robust statistics (Median, Interquartile Range, Median Absolute Deviation).
- Calculates entity deviations from peer cohort baselines without global pooled contamination.

### D. Real Hybrid Local Anomaly Engine
- Deterministic heuristic checks + statistical outlier detection + Scikit-Learn `IsolationForest`.
- Dynamically adapts contamination rate to feature quality and sample size.
- Promotes every actionable anomaly into a first-class `Finding` belonging to category `ANOMALY`.

### E. Eight Supervisory Capability Dimensions
Evaluates actual evidence across official dimensions:
1. Threat Detection
2. Investigation
3. Escalation
4. Incident Response
5. Security Operations
6. Governance and Oversight
7. Operational Discipline
8. Cyber Resilience

Each dimension provides observed metrics, baselines, confidence, and status (`STRONG EVIDENCE`, `ATTENTION`, `INSUFFICIENT EVIDENCE`, `NOT ASSESSED`).

### F. Explainable Supervisory Attention Indicator (SAI)
Deterministic 0–100 index with full category breakdown:
- Execution Gaps contribution
- Negative Space contribution
- Capability deficits
- Peer deviations penalty
- Anomalies & Temporal persistence

---

## 4. Analysis Run Isolation & Idempotency

- Every finding and metric belongs to an isolated `(analysis_run_id, assessment_period_id, dataset_version_id)`.
- Re-running analysis with identical dataset, period, ruleset, and model versions produces an idempotent result without creating duplicate active findings or inflating risk scores.
- Historical runs remain immutable; the dashboard always defaults to the latest completed run for the selected assessment period.

---

## 5. Tamper-Evident Audit Chain

- Every major action (data ingestion, validation, analysis run execution, supervisory review state change, expert annotation, and report generation) appends to a SHA-256 cryptographic audit chain:
  `event_hash = SHA256(previous_event_hash | timestamp | action | actor | details_json)`
- Integrity can be verified at any time via `GET /api/audit/verify` or via the web console.

---

## 6. Review Workflow & Expert Validation

### A. 6-State Formal Review Workflow
Supervisors process findings through explicit states:
`OPEN` → `UNDER_REVIEW` → `CONFIRMED` | `REJECTED` | `DEFERRED` | `REQUEST_EVIDENCE`
*Review is not confirmation. Review actions, reviewer identities, and supervisor notes are permanently logged in the audit trail.*

### B. Dual-Mode Validation Framework
- **Mode A (Synthetic Ground-Truth Benchmark)**: Measures True Positives, False Positives, False Negatives, Precision, Recall, and F1 against planted ground-truth scenarios.
- **Mode B (Human Expert Review Mode)**: Authorized human experts submit independent annotations. Calibration and agreement rates are only calculated when actual expert labels exist.

---

## 7. Quick Start & Setup

### Prerequisites
- Python 3.11+ (Python 3.14 tested)
- Node.js 18+ & npm
- PowerShell or Bash

### Backend Setup & Execution
```powershell
# From workspace root
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Backend API will be active at `http://127.0.0.1:8000`  
Interactive Swagger API docs at `http://127.0.0.1:8000/docs`

### Frontend Setup & Execution
```powershell
# In a separate terminal from workspace root
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
Web console will be active at `http://127.0.0.1:5173`

### Production Build Verification
```powershell
# Frontend production build
cd frontend
npm run build
```

---

## 8. Automated Test Suite

Run the full automated test suite (30 passing tests covering all analytical and compliance requirements):
```powershell
.\backend\.venv\Scripts\pytest backend/tests -v
```

Test coverage includes:
- Data ingestion, CSV parsing, date normalization, schema validation
- Data quality engine & UNKNOWN value preservation
- Run isolation, idempotency, and historical separation
- Execution gap detection (Rules A–H) and source record traceability
- Negative space expectation engine and asset coverage gaps
- Robust statistical peer benchmarking (MAD, IQR)
- Real hybrid anomaly engine & first-class anomaly findings
- Eight capability dimensions and explainable attention indicator breakdown
- Temporal multi-period drift, regression slopes, and deterioration signals
- Sample prioritization engine with explainable selection reasoning
- Six-state review workflow and non-auto-confirmation
- Tamper-evident SHA-256 audit chain verification
- Dual-mode validation (Mode A Synthetic + Mode B Expert)
- Air-gapped offline compliance verification (zero outbound network calls)
- Multi-section supervisory report generator and markdown export

---

## 9. API Reference Overview

| Endpoint | Method | Description |
|---|---|---|
| `/api/system/status` | GET | Air-gapped offline compliance status & system health |
| `/api/analysis/periods` | GET | List available assessment periods |
| `/api/analysis/runs` | GET / POST | Manage and trigger run-isolated supervisory assessments |
| `/api/analysis/dashboard-summary` | GET | Authoritative metrics across all evaluated entities |
| `/api/analysis/entity/{id}` | GET | Canonical supervisory profile, metrics, & 8 dimensions |
| `/api/analysis/findings` | GET | Filterable findings with direct evidence link counts |
| `/api/analysis/findings/{id}` | GET | Finding detail with full evidence chain and raw records |
| `/api/analysis/negative-space` | GET | Advanced expectation model & unmonitored assets |
| `/api/analysis/anomalies` | GET | Hybrid anomaly engine detections & first-class findings |
| `/api/analysis/peer-benchmarks` | GET | Robust peer cohort medians, deviations, & sample sizes |
| `/api/analysis/temporal-drift` | GET | Multi-period regression slopes, deterioration, & persistence |
| `/api/analysis/sample-recommendations`| GET | Prioritized review sample recommender |
| `/api/analysis/data-quality` | GET | Ingestion completeness, validity, & confidence factors |
| `/api/analysis/validation-benchmark` | GET | Mode A Synthetic Ground-Truth Benchmark metrics |
| `/api/analysis/validation/expert-review` | GET | Mode B Human Expert Review calibration status |
| `/api/analysis/validation/expert-labels` | POST | Submit authorized human expert labels |
| `/api/reviews` | GET / POST | Retrieve review queue and record supervisor actions |
| `/api/audit/verify` | GET | Cryptographically verify SHA-256 audit chain integrity |
| `/api/report` | GET | Generate 18-section supervisory assessment report |
| `/api/report/markdown` | GET | Download formal Markdown audit report |

---

## 10. Operational Limitations & Boundaries

1. **Periodic Telemetry**: SAT-SA evaluates periodic batch telemetry submitted by entities. It does not replace live inline packet sensors or endpoint agents.
2. **Supervisory Signals**: Statistical outliers and execution gaps indicate potential operational deviations requiring supervisor inquiry; they do not constitute legal proof of malicious breach.
3. **Sensor Blind Spots**: If an entity omits an asset from its declared inventory and produces zero logs, the system identifies the absence of expected threat categories but cannot physically discover unlisted hardware without network tap verification.
4. **Air-Gapped Constraint**: System is self-contained. Any enrichment feeds (e.g. NIST CSF 2.0 mapping or MITRE ATT&CK taxonomy) are bundled offline.
