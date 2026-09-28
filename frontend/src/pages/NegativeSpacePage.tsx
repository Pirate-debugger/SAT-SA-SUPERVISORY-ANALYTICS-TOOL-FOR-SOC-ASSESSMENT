import React, { useState, useEffect } from 'react';
import { ScanSearch, Info, EyeOff, Radio } from 'lucide-react';
import { api } from '../services/api';

interface NegativeSpacePageProps {
  assessmentPeriodId: string;
}

export const NegativeSpacePage: React.FC<NegativeSpacePageProps> = ({ assessmentPeriodId }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedEntity, setSelectedEntity] = useState<string>('ALL');

  useEffect(() => {
    const fetchNegativeSpace = async () => {
      try {
        setLoading(true);
        const res = await api.getNegativeSpace(assessmentPeriodId);
        setData(res);
      } catch (err) {
        console.error('Failed to fetch negative space analysis:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchNegativeSpace();
  }, [assessmentPeriodId]);

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-muted)' }}>Executing context-aware Negative Space Expectation Engine...</p>
      </div>
    );
  }

  const byEntity = data?.negative_space_by_entity || {};
  const entityList = Object.keys(byEntity);
  const totalFindings = Object.values(byEntity).reduce((acc: number, list: any) => acc + (list?.length || 0), 0);

  return (
    <div className="page-container">
      {/* Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Negative Space & Coverage Gaps
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Section 10: Expectation Engine detecting critical asset silence, missing threat categories, and suppressed activity
          </p>
        </div>
        <div style={{ textAlign: 'right', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Period: <strong className="font-mono" style={{ color: 'var(--text-secondary)' }}>{assessmentPeriodId}</strong>
        </div>
      </div>

      {/* Epistemological Banner */}
      <div
        style={{
          backgroundColor: 'rgba(34, 211, 238, 0.1)',
          border: '1px solid rgba(34, 211, 238, 0.3)',
          borderRadius: '8px',
          padding: '0.85rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          fontSize: '0.8rem',
          color: '#67e8f9'
        }}
      >
        <Info size={18} color="#22d3ee" />
        <div>
          <strong>Analytical Principle:</strong> Absence of telemetry is not proof of compromise or security. 
          Signals are categorized as <strong>POTENTIAL NEGATIVE SPACE</strong> or <strong>MONITORING COVERAGE GAP</strong> rather than unverified assertions.
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
        <div className="card" style={{ borderLeft: '4px solid var(--negative-accent)' }}>
          <div className="card-header">
            <span className="card-title">Negative Space Signals</span>
            <ScanSearch size={16} color="#22d3ee" />
          </div>
          <div className="metric-val" style={{ color: '#22d3ee' }}>{totalFindings}</div>
          <div className="metric-sub">Across {data?.total_entities_evaluated || 0} monitored entities</div>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--critical)' }}>
          <div className="card-header">
            <span className="card-title">Silent Critical Assets</span>
            <EyeOff size={16} color="#ef4444" />
          </div>
          <div className="metric-val" style={{ color: '#f87171' }}>
            {Object.values(byEntity).flat().filter((f: any) => f.finding_type === 'CRITICAL_ASSET_SILENCE').length}
          </div>
          <div className="metric-sub">Tier-1 core banking / SCADA assets zero-reporting</div>
        </div>

        <div className="card" style={{ borderLeft: '4px solid var(--moderate)' }}>
          <div className="card-header">
            <span className="card-title">Missing Threat Signatures</span>
            <Radio size={16} color="#fbbf24" />
          </div>
          <div className="metric-val" style={{ color: '#fbbf24' }}>
            {Object.values(byEntity).flat().filter((f: any) => f.finding_type === 'EXPECTED_THREAT_CATEGORY_ABSENCE').length}
          </div>
          <div className="metric-sub">Expected MITRE tactics absent from active telemetry</div>
        </div>
      </div>

      {/* Findings Breakdown by Entity */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="card-title">Entity Expectation Models</span>
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

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          {entityList
            .filter((eid) => selectedEntity === 'ALL' || eid === selectedEntity)
            .map((eid) => {
              const findings = byEntity[eid] || [];
              if (findings.length === 0) {
                return (
                  <div key={eid} style={{ padding: '0.85rem 1rem', border: '1px solid var(--border-color)', borderRadius: '6px', opacity: 0.7 }}>
                    <strong className="font-mono">{eid}</strong>: Expected monitoring coverage intact. No anomalous negative space detected.
                  </div>
                );
              }

              return (
                <div key={eid} style={{ border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span className="font-mono" style={{ fontWeight: 700, fontSize: '0.95rem' }}>{eid}</span>
                      <span className="badge badge-negative">{findings.length} Signals</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {findings.map((f: any, idx: number) => (
                      <div
                        key={idx}
                        style={{
                          backgroundColor: 'rgba(15, 23, 42, 0.6)',
                          borderLeft: `3px solid ${f.severity === 'CRITICAL' ? 'var(--critical)' : 'var(--moderate)'}`,
                          padding: '0.75rem 1rem',
                          borderRadius: '4px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                          <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{f.reason}</span>
                          <span className={`badge badge-${f.severity.toLowerCase()}`}>{f.severity}</span>
                        </div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
                          {f.evidence_summary}
                        </p>
                        <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {f.observed_value && <span>Observed: {JSON.stringify(f.observed_value)}</span>}
                          {f.expected_value && <span>Expected: {JSON.stringify(f.expected_value)}</span>}
                        </div>
                        {f.recommended_review_area && (
                          <div style={{ marginTop: '0.4rem', fontSize: '0.75rem', color: '#93c5fd' }}>
                            Action: {f.recommended_review_area}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
        </div>
      </div>
    </div>
  );
};
