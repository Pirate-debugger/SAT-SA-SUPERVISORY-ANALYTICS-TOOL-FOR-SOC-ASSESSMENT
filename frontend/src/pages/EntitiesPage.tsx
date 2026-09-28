import React, { useState, useEffect } from 'react';
import {
  Building2,
  Server,
  AlertTriangle,
  FolderMinus,
  ArrowLeft,
  ShieldAlert,
  Search,
  ExternalLink
} from 'lucide-react';
import { EntitySupervisoryCard } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';

interface EntitiesPageProps {
  entities: EntitySupervisoryCard[];
  selectedEntityId: string | null;
  onSelectEntity: (entityId: string | null) => void;
  onOpenFinding: (findingId: string) => void;
}

export const EntitiesPage: React.FC<EntitiesPageProps> = ({
  entities,
  selectedEntityId,
  onSelectEntity,
  onOpenFinding
}) => {
  const [detail, setDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (selectedEntityId) {
      setLoading(true);
      api.getEntityDetail(selectedEntityId)
        .then((res) => setDetail(res))
        .catch(console.error)
        .finally(() => setLoading(false));
    } else {
      setDetail(null);
    }
  }, [selectedEntityId]);

  const filteredEntities = entities.filter(
    (e) =>
      e.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.entity_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.sector.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // If viewing detailed entity
  if (selectedEntityId) {
    return (
      <div className="page-container">
        <button
          className="btn btn-outline btn-sm"
          onClick={() => onSelectEntity(null)}
          style={{ marginBottom: '1.25rem' }}
        >
          <ArrowLeft size={14} /> Back to Entities Directory
        </button>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}>Loading entity assessment data...</div>
        ) : detail ? (
          <div>
            {/* Entity Header Banner */}
            <div className="card" style={{ marginBottom: '1.5rem', backgroundColor: 'var(--bg-sidebar)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.35rem' }}>
                    <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>{detail.name}</h2>
                    <span className="font-mono" style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      {detail.entity_id}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    Sector: <strong>{detail.sector}</strong> | Claimed Tier: <strong>{detail.claimed_tier}</strong> | Operating Model: <strong>{detail.soc_model}</strong>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                    Supervisory Risk
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
                    <StatusBadge type="risk" value={detail.risk_level} />
                    <span className="font-mono" style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                      {detail.risk_score} / 100
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Metrics Breakdown Grid */}
            <div className="grid-3">
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Asset Telemetry Coverage</span>
                  <Server size={16} color="#60a5fa" />
                </div>
                <div className="metric-val">
                  {detail.active_reporting_assets} / {detail.monitored_asset_count}
                </div>
                <div className="metric-sub">
                  {detail.coverage_gap_pct > 0 ? (
                    <span style={{ color: detail.coverage_gap_pct > 25 ? 'var(--critical)' : 'var(--moderate)' }}>
                      ⚠️ {detail.coverage_gap_pct}% Telemetry Blind Spot
                    </span>
                  ) : (
                    <span style={{ color: 'var(--low)' }}>100% Monitored Assets Active</span>
                  )}
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <span className="card-title">Alert Volume Ingested</span>
                  <ShieldAlert size={16} color="#c084fc" />
                </div>
                <div className="metric-val">{detail.total_alerts}</div>
                <div className="metric-sub">
                  Across {Object.keys(detail.category_distribution || {}).length} attack categories
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <span className="card-title">Case Management Submissions</span>
                  <Building2 size={16} color="#22d3ee" />
                </div>
                <div className="metric-val">{detail.total_cases}</div>
                <div className="metric-sub">Documented investigations</div>
              </div>
            </div>

            {/* Supervisory Findings for this Entity */}
            <div style={{ marginBottom: '1.75rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                Operational Findings & Supervisory Gaps ({detail.findings?.length || 0})
              </h3>

              {(!detail.findings || detail.findings.length === 0) ? (
                <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                  No operational findings generated for this entity.
                </div>
              ) : (
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Category</th>
                        <th>Severity</th>
                        <th>Finding Type</th>
                        <th>Reason / Supervisory Explanation</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.findings.map((f: any) => (
                        <tr key={f.finding_id}>
                          <td><StatusBadge type="category" value={f.category} /></td>
                          <td><StatusBadge type="severity" value={f.severity} /></td>
                          <td className="font-mono" style={{ fontSize: '0.8rem', color: '#93c5fd' }}>
                            {f.finding_type}
                          </td>
                          <td style={{ fontSize: '0.825rem', maxWidth: '420px', lineHeight: 1.4 }}>
                            {f.reason}
                          </td>
                          <td>
                            <button
                              className="btn btn-outline btn-sm"
                              onClick={() => onOpenFinding(f.finding_id)}
                            >
                              Explore Evidence <ExternalLink size={12} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Asset Inventory Sample */}
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                Monitored Assets Sample ({detail.assets_sample?.length || 0} shown)
              </h3>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Asset ID</th>
                      <th>Hostname</th>
                      <th>IP Address</th>
                      <th>Criticality</th>
                      <th>Asset Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(detail.assets_sample || []).map((a: any) => (
                      <tr key={a.asset_id}>
                        <td className="font-mono" style={{ color: '#60a5fa' }}>{a.asset_id}</td>
                        <td>{a.hostname}</td>
                        <td className="font-mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          {a.ip_address || '—'}
                        </td>
                        <td><StatusBadge type="severity" value={a.criticality} /></td>
                        <td>{a.asset_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  // Directory View
  return (
    <div className="page-container">
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Critical Sector Entities (CSEs)</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Registered supervised entities, claimed security capabilities, and operational assessment scores
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', width: '280px' }}>
          <Search size={16} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search entity, ID or sector..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '0.45rem 0.75rem',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              color: 'var(--text-main)',
              fontSize: '0.85rem'
            }}
          />
        </div>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Entity ID</th>
              <th>Entity Name</th>
              <th>Sector</th>
              <th>Claimed Tier</th>
              <th>Assets (Reported/Declared)</th>
              <th>Coverage Gap</th>
              <th>Risk Level</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredEntities.map((e) => (
              <tr key={e.entity_id}>
                <td className="font-mono" style={{ color: '#60a5fa', fontWeight: 600 }}>
                  {e.entity_id}
                </td>
                <td style={{ fontWeight: 600 }}>{e.name}</td>
                <td>{e.sector}</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{e.claimed_tier}</td>
                <td>{e.active_reporting_assets} / {e.monitored_asset_count}</td>
                <td>
                  {e.coverage_gap_pct > 25 ? (
                    <span className="badge badge-negative">-{e.coverage_gap_pct}%</span>
                  ) : (
                    <span style={{ color: 'var(--low)' }}>Normal</span>
                  )}
                </td>
                <td>
                  <StatusBadge type="risk" value={e.risk_level} />
                </td>
                <td>
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={() => onSelectEntity(e.entity_id)}
                  >
                    View Assessment
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
