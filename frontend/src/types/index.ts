export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
export type FindingCategory = 'EXECUTION_GAP' | 'NEGATIVE_SPACE' | 'ANOMALY';
export type ReviewStatus = 'OPEN' | 'UNDER_REVIEW' | 'CONFIRMED' | 'REJECTED' | 'DEFERRED' | 'REQUEST_EVIDENCE' | 'REVIEWED' | 'DISMISSED' | 'ESCALATED';

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
  assessment_period_id?: string;
  dataset_version_id?: string;
  finding_type: string;
  category: FindingCategory;
  capability_dimension?: string;
  rule_id?: string;
  severity: Severity;
  confidence: number;
  reason: string;
  evidence_summary: string;
  observed_value?: Record<string, any> | null;
  expected_value?: Record<string, any> | null;
  baseline?: Record<string, any> | null;
  metric_values?: Record<string, any> | null;
  recommended_review_area?: string | null;
  nist_csf_category?: string | null;
  mitre_attack_technique?: string | null;
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
  assessment_period_id?: string;
  run_id?: string | null;
  priority: string;
  status: ReviewStatus;
  assigned_reviewer?: string | null;
  notes?: string | null;
  finding_reason?: string | null;
  finding_category?: string | null;
  finding_severity?: string | null;
  capability_dimension?: string | null;
  recommended_review_area?: string | null;
  updated_at: string;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  action: string;
  entity_id?: string | null;
  actor: string;
  details?: Record<string, any> | null;
  previous_event_hash?: string | null;
  event_hash?: string | null;
}

export interface AuditVerificationResult {
  verified: boolean;
  total_events: number;
  tampered_events: number[];
  root_hash: string | null;
  latest_hash: string | null;
  status: string;
  verification_timestamp: string;
}

export interface AssessmentPeriodInfo {
  period_id: string;
  name: string;
  is_active: boolean;
  alert_count: number;
  case_count: number;
  latest_run_id: string | null;
  latest_run_timestamp: string | null;
}

export interface DataQualitySummary {
  assessment_period_id: string;
  entity_id: string | null;
  total_records_evaluated: number;
  overall_quality_pct: number;
  confidence_penalty_factor: number;
  completeness: { score_pct: number; total_fields_checked: number; missing_critical_values: number };
  validity: { score_pct: number; unknown_severities_preserved: number; unknown_statuses_preserved: number; schema_errors: number };
  timestamp_quality: { score_pct: number; missing_timestamps: number; future_timestamps: number; inversion_events: number };
  evidence_coverage: { score_pct: number; total_cases: number; cases_missing_evidence: number };
  quality_gate_passed: boolean;
  analytical_confidence_level: 'HIGH' | 'MODERATE' | 'LOW' | 'UNRELIABLE';
}

export interface PeerMetricComparison {
  metric_name: string;
  entity_value: number;
  peer_median: number;
  peer_iqr: number;
  peer_mad: number;
  deviation_from_median: number;
  status: 'TYPICAL' | 'ELEVATED' | 'DEVIATION_HIGH' | 'DEVIATION_LOW' | 'INSUFFICIENT_PEER_SAMPLE';
  interpretation: string;
}

export interface PeerBenchmarkReport {
  assessment_period_id: string;
  peer_groups_evaluated: number;
  peer_groups: Record<string, {
    peer_group_id: string;
    sample_size: number;
    sufficient_sample: boolean;
    members: string[];
    baselines: Record<string, { median: number; mad: number; iqr: number; q25: number; q75: number; count: number }>;
  }>;
  entity_comparisons: Record<string, {
    entity_id: string;
    peer_group_id: string;
    peer_sample_size: number;
    sufficient_sample: boolean;
    metrics: Record<string, PeerMetricComparison>;
    supervisory_deviations_count: number;
  }>;
}

export interface AnomalyDetail {
  entity_id: string;
  feature_name: string;
  observed_value: number;
  expected_median: number;
  deviation: number;
  threshold_applied: number;
  direction: string;
  why_flagged: string;
  confidence: number;
  sample_size: number;
  flagged_as_finding: boolean;
}

export interface AnomalySummary {
  assessment_period_id: string;
  methodology: string;
  adaptive_contamination: number;
  total_entities_evaluated: number;
  anomalies_detected: number;
  details: AnomalyDetail[];
}

export interface TemporalTrendSummary {
  entity_id?: string | null;
  assessment_periods_evaluated: string[];
  total_periods: number;
  sufficient_data_for_trend: boolean;
  temporal_findings: Array<{
    finding_id?: string;
    finding_type: string;
    entity_id: string;
    severity: string;
    reason: string;
    evidence_summary: string;
    trend_metrics: Record<string, any>;
  }>;
  entity_profiles: Record<string, {
    entity_id: string;
    periods_count: number;
    coverage_trend: { slope: number; persistence: number; status: string };
    unremediated_repeat_rate_trend: { slope: number; persistence: number; status: string };
    rapid_closure_rate_trend: { slope: number; persistence: number; status: string };
    supervisory_attention_trend: { slope: number; persistence: number; status: string };
    overall_trajectory: string;
  }>;
}

export interface PrioritizedSample {
  alert_id: string;
  entity_id: string;
  timestamp: string;
  alert_type: string;
  severity: string;
  status: string;
  priority_score: number;
  priority_rank: number;
  selection_category: string;
  why_selected: string;
  case_id?: string | null;
  closure_duration_seconds?: number | null;
  evidence_count?: number;
}

export interface SupervisoryReportData {
  report_metadata: {
    report_title: string;
    classification_banner: string;
    generation_timestamp: string;
    assessment_period_id: string;
    analysis_run_id: string;
    ruleset_version: string;
    analytics_version: string;
    mode: string;
  };
  executive_summary: {
    total_entities_assessed: number;
    entities_requiring_attention: number;
    total_findings_generated: number;
    critical_findings_count: number;
    high_findings_count: number;
    key_takeaway: string;
  };
  data_quality_summary: DataQualitySummary;
  entities_assessed: Array<{
    entity_id: string;
    name: string;
    sector: string;
    supervisory_attention_indicator: number;
    supervisory_attention_level: string;
    data_quality_pct: number;
    capability_profile: Record<string, { score: number; status: string }>;
    findings_count: number;
  }>;
  execution_gaps_summary: { total: number; rules_triggered: Record<string, number> };
  negative_space_summary: { total_concerns: number };
  anomalies_summary: { total_anomalies: number; methodology: string };
  peer_benchmarking_summary: { peer_groups_count: number; total_deviations: number };
  temporal_drift_summary: { periods_evaluated: string[]; persistent_weaknesses_count: number };
  prioritized_samples_count: number;
  audit_chain_verification: { verified: boolean; total_events: number; latest_hash: string | null };
}

export interface ExpertReviewValidation {
  run_id: string;
  total_expert_labels: number;
  sufficient_expert_data: boolean;
  status: string;
  confusion_matrix: { tp: number; fp: number; tn: number; fn: number };
  metrics: { precision: number; recall: number; f1_score: number };
  labels: Array<{
    label_id: number;
    target_type: string;
    target_id: string;
    entity_id: string;
    expert_label: string;
    severity: string;
    reviewer_name: string;
    evidence_notes?: string | null;
    created_at: string;
  }>;
}
