import React from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  FolderMinus,
  CheckCircle,
  Building2,
  FileSearch,
  ArrowRight
} from 'lucide-react';
import { DashboardSummary, EntitySupervisoryCard } from '../types';
import { StatusBadge } from '../components/StatusBadge';

interface DashboardPageProps {
  summary: DashboardSummary | null;
  entities: EntitySupervisoryCard[];
  onSelectEntity: (entityId: string) => void;
  onViewFindings: (category?: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  summary,
  entities,
  onSelectEntity,
  onViewFindings
}) => {
  return (
    <div className="page-container">
      {/* Page Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Supervisory SOC Assessment Overview
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Multi-Entity Operational Assessment • Execution Gaps & Negative Space Detection
          </p>
        </div>
        {summary?.latest_run_id && (
          <div style={{ textAlign: 'right', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Latest Assessment: <strong className="font-mono" style={{ color: 'var(--text-secondary)' }}>{summary.latest_run_id}</strong>
          </div>
        )}
      </div>

      {/* Primary KPI Grid */}
      <div className="grid-4">
        <div className="card" style={{ borderLeft: '4px solid var(--primary)' }}>
          <div className="card-header">
            <span className="card-title">Entities Monitored</span>
            <Building2 size={16} color="#60a5fa" />
          </div>
          <div className="metric-val">{summary?.total_entities || 0}</div>
          <div className="metric-sub">
            <strong style={{ color: summary?.entities_requiring_attention ? 'var(--critical)' : 'var(--low)' }}>
              {summary?.entities_requiring_attention || 0}
            </strong> requiring supervisory review
          </div>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--critical)' }}>
          <div className="card-header">
            <span className="card-title">High-Risk Findings</span>
            <ShieldAlert size={16} color="#ef4444" />
          </div>
          <div className="metric-val" style={{ color: '#f87171' }}>
            {summary?.high_risk_findings || 0}
          </div>
          <div className="metric-sub">Critical operational vulnerabilities</div>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--gap-accent)' }}>
          <div className="card-header">
            <span className="card-title">Execution Gaps</span>
            <AlertTriangle size={16} color="#c084fc" />
          </div>
          <div className="metric-val" style={{ color: '#c084fc' }}>
            {summary?.execution_gaps_count || 0}
          </div>
          <div className="metric-sub">Rapid closure, no escalation, metrics gaming</div>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--negative-accent)' }}>
          <div className="card-header">
            <span className="card-title">Negative Space</span>
            <FolderMinus size={16} color="#22d3ee" />
          </div>
          <div className="metric-val" style={{ color: '#22d3ee' }}>
            {summary?.negative_space_count || 0}
          </div>
          <div className="metric-sub">Asset silence & missing attack signatures</div>
        </div>
      </div>

      {/* Critical Attention Banner if entities require intervention */}
      {(summary?.entities_requiring_attention || 0) > 0 && (
        <div
          style={{
            backgroundColor: 'var(--critical-bg)',
            border: '1px solid var(--critical-border)',
            borderRadius: '8px',
            padding: '1rem 1.25rem',
            marginBottom: '1.75rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <ShieldAlert size={20} color="#ef4444" />
            <div>
              <strong style={{ color: '#f87171', fontSize: '0.9rem' }}>
                Operational Warning: {summary?.entities_requiring_attention} CSEs exhibit critical supervisory risk
              </strong>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                Operational telemetry demonstrates significant execution gaps and negative space deviations requiring immediate supervisory audit.
              </div>
            </div>
          </div>
          <button className="btn btn-outline btn-sm" onClick={() => onViewFindings()}>
            Review All Findings
          </button>
        </div>
      )}

      {/* Entity Supervisory Risk Ranking Table */}
      <div style={{ marginBottom: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Entity Supervisory Assessment Ranking</h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Ranked by Weighted Supervisory Evidence Risk Score
          </span>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Entity / CSE</th>
                <th>Sector</th>
                <th>Claimed Tier</th>
                <th>Telemetry Coverage</th>
                <th>Execution Gaps</th>
                <th>Negative Space</th>
                <th>Risk Level</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {entities.map((e) => (
                <tr key={e.entity_id}>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{e.name}</div>
                    <div className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {e.entity_id}
                    </div>
                  </td>
                  <td>{e.sector}</td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{e.claimed_tier}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '0.8rem' }}>
                        {e.active_reporting_assets}/{e.monitored_asset_count}
                      </span>
                      {e.coverage_gap_pct > 25 && (
                        <span className="badge badge-negative" style={{ fontSize: '0.65rem' }}>
                          -{e.coverage_gap_pct}% gap
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    {e.execution_gaps_count > 0 ? (
                      <span className="badge badge-gap">{e.execution_gaps_count} Gaps</span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>0</span>
                    )}
                  </td>
                  <td>
                    {e.negative_space_count > 0 ? (
                      <span className="badge badge-negative">{e.negative_space_count} Silent</span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>0</span>
                    )}
                  </td>
                  <td>
                    <StatusBadge type="risk" value={e.risk_level} />
                    <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      ({e.risk_score})
                    </span>
                  </td>
                  <td>
                    <button
                      className="btn btn-outline btn-sm"
                      onClick={() => onSelectEntity(e.entity_id)}
                      style={{ fontSize: '0.75rem' }}
                    >
                      Audit Entity <ArrowRight size={12} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
