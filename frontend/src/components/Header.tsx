import React from 'react';
import { ShieldCheck, Play, Database, RefreshCw } from 'lucide-react';

interface HeaderProps {
  onRunAnalysis: () => void;
  onRefresh: () => void;
  isRunningAnalysis: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onRunAnalysis, onRefresh, isRunningAnalysis }) => {
  return (
    <>
      <div className="disclaimer-banner">
        ⚠️ SYNTHETIC SOC DEMO ENVIRONMENT — ALL DATA MARKED DEMO/SYNTHETIC — AIR-GAPPED OFFLINE ASSESSMENT (SIH26157)
      </div>
      <header className="top-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div className="header-status-pill">
            <span className="status-dot"></span>
            AIR-GAPPED OFFLINE MODE
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Ruleset: <strong style={{ color: 'var(--text-secondary)' }}>v1.0.0-deterministic</strong>
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
