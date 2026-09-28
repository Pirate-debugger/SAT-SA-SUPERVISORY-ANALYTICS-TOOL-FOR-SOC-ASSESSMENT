import React, { useState, useEffect } from 'react';
import { Scale, Users, AlertCircle, Info, CheckCircle2, TrendingUp, TrendingDown } from 'lucide-react';
import { api } from '../services/api';
import { PeerBenchmarkReport } from '../types';

interface PeerBenchmarkPageProps {
  assessmentPeriodId: string;
}

export const PeerBenchmarkPage: React.FC<PeerBenchmarkPageProps> = ({ assessmentPeriodId }) => {
  const [report, setReport] = useState<PeerBenchmarkReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedGroup, setSelectedGroup] = useState<string>('ALL');

  useEffect(() => {
    const fetchPeerData = async () => {
      try {
        setLoading(true);
        const data = await api.getPeerBenchmarking(assessmentPeriodId);
        setReport(data);
      } catch (err) {
        console.error('Failed to fetch peer benchmarking:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchPeerData();
  }, [assessmentPeriodId]);

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-muted)' }}>Evaluating robust peer cohort statistics...</p>
      </div>
    );
  }

  const peerGroups = report?.peer_groups || {};
  const entityComparisons = report?.entity_comparisons || {};
  const groupKeys = Object.keys(peerGroups);

  return (
    <div className="page-container">
      {/* Page Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            Peer Cohort Benchmarking (Robust Statistics)
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Section 11: Median, Median Absolute Deviation (MAD), & Interquartile Range (IQR) across Sector/Tier Cohorts
          </p>
        </div>
        <div style={{ textAlign: 'right', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Period: <strong className="font-mono" style={{ color: 'var(--text-secondary)' }}>{assessmentPeriodId}</strong>
        </div>
      </div>

      {/* Methodology banner */}
      <div
        style={{
          backgroundColor: 'rgba(30, 58, 138, 0.2)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          borderRadius: '8px',
          padding: '0.85rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          fontSize: '0.8rem',
          color: '#93c5fd'
        }}
      >
        <Info size={18} color="#60a5fa" />
        <div>
          <strong>Statistical Rigor:</strong> Global pooled averages have been replaced with sector and tier-specific peer cohorts. 
          To prevent outlier contamination, baselines use <strong>Median & MAD</strong> rather than Gaussian mean. Differences are classified as supervisory signals, not automatic anomalies.
        </div>
      </div>

      {/* Cohort Summary Cards */}
      <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
        {groupKeys.map((gk) => {
          const pg = peerGroups[gk];
          return (
            <div
              key={gk}
              className="card"
              style={{
                cursor: 'pointer',
                border: selectedGroup === gk ? '1px solid var(--primary)' : '1px solid var(--border-color)',
                backgroundColor: selectedGroup === gk ? 'rgba(37, 99, 235, 0.05)' : undefined
              }}
              onClick={() => setSelectedGroup(gk === selectedGroup ? 'ALL' : gk)}
            >
              <div className="card-header">
                <span className="card-title font-mono">{gk}</span>
                <Users size={16} color="#60a5fa" />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <span className="metric-val">{pg.sample_size}</span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>entities in cohort</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: pg.sufficient_sample ? 'var(--low)' : 'var(--moderate)' }}>
                {pg.sufficient_sample ? '✓ Statistically Viable (N ≥ 3)' : '⚠ Limited Sample Size (N < 3)'}
              </div>
              <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Members: {pg.members.join(', ')}
              </div>
            </div>
          );
        })}
      </div>

      {/* Entity Peer Deviations Table */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header">
          <span className="card-title">Entity Deviations vs Peer Cohort Medians</span>
          <Scale size={16} color="#c084fc" />
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Entity ID</th>
                <th>Peer Cohort</th>
                <th>Sample (N)</th>
                <th>Closure Time vs Median</th>
                <th>Escalation Rate vs Median</th>
                <th>Repeat Rate vs Median</th>
                <th>Deviations Flagged</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(entityComparisons)
                .filter(([_, ec]) => selectedGroup === 'ALL' || ec.peer_group_id === selectedGroup)
                .map(([eid, ec]) => {
                  const mClose = ec.metrics['closure_duration_seconds'];
                  const mEsc = ec.metrics['escalation_rate'];
                  const mRep = ec.metrics['repeat_alert_rate'];

                  return (
                    <tr key={eid}>
                      <td className="font-mono" style={{ fontWeight: 600 }}>{eid}</td>
                      <td>
                        <span className="badge" style={{ backgroundColor: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa' }}>
                          {ec.peer_group_id}
                        </span>
                      </td>
                      <td>
                        {ec.sufficient_sample ? (
                          <span style={{ color: 'var(--low)', fontSize: '0.8rem' }}>N={ec.peer_sample_size}</span>
                        ) : (
                          <span style={{ color: 'var(--moderate)', fontSize: '0.8rem' }}>N={ec.peer_sample_size} (Low)</span>
                        )}
                      </td>
                      <td>
                        {mClose ? (
                          <div>
                            <span style={{ fontWeight: 600 }}>{mClose.entity_value}s</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: '0.4rem' }}>
                              (Med: {mClose.peer_median}s)
                            </span>
                            {mClose.status === 'DEVIATION_LOW' && (
                              <div style={{ color: '#f87171', fontSize: '0.7rem' }}>⚠ Suspiciously Rapid</div>
                            )}
                          </div>
                        ) : '—'}
                      </td>
                      <td>
                        {mEsc ? (
                          <div>
                            <span style={{ fontWeight: 600 }}>{mEsc.entity_value}%</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: '0.4rem' }}>
                              (Med: {mEsc.peer_median}%)
                            </span>
                            {mEsc.status === 'DEVIATION_LOW' && (
                              <div style={{ color: '#f87171', fontSize: '0.7rem' }}>⚠ Low Escalation</div>
                            )}
                          </div>
                        ) : '—'}
                      </td>
                      <td>
                        {mRep ? (
                          <div>
                            <span style={{ fontWeight: 600 }}>{mRep.entity_value}%</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: '0.4rem' }}>
                              (Med: {mRep.peer_median}%)
                            </span>
                            {mRep.status === 'DEVIATION_HIGH' && (
                              <div style={{ color: '#f87171', fontSize: '0.7rem' }}>⚠ Elevated Repeats</div>
                            )}
                          </div>
                        ) : '—'}
                      </td>
                      <td>
                        {ec.supervisory_deviations_count > 0 ? (
                          <span className="badge badge-gap">
                            {ec.supervisory_deviations_count} Deviations
                          </span>
                        ) : (
                          <span style={{ color: 'var(--low)', fontSize: '0.8rem' }}>Within Normal Range</span>
                        )}
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
