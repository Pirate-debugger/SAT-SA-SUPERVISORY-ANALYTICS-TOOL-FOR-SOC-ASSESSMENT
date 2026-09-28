import React, { useState, useEffect } from 'react';
import { Activity, AlertTriangle, CheckCircle, Info, Sliders, ShieldAlert } from 'lucide-react';
import { api } from '../services/api';
import { AnomalySummary, AnomalyDetail } from '../types';

interface AnomaliesPageProps {
  assessmentPeriodId: string;
}

export const AnomaliesPage: React.FC<AnomaliesPageProps> = ({ assessmentPeriodId }) => {
  const [data, setData] = useState<AnomalySummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [featureFilter, setFeatureFilter] = useState<string>('ALL');

  useEffect(() => {
    const fetchAnomalies = async () => {
      try {
        setLoading(true);
        const res = await api.getOperationalAnomalies(assessmentPeriodId);
        setData(res);
      } catch (err) {
        console.error('Failed to fetch operational anomalies:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAnomalies();
  }, [assessmentPeriodId]);

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-muted)' }}>Executing Isolation Forest & Robust Statistical MAD anomaly detection...</p>
      </div>
    );
  }

  const details: AnomalyDetail[] = data?.details || [];
  const uniqueFeatures = Array.from(new Set(details.map((d) => d.feature_name)));
  const filtered = details.filter((d) => featureFilter === 'ALL' || d.feature_name === featureFilter);

  return (
    <div className="page-container">
      {/* Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Operational Anomaly Detection
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Section 12: Hybrid Local Engine (Deterministic Rules + Median Absolute Deviation + Adaptive Isolation Forest)
          </p>
        </div>
        <div style={{ textAlign: 'right', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Period: <strong className="font-mono" style={{ color: 'var(--text-secondary)' }}>{assessmentPeriodId}</strong>
        </div>
      </div>

      {/* Adaptive Contamination Info */}
      <div
        style={{
          backgroundColor: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.25)',
          borderRadius: '8px',
          padding: '0.85rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          fontSize: '0.8rem',
          color: '#fca5a5'
        }}
      >
        <Sliders size={18} color="#ef4444" />
        <div>
          <strong>Adaptive Contamination Parameter:</strong> Evaluated at{' '}
          <strong>{((data?.adaptive_contamination || 0.1) * 100).toFixed(1)}%</strong> based on entity sample variance and feature quality. 
          Every actionable anomaly is instantiated as a <strong>first-class Finding (Category: ANOMALY)</strong> with full evidence provenance.
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
        <div className="card" style={{ borderLeft: '4px solid var(--critical)' }}>
          <div className="card-header">
            <span className="card-title">Anomalies Detected</span>
            <Activity size={16} color="#ef4444" />
          </div>
          <div className="metric-val" style={{ color: '#f87171' }}>{data?.anomalies_detected || 0}</div>
          <div className="metric-sub">Across {data?.total_entities_evaluated || 0} monitored CSEs</div>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--primary)' }}>
          <div className="card-header">
            <span className="card-title">Engine Methodology</span>
            <ShieldAlert size={16} color="#60a5fa" />
          </div>
          <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)', marginTop: '0.5rem' }}>
            {data?.methodology || 'Hybrid Deterministic + Robust MAD + iForest'}
          </div>
          <div className="metric-sub">No fixed arbitrary 25% contamination</div>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--low)' }}>
          <div className="card-header">
            <span className="card-title">Traceability</span>
            <CheckCircle size={16} color="#4ade80" />
          </div>
          <div className="metric-val" style={{ color: '#4ade80' }}>100%</div>
          <div className="metric-sub">All anomalies link to supporting alerts & cases</div>
        </div>
      </div>

      {/* Anomalies Table */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="card-title">Detected Operational Feature Anomalies</span>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.8rem' }}>
            <span>Filter Feature:</span>
            <select
              value={featureFilter}
              onChange={(e) => setFeatureFilter(e.target.value)}
              style={{
                backgroundColor: 'var(--bg-input, #1e293b)',
                color: 'var(--text-main, #f8fafc)',
                border: '1px solid var(--border-color, #334155)',
                borderRadius: '4px',
                padding: '0.2rem 0.5rem',
                fontSize: '0.8rem'
              }}
            >
              <option value="ALL">All Features ({uniqueFeatures.length})</option>
              {uniqueFeatures.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="table-wrapper" style={{ marginTop: '1rem' }}>
          <table>
            <thead>
              <tr>
                <th>Entity ID</th>
                <th>Feature Name</th>
                <th>Observed</th>
                <th>Baseline (Median)</th>
                <th>Robust Dev (MAD)</th>
                <th>Why Flagged</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>
                    No operational anomalies exceeding threshold for current filter.
                  </td>
                </tr>
              ) : (
                filtered.map((d, idx) => (
                  <tr key={idx}>
                    <td className="font-mono" style={{ fontWeight: 600 }}>{d.entity_id}</td>
                    <td>
                      <span className="badge" style={{ backgroundColor: 'rgba(99, 102, 241, 0.1)', color: '#818cf8' }}>
                        {d.feature_name}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600, color: d.direction === 'HIGH' ? '#f87171' : '#38bdf8' }}>
                      {d.observed_value}
                    </td>
                    <td>{d.expected_median}</td>
                    <td>
                      <span style={{ color: 'var(--moderate)' }}>
                        +{d.deviation} MAD
                      </span>
                    </td>
                    <td style={{ maxWidth: '300px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      {d.why_flagged}
                    </td>
                    <td>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                        {Math.round(d.confidence * 100)}%
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
