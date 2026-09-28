import React, { useState, useEffect } from 'react';
import { Download, ShieldCheck, CheckCircle2, Award } from 'lucide-react';
import { api } from '../services/api';
import { SupervisoryReportData } from '../types';

interface ReportsPageProps {
  assessmentPeriodId: string;
}

export const ReportsPage: React.FC<ReportsPageProps> = ({ assessmentPeriodId }) => {
  const [report, setReport] = useState<SupervisoryReportData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        setLoading(true);
        const data = await api.getSupervisoryReport(undefined, assessmentPeriodId);
        setReport(data);
      } catch (err) {
        console.error('Failed to fetch supervisory report:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [assessmentPeriodId]);

  const handleDownloadMarkdown = () => {
    const url = api.getMarkdownReportUrl(undefined, assessmentPeriodId);
    window.open(url, '_blank');
  };

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-muted)' }}>Compiling official 18-section Supervisory Assessment Report...</p>
      </div>
    );
  }

  const meta = report?.report_metadata;
  const exec = report?.executive_summary;
  const dq = report?.data_quality_summary;
  const audit = report?.audit_chain_verification;

  return (
    <div className="page-container">
      {/* Classification Banner - Master Prompt Section 31 MANDATORY */}
      <div
        style={{
          backgroundColor: '#b91c1c',
          color: '#ffffff',
          fontWeight: 800,
          textAlign: 'center',
          padding: '0.65rem',
          borderRadius: '6px',
          letterSpacing: '0.05em',
          fontSize: '0.85rem',
          marginBottom: '1.25rem'
        }}
      >
        {meta?.classification_banner || 'DEMO / SYNTHETIC DATA — NOT FOR OPERATIONAL USE'}
      </div>

      {/* Header */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
            {meta?.report_title || 'SAT-SA Supervisory SOC Assessment Report'}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Sections 30 & 31: Canonical Supervisory Synthesis • Evidence-Backed & Tamper-Evident
          </p>
        </div>
        <button
          className="btn btn-primary btn-sm"
          onClick={handleDownloadMarkdown}
          style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
        >
          <Download size={14} />
          Download Markdown (.md)
        </button>
      </div>

      {/* Metadata Overview Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header">
          <span className="card-title">Report Metadata & Cryptographic Provenance</span>
          <ShieldCheck size={16} color="#60a5fa" />
        </div>
        <div className="grid-4" style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Period:</span>
            <div style={{ fontWeight: 600 }}>{meta?.assessment_period_id}</div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Analysis Run ID:</span>
            <div className="font-mono" style={{ fontWeight: 600, fontSize: '0.75rem' }}>{meta?.analysis_run_id}</div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Ruleset Version:</span>
            <div style={{ fontWeight: 600 }}>{meta?.ruleset_version}</div>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Audit Chain Status:</span>
            <div style={{ color: audit?.verified ? 'var(--low)' : 'var(--critical)', fontWeight: 600 }}>
              {audit?.verified ? '✓ Cryptographically Verified' : '⚠ Tamper Warning'}
            </div>
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="card" style={{ marginBottom: '1.5rem', borderLeft: '4px solid var(--primary)' }}>
        <div className="card-header">
          <span className="card-title">1. Executive Summary</span>
          <Award size={16} color="#60a5fa" />
        </div>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', margin: '0.5rem 0' }}>
          {exec?.key_takeaway}
        </p>
        <div className="grid-3" style={{ marginTop: '1rem' }}>
          <div style={{ padding: '0.75rem', backgroundColor: 'rgba(15, 23, 42, 0.5)', borderRadius: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Entities Assessed</span>
            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{exec?.total_entities_assessed}</div>
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: 'rgba(15, 23, 42, 0.5)', borderRadius: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Entities Requiring Attention</span>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f87171' }}>
              {exec?.entities_requiring_attention}
            </div>
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: 'rgba(15, 23, 42, 0.5)', borderRadius: '6px' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Critical / High Findings</span>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fbbf24' }}>
              {(exec?.critical_findings_count || 0) + (exec?.high_findings_count || 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: Data Quality Engine Summary */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header">
          <span className="card-title">2. Data Quality & Confidence Audit (Section 7)</span>
          <CheckCircle2 size={16} color="#4ade80" />
        </div>
        <div className="grid-4" style={{ marginTop: '0.75rem' }}>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Overall Quality</span>
            <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{dq?.overall_quality_pct}%</div>
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Completeness</span>
            <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{dq?.completeness?.score_pct}%</div>
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Validity (Unknowns Preserved)</span>
            <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{dq?.validity?.score_pct}%</div>
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Confidence Level</span>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--low)' }}>
              {dq?.analytical_confidence_level}
            </div>
          </div>
        </div>
      </div>

      {/* Section 3: Entity Supervisory Attention Breakdown */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">3. Entity Assessment & Supervisory Attention Ranking</span>
        </div>
        <div className="table-wrapper" style={{ marginTop: '0.75rem' }}>
          <table>
            <thead>
              <tr>
                <th>Entity / Sector</th>
                <th>Attention Indicator</th>
                <th>Attention Level</th>
                <th>Data Quality</th>
                <th>Threat Detection</th>
                <th>Investigation</th>
                <th>Escalation</th>
                <th>Discipline</th>
                <th>Findings</th>
              </tr>
            </thead>
            <tbody>
              {report?.entities_assessed?.map((e) => {
                const cap = e.capability_profile || {};
                return (
                  <tr key={e.entity_id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{e.name}</div>
                      <div className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {e.entity_id} • {e.sector}
                      </div>
                    </td>
                    <td style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                      {e.supervisory_attention_indicator}
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          e.supervisory_attention_level === 'CRITICAL'
                            ? 'badge-critical'
                            : e.supervisory_attention_level === 'HIGH'
                            ? 'badge-high'
                            : 'badge-low'
                        }`}
                      >
                        {e.supervisory_attention_level}
                      </span>
                    </td>
                    <td>{e.data_quality_pct}%</td>
                    <td>{cap['Threat Detection']?.score ?? '—'}</td>
                    <td>{cap['Investigation']?.score ?? '—'}</td>
                    <td>{cap['Escalation']?.score ?? '—'}</td>
                    <td>{cap['Operational Discipline']?.score ?? '—'}</td>
                    <td>
                      <span className="badge badge-gap">{e.findings_count}</span>
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
