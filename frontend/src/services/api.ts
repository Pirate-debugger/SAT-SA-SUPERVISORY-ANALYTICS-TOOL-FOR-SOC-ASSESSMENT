import {
  DashboardSummary,
  EntitySupervisoryCard,
  Finding,
  FindingDetail,
  AnalysisRun,
  IngestionBatch,
  IngestionValidationReport,
  ReviewItem,
  AuditLog,
  AuditVerificationResult,
  AssessmentPeriodInfo,
  DataQualitySummary,
  PeerBenchmarkReport,
  AnomalySummary,
  TemporalTrendSummary,
  PrioritizedSample,
  SupervisoryReportData,
  ExpertReviewValidation
} from '../types';

const API_BASE = '/api';

export const api = {
  // System status
  async getStatus(): Promise<any> {
    const res = await fetch(`${API_BASE}/status`);
    if (!res.ok) throw new Error('Failed to fetch system status');
    return res.json();
  },

  // Assessment Periods (Section 34)
  async getAssessmentPeriods(): Promise<AssessmentPeriodInfo[]> {
    const res = await fetch(`${API_BASE}/periods`);
    if (!res.ok) throw new Error('Failed to fetch assessment periods');
    return res.json();
  },

  // Dashboard summary with isolated assessment period
  async getDashboardSummary(assessmentPeriodId?: string): Promise<DashboardSummary> {
    const url = assessmentPeriodId 
      ? `${API_BASE}/dashboard/summary?assessment_period_id=${encodeURIComponent(assessmentPeriodId)}`
      : `${API_BASE}/dashboard/summary`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch dashboard summary');
    return res.json();
  },

  // Entities
  async getEntities(assessmentPeriodId?: string): Promise<EntitySupervisoryCard[]> {
    const url = assessmentPeriodId 
      ? `${API_BASE}/entities?assessment_period_id=${encodeURIComponent(assessmentPeriodId)}`
      : `${API_BASE}/entities`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch entities');
    return res.json();
  },

  async getEntityDetail(entityId: string, assessmentPeriodId?: string, runId?: string): Promise<any> {
    const search = new URLSearchParams();
    if (assessmentPeriodId) search.append('assessment_period_id', assessmentPeriodId);
    if (runId) search.append('run_id', runId);
    const qs = search.toString() ? `?${search.toString()}` : '';
    const res = await fetch(`${API_BASE}/entities/${entityId}${qs}`);
    if (!res.ok) throw new Error(`Failed to fetch entity ${entityId}`);
    return res.json();
  },

  // Findings & Evidence
  async getFindings(params?: { entity_id?: string; category?: string; severity?: string; run_id?: string; assessment_period_id?: string }): Promise<Finding[]> {
    const search = new URLSearchParams();
    if (params?.entity_id) search.append('entity_id', params.entity_id);
    if (params?.category) search.append('category', params.category);
    if (params?.severity) search.append('severity', params.severity);
    if (params?.run_id) search.append('run_id', params.run_id);
    if (params?.assessment_period_id) search.append('assessment_period_id', params.assessment_period_id);

    const res = await fetch(`${API_BASE}/findings?${search.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch findings');
    return res.json();
  },

  async getFindingDetail(findingId: string): Promise<FindingDetail> {
    const res = await fetch(`${API_BASE}/findings/${findingId}`);
    if (!res.ok) throw new Error(`Failed to fetch finding ${findingId}`);
    return res.json();
  },

  // Analysis Runs
  async getAnalysisRuns(assessmentPeriodId?: string, onlyLatest?: boolean): Promise<AnalysisRun[]> {
    const search = new URLSearchParams();
    if (assessmentPeriodId) search.append('assessment_period_id', assessmentPeriodId);
    if (onlyLatest) search.append('only_latest', 'true');
    const res = await fetch(`${API_BASE}/analysis/runs?${search.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch analysis runs');
    return res.json();
  },

  async triggerAnalysisRun(entityIds?: string[], datasetVersion?: string, assessmentPeriodId: string = '2026-Q2', forceRerun: boolean = false): Promise<AnalysisRun> {
    const res = await fetch(`${API_BASE}/analysis/run?assessment_period_id=${encodeURIComponent(assessmentPeriodId)}&force_rerun=${forceRerun}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        entity_ids: entityIds,
        dataset_version: datasetVersion || 'v1.0-offline',
        note: 'Supervisory Assessment Triggered via Web Console'
      })
    });
    if (!res.ok) throw new Error('Failed to trigger analysis run');
    return res.json();
  },

  // Data Quality (Section 7)
  async getDataQuality(assessmentPeriodId: string = '2026-Q2', entityId?: string): Promise<DataQualitySummary> {
    const search = new URLSearchParams({ assessment_period_id: assessmentPeriodId });
    if (entityId) search.append('entity_id', entityId);
    const res = await fetch(`${API_BASE}/analysis/data-quality?${search.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch data quality report');
    return res.json();
  },

  // Peer Benchmarking (Section 11)
  async getPeerBenchmarking(assessmentPeriodId: string = '2026-Q2'): Promise<PeerBenchmarkReport> {
    const res = await fetch(`${API_BASE}/analysis/peer-benchmarking?assessment_period_id=${encodeURIComponent(assessmentPeriodId)}`);
    if (!res.ok) throw new Error('Failed to fetch peer benchmarking report');
    return res.json();
  },

  // Operational Anomalies (Section 12)
  async getOperationalAnomalies(assessmentPeriodId: string = '2026-Q2'): Promise<AnomalySummary> {
    const res = await fetch(`${API_BASE}/analysis/anomalies?assessment_period_id=${encodeURIComponent(assessmentPeriodId)}`);
    if (!res.ok) throw new Error('Failed to fetch operational anomalies');
    return res.json();
  },

  // Negative Space (Section 10)
  async getNegativeSpace(assessmentPeriodId: string = '2026-Q2'): Promise<any> {
    const res = await fetch(`${API_BASE}/analysis/negative-space?assessment_period_id=${encodeURIComponent(assessmentPeriodId)}`);
    if (!res.ok) throw new Error('Failed to fetch negative space analysis');
    return res.json();
  },

  // Temporal Drift (Section 13)
  async getTemporalDrift(entityId?: string): Promise<TemporalTrendSummary> {
    const url = entityId ? `${API_BASE}/analysis/temporal-drift?entity_id=${encodeURIComponent(entityId)}` : `${API_BASE}/analysis/temporal-drift`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch temporal drift analytics');
    return res.json();
  },

  // Prioritized Samples (Section 15)
  async getSampleRecommendations(entityId?: string, assessmentPeriodId: string = '2026-Q2', limit: number = 25): Promise<PrioritizedSample[]> {
    const search = new URLSearchParams({ assessment_period_id: assessmentPeriodId, limit: limit.toString() });
    if (entityId) search.append('entity_id', entityId);
    const res = await fetch(`${API_BASE}/analysis/sample-recommendations?${search.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch sample recommendations');
    return res.json();
  },

  // Supervisory Report (Section 30 & 31)
  async getSupervisoryReport(runId?: string, assessmentPeriodId: string = '2026-Q2'): Promise<SupervisoryReportData> {
    const search = new URLSearchParams({ assessment_period_id: assessmentPeriodId });
    if (runId) search.append('run_id', runId);
    const res = await fetch(`${API_BASE}/analysis/report?${search.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch supervisory report');
    return res.json();
  },

  getMarkdownReportUrl(runId?: string, assessmentPeriodId: string = '2026-Q2'): string {
    const search = new URLSearchParams({ assessment_period_id: assessmentPeriodId });
    if (runId) search.append('run_id', runId);
    return `${API_BASE}/analysis/report/markdown?${search.toString()}`;
  },

  // Validation Framework (Section 21)
  async getSyntheticGroundTruthBenchmark(runId?: string): Promise<any> {
    const url = runId ? `${API_BASE}/analysis/validation-benchmark?run_id=${encodeURIComponent(runId)}` : `${API_BASE}/analysis/validation-benchmark`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch synthetic benchmark');
    return res.json();
  },

  async getExpertReviewValidation(runId?: string): Promise<ExpertReviewValidation> {
    const url = runId ? `${API_BASE}/analysis/validation/expert-review?run_id=${encodeURIComponent(runId)}` : `${API_BASE}/analysis/validation/expert-review`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch expert review validation');
    return res.json();
  },

  async submitExpertReviewLabel(payload: {
    target_type: string;
    target_id: string;
    entity_id: string;
    assessment_period_id: string;
    expert_label: string;
    severity: string;
    evidence_notes?: string;
    reviewer_name: string;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/analysis/validation/expert-labels`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Failed to submit expert label');
    return res.json();
  },

  // Ingestion
  async getIngestionBatches(): Promise<IngestionBatch[]> {
    const res = await fetch(`${API_BASE}/ingestion/batches`);
    if (!res.ok) throw new Error('Failed to fetch ingestion batches');
    return res.json();
  },

  async getIngestionBatchDetail(batchId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/ingestion/batches/${batchId}`);
    if (!res.ok) throw new Error(`Failed to fetch batch ${batchId}`);
    return res.json();
  },

  async inspectFile(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/ingestion/inspect`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error('Failed to inspect file');
    return res.json();
  },

  async uploadFile(file: File, targetCategory?: string, defaultEntityId?: string, mappingJson?: string): Promise<IngestionValidationReport> {
    const formData = new FormData();
    formData.append('file', file);
    if (targetCategory) formData.append('target_category', targetCategory);
    if (defaultEntityId) formData.append('default_entity_id', defaultEntityId);
    if (mappingJson) formData.append('column_mapping_json', mappingJson);

    const res = await fetch(`${API_BASE}/ingestion/upload`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error('Failed to upload file');
    return res.json();
  },

  // Review Queue (Section 19)
  async getReviewQueue(status?: string, priority?: string, assessmentPeriodId?: string): Promise<ReviewItem[]> {
    const search = new URLSearchParams();
    if (status) search.append('status', status);
    if (priority) search.append('priority', priority);
    if (assessmentPeriodId) search.append('assessment_period_id', assessmentPeriodId);

    const res = await fetch(`${API_BASE}/review-queue?${search.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch review queue');
    return res.json();
  },

  async updateReviewItem(reviewId: string, action: { status: string; notes?: string; assigned_reviewer?: string; action_name?: string }): Promise<ReviewItem> {
    const res = await fetch(`${API_BASE}/review-queue/${reviewId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(action)
    });
    if (!res.ok) throw new Error(`Failed to update review item ${reviewId}`);
    return res.json();
  },

  // Audit Logs & Cryptographic Integrity (Section 20)
  async getAuditLogs(limit: number = 50): Promise<AuditLog[]> {
    const res = await fetch(`${API_BASE}/audit-logs?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch audit logs');
    return res.json();
  },

  async verifyAuditIntegrity(): Promise<AuditVerificationResult> {
    const res = await fetch(`${API_BASE}/audit/verify`);
    if (!res.ok) throw new Error('Failed to verify audit trail integrity');
    return res.json();
  },

  // Synthetic Data Generator
  async generateSyntheticData(targetAlerts: number = 3200): Promise<any> {
    const res = await fetch(`${API_BASE}/synthetic/generate?target_alerts=${targetAlerts}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error('Failed to generate synthetic data');
    return res.json();
  }
};
