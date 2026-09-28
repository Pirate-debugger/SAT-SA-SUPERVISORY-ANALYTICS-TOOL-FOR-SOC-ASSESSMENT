import React from 'react';
import { Play, RefreshCw, Calendar, ShieldCheck } from 'lucide-react';
import { AssessmentPeriodInfo } from '../types';

interface HeaderProps {
  onRunAnalysis: () => void;
  onRefresh: () => void;
  isRunningAnalysis: boolean;
  periods?: AssessmentPeriodInfo[];
  selectedPeriod: string;
  onSelectPeriod: (periodId: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  onRunAnalysis,
  onRefresh,
  isRunningAnalysis,
  periods = [],
  selectedPeriod,
  onSelectPeriod
}) => {
  return (
    <>
      <div className="disclaimer-banner">
        ⚠️ DEMO / SYNTHETIC DATA — NOT FOR OPERATIONAL USE • AIR-GAPPED OFFLINE SUPERVISORY ASSESSMENT (SIH26157)
      </div>
      <header className="top-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div className="header-status-pill">
            <span className="status-dot"></span>
            AIR-GAPPED OFFLINE MODE
          </div>

          {/* Assessment Period Selector (Section 34) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem' }}>
            <Calendar size={14} color="#60a5fa" />
            <span style={{ color: 'var(--text-muted)' }}>Period:</span>
            <select
              value={selectedPeriod}
              onChange={(e) => onSelectPeriod(e.target.value)}
              style={{
                backgroundColor: 'var(--bg-input, #1e293b)',
                color: 'var(--text-main, #f8fafc)',
                border: '1px solid var(--border-color, #334155)',
                borderRadius: '4px',
                padding: '0.2rem 0.5rem',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {periods.length > 0 ? (
                periods.map((p) => (
                  <option key={p.period_id} value={p.period_id}>
                    {p.name || p.period_id} {p.is_active ? '(Active)' : ''}
                  </option>
                ))
              ) : (
                <>
                  <option value="2026-Q2">2026-Q2 (Active Period)</option>
                  <option value="2026-Q1">2026-Q1</option>
                  <option value="2025-Q4">2025-Q4</option>
                </>
              )}
            </select>
          </div>

          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Ruleset: <strong style={{ color: 'var(--text-secondary)' }}>v1.0.0-canonical</strong>
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            id="btn-refresh-data"
            className="btn btn-outline btn-sm"
            onClick={onRefresh}
            title="Refresh current metrics"
          >
            <RefreshCw size={14} />
            Refresh
          </button>

          <button
            id="btn-trigger-analysis"
            className="btn btn-primary btn-sm"
            onClick={onRunAnalysis}
            disabled={isRunningAnalysis}
          >
            <Play size={14} />
            {isRunningAnalysis ? 'Analyzing...' : 'Run Assessment'}
          </button>
        </div>
      </header>
    </>
  );
};
