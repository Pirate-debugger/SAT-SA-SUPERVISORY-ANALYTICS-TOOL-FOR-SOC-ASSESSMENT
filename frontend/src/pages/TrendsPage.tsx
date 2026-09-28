import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle, Calendar, LineChart } from 'lucide-react';
import { api } from '../services/api';
import { TemporalTrendSummary } from '../types';

export const TrendsPage: React.FC = () => {
  const [data, setData] = useState<TemporalTrendSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedEntity, setSelectedEntity] = useState<string>('ALL');

  useEffect(() => {
    const fetchTrends = async () => {
      try {
        setLoading(true);
        const res = await api.getTemporalDrift();
        setData(res);
      } catch (err) {
        console.error('Failed to fetch temporal drift:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchTrends();
  }, []);

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-muted)' }}>Analyzing multi-period assessment progression and temporal drift...</p>
      </div>
    );
  }

  const periods = data?.assessment_periods_evaluated || [];
  const profiles = data?.entity_profiles || {};
  const findings = data?.temporal_findings || [];
  const entityList = Object.keys(profiles);

  return (
    <div className="page-container">
      {/* Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Temporal Drift & Multi-Period Trends
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Section 13: Period-over-period sequence, slopes, step-change detection, and sustained deterioration
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <Calendar size={14} color="#60a5fa" />
          <span>Periods Evaluated: <strong>{periods.join(' → ') || '2025-Q4 → 2026-Q1 → 2026-Q2'}</strong></span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
        <div className="card" style={{ borderLeft: '4px solid var(--critical)' }}>
          <div className="card-header">
            <span className="card-title">Persistent Weaknesses</span>
            <AlertTriangle size={16} color="#ef4444" />
          </div>
          <div className="metric-val" style={{ color: '#f87171' }}>{findings.length}</div>
          <div className="metric-sub">Sustained multi-period degradation signals</div>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--primary)' }}>
          <div className="card-header">
            <span className="card-title">Historical Depth</span>
            <LineChart size={16} color="#60a5fa" />
          </div>
          <div className="metric-val">{periods.length} Periods</div>
          <div className="metric-sub">Multi-quarter slope tracking enabled</div>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--low)' }}>
          <div className="card-header">
            <span className="card-title">Analytical Trust</span>
            <CheckCircle size={16} color="#4ade80" />
          </div>
          <div className="metric-val" style={{ color: '#4ade80' }}>
            {data?.sufficient_data_for_trend ? 'High' : 'Moderate'}
          </div>
          <div className="metric-sub">Full period sequence evaluation (not just endpoints)</div>
        </div>
      </div>

      {/* Persistent Temporal Findings */}
      {findings.length > 0 && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-header">
            <span className="card-title">Actionable Temporal Weaknesses</span>
            <span className="badge badge-critical">{findings.length} Flagged</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.75rem' }}>
            {findings.map((f, idx) => (
              <div
                key={idx}
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.05)',
                  borderLeft: '4px solid var(--critical)',
                  padding: '0.75rem 1rem',
                  borderRadius: '4px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="font-mono" style={{ fontWeight: 700 }}>{f.entity_id}</span>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{f.reason}</span>
                  </div>
                  <span className={`badge badge-${f.severity.toLowerCase()}`}>{f.severity}</span>
                </div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  {f.evidence_summary}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Entity Trajectory Profiles Table */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="card-title">Entity Longitudinal Trajectories</span>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', fontSize: '0.8rem' }}>
            <span>Filter Entity:</span>
            <select
              value={selectedEntity}
              onChange={(e) => setSelectedEntity(e.target.value)}
              style={{
                backgroundColor: 'var(--bg-input, #1e293b)',
                color: 'var(--text-main, #f8fafc)',
                border: '1px solid var(--border-color, #334155)',
                borderRadius: '4px',
                padding: '0.2rem 0.5rem',
                fontSize: '0.8rem'
              }}
            >
              <option value="ALL">All Entities ({entityList.length})</option>
              {entityList.map((eid) => (
                <option key={eid} value={eid}>{eid}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="table-wrapper" style={{ marginTop: '1rem' }}>
          <table>
            <thead>
              <tr>
                <th>Entity ID</th>
                <th>Periods</th>
                <th>Coverage Trend</th>
                <th>Unremediated Repeats</th>
                <th>Rapid Closure Trend</th>
                <th>Overall Trajectory</th>
              </tr>
            </thead>
            <tbody>
              {entityList
                .filter((eid) => selectedEntity === 'ALL' || eid === selectedEntity)
                .map((eid) => {
                  const prof = profiles[eid];
                  const cov = prof.coverage_trend;
                  const rep = prof.unremediated_repeat_rate_trend;
                  const rap = prof.rapid_closure_rate_trend;

                  return (
                    <tr key={eid}>
                      <td className="font-mono" style={{ fontWeight: 600 }}>{eid}</td>
                      <td>{prof.periods_count}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          {cov.slope < -0.05 ? (
                            <TrendingDown size={14} color="#f87171" />
                          ) : cov.slope > 0.05 ? (
                            <TrendingUp size={14} color="#4ade80" />
                          ) : (
                            <Minus size={14} color="#94a3b8" />
                          )}
                          <span style={{ fontSize: '0.8rem' }}>
                            {cov.status} ({cov.slope > 0 ? `+${cov.slope}` : cov.slope})
                          </span>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          {rep.slope > 0.05 ? (
                            <TrendingUp size={14} color="#f87171" />
                          ) : rep.slope < -0.05 ? (
                            <TrendingDown size={14} color="#4ade80" />
                          ) : (
                            <Minus size={14} color="#94a3b8" />
                          )}
                          <span style={{ fontSize: '0.8rem' }}>
                            {rep.status}
                          </span>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          {rap.slope > 0.05 ? (
                            <TrendingUp size={14} color="#f87171" />
                          ) : rap.slope < -0.05 ? (
                            <TrendingDown size={14} color="#4ade80" />
                          ) : (
                            <Minus size={14} color="#94a3b8" />
                          )}
                          <span style={{ fontSize: '0.8rem' }}>
                            {rap.status}
                          </span>
                        </div>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            prof.overall_trajectory.includes('DETERIORATING')
                              ? 'badge-critical'
                              : prof.overall_trajectory.includes('IMPROVING')
                              ? 'badge-low'
                              : 'badge-moderate'
                          }`}
                        >
                          {prof.overall_trajectory}
                        </span>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
