import {
  DashboardSummary,
  EntitySupervisoryCard,
  Finding,
  FindingDetail,
  AnalysisRun,
  IngestionBatch,
  IngestionValidationReport,
  ReviewItem,
  AuditLog
} from '../types';

const API_BASE = '/api';

export const api = {
  // System status
  async getStatus(): Promise<any> {
    const res = await fetch(`${API_BASE}/status`);
    if (!res.ok) throw new Error('Failed to fetch system status');
    return res.json();
  },

  // Dashboard summary
  async getDashboardSummary(): Promise<DashboardSummary> {
    const res = await fetch(`${API_BASE}/dashboard/summary`);
    if (!res.ok) throw new Error('Failed to fetch dashboard summary');
    return res.json();
  },

  // Entities
  async getEntities(): Promise<EntitySupervisoryCard[]> {
    const res = await fetch(`${API_BASE}/entities`);
    if (!res.ok) throw new Error('Failed to fetch entities');
    return res.json();
  },

  async getEntityDetail(entityId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/entities/${entityId}`);
    if (!res.ok) throw new Error(`Failed to fetch entity ${entityId}`);
    return res.json();
  },

  // Findings & Evidence
  async getFindings(params?: { entity_id?: string; category?: string; severity?: string }): Promise<Finding[]> {
    const search = new URLSearchParams();
    if (params?.entity_id) search.append('entity_id', params.entity_id);
    if (params?.category) search.append('category', params.category);
    if (params?.severity) search.append('severity', params.severity);

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
  async getAnalysisRuns(): Promise<AnalysisRun[]> {
    const res = await fetch(`${API_BASE}/analysis/runs`);
    if (!res.ok) throw new Error('Failed to fetch analysis runs');
    return res.json();
  },

  async triggerAnalysisRun(entityIds?: string[], datasetVersion?: string): Promise<AnalysisRun> {
    const res = await fetch(`${API_BASE}/analysis/run`, {
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

  // Review Queue
  async getReviewQueue(status?: string, priority?: string): Promise<ReviewItem[]> {
    const search = new URLSearchParams();
    if (status) search.append('status', status);
    if (priority) search.append('priority', priority);

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

  // Audit Logs
  async getAuditLogs(limit: number = 50): Promise<AuditLog[]> {
    const res = await fetch(`${API_BASE}/audit-logs?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch audit logs');
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
