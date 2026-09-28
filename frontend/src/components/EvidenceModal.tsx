import React, { useEffect, useState } from 'react';
import { X, ExternalLink, ShieldAlert, Clock, Database, CheckCircle2, AlertTriangle } from 'lucide-react';
import { FindingDetail } from '../types';
import { api } from '../services/api';
import { StatusBadge } from './StatusBadge';

interface EvidenceModalProps {
  findingId: string | null;
  onClose: () => void;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({ findingId, onClose }) => {
  const [detail, setDetail] = useState<FindingDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!findingId) return;
    setLoading(true);
    setError(null);
    api.getFindingDetail(findingId)
      .then((data) => setDetail(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [findingId]);

  if (!findingId) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <ShieldAlert size={20} color="#60a5fa" />
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>Supervisory Evidence Explorer</h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Deterministic Finding Traceability & Records Drill-Down
              </p>
            </div>
          </div>
          <button className="btn btn-outline btn-sm" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          {loading && <div style={{ textAlign: 'center', padding: '2rem' }}>Retrieving evidence records...</div>}
          {error && <div style={{ color: 'var(--critical)', padding: '1rem' }}>Error: {error}</div>}

          {detail && (
            <div>
              {/* Finding Title & Badges */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                <StatusBadge type="severity" value={detail.severity} />
                <StatusBadge type="category" value={detail.category} />
                <span className="font-mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {detail.finding_id}
                </span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Entity: <strong>{detail.entity_id}</strong>
                </span>
              </div>

              {/* Reason Card */}
              <div className="card" style={{ marginBottom: '1.25rem', backgroundColor: 'var(--bg-subtle)' }}>
                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Supervisory Reason & Finding Explanation
                </div>
                <div style={{ fontSize: '0.925rem', color: 'var(--text-main)', lineHeight: 1.6 }}>
                  {detail.reason}
                </div>
              </div>

              {/* Metrics & Baseline Comparison Grid */}
              <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
                <div className="card">
                  <div className="card-title">Observed Operational Metric</div>
                  {detail.metric_values ? (
                    <pre className="font-mono" style={{ fontSize: '0.8rem', color: '#93c5fd', whiteSpace: 'pre-wrap', marginTop: '0.5rem' }}>
                      {JSON.stringify(detail.metric_values, null, 2)}
                    </pre>
                  ) : (
                    <div style={{ color: 'var(--text-muted)' }}>No direct metrics object</div>
                  )}
                </div>

                <div className="card">
                  <div className="card-title">Supervisory Baseline / Threshold</div>
                  {detail.baseline ? (
                    <pre className="font-mono" style={{ fontSize: '0.8rem', color: '#facc15', whiteSpace: 'pre-wrap', marginTop: '0.5rem' }}>
                      {JSON.stringify(detail.baseline, null, 2)}
                    </pre>
                  ) : (
                    <div style={{ color: 'var(--text-muted)' }}>Baseline comparison derived from peer pool</div>
                  )}
                </div>
              </div>

              {/* Evidence Records Table */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)' }}>
                    Linked Evidence Records ({detail.evidence_records.length} sample records linked)
                  </h4>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Confidence: {(detail.confidence * 100).toFixed(0)}%
                  </span>
                </div>

                {detail.evidence_records.length === 0 ? (
                  <div style={{ padding: '1.5rem', textAlign: 'center', backgroundColor: 'var(--bg-subtle)', borderRadius: 6, color: 'var(--text-muted)' }}>
                    No specific individual record IDs linked; finding is based on aggregate absence of logs (Negative Space).
                  </div>
                ) : (
                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr>
                          <th>Record Type</th>
                          <th>Record ID</th>
                          <th>Relevance Note</th>
                          <th>Attributes / Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detail.evidence_records.map((rec, i) => (
                          <tr key={i}>
                            <td>
                              <span className="badge" style={{ backgroundColor: 'var(--bg-subtle)' }}>
                                {rec.record_type}
                              </span>
                            </td>
                            <td className="font-mono" style={{ color: '#60a5fa', fontWeight: 600 }}>
                              {rec.record_id}
                            </td>
                            <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                              {rec.relevance_note || 'Direct supporting record for supervisory deviation'}
                            </td>
                            <td>
                              {rec.details ? (
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                                  {rec.details.severity && <span>Sev: <strong>{rec.details.severity}</strong> | </span>}
                                  {rec.details.disposition && <span>Disp: <strong>{rec.details.disposition}</strong> | </span>}
                                  {rec.details.timestamp && <span>Time: {rec.details.timestamp.split('T')[0]}</span>}
                                  {rec.details.hostname && <span>Host: {rec.details.hostname}</span>}
                                  {rec.details.closure_reason && <div>Note: <em>{rec.details.closure_reason}</em></div>}
                                </div>
                              ) : (
                                <span style={{ color: 'var(--text-muted)' }}>—</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary btn-sm" onClick={onClose}>
            Close Explorer
          </button>
        </div>
      </div>
    </div>
  );
};
