export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
export type FindingCategory = 'EXECUTION_GAP' | 'NEGATIVE_SPACE' | 'ANOMALY';
export type ReviewStatus = 'OPEN' | 'UNDER_REVIEW' | 'REVIEWED' | 'DISMISSED' | 'ESCALATED';

export interface DashboardSummary {
  total_entities: number;
  entities_requiring_attention: number;
  high_risk_findings: number;
  execution_gaps_count: number;
  negative_space_count: number;
  anomalies_count: number;
  total_alerts_ingested: number;
  total_cases_ingested: number;
  latest_run_id: string | null;
  latest_run_timestamp: string | null;
}

export interface EntitySupervisoryCard {
  entity_id: string;
  name: string;
  sector: string;
  claimed_tier: string;
  monitored_asset_count: number;
  active_reporting_assets: number;
  coverage_gap_pct: number;
  total_alerts: number;
  total_cases: number;
  execution_gaps_count: number;
  negative_space_count: number;
  anomalies_count: number;
  risk_level: RiskLevel;
  risk_score: number;
  primary_concerns: string[];
}

export interface Finding {
  finding_id: string;
  run_id: string;
  entity_id: string;
  finding_type: string;
  category: FindingCategory;
  severity: Severity;
  confidence: number;
  reason: string;
  evidence_summary: string;
  metric_values?: Record<string, any> | null;
  baseline?: Record<string, any> | null;
  sample_size: number;
  status: string;
  created_at: string;
}

export interface EvidenceRecord {
  record_type: 'ALERT' | 'CASE' | 'ASSET';
  record_id: string;
  relevance_note?: string | null;
  details?: Record<string, any> | null;
}

export interface FindingDetail extends Finding {
  evidence_records: EvidenceRecord[];
}

export interface AnalysisRun {
  run_id: string;
  timestamp: string;
  dataset_version: string;
  ruleset_version: string;
  analytics_version: string;
  status: string;
  entities_analyzed_count: number;
  alerts_analyzed_count: number;
  cases_analyzed_count: number;
  findings_count: number;
  summary?: Record<string, any> | null;
  execution_time_seconds: number;
}

export interface IngestionBatch {
  batch_id: string;
  filename: string;
  file_type: string;
  entity_id?: string | null;
  status: string;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  duplicate_records: number;
  created_at: string;
}

export interface IngestionValidationReport {
  batch_id: string;
  filename: string;
  file_type: string;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  duplicate_records: number;
  missing_fields: string[];
  normalization_warnings: string[];
  invalid_samples: any[];
  status: string;
  message: string;
}

export interface ReviewItem {
  review_id: string;
  finding_id: string;
  entity_id: string;
  priority: string;
  status: ReviewStatus;
  assigned_reviewer?: string | null;
  notes?: string | null;
  finding_reason?: string | null;
  finding_category?: string | null;
  finding_severity?: string | null;
  updated_at: string;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  action: string;
  entity_id?: string | null;
  actor: string;
  details?: Record<string, any> | null;
}
