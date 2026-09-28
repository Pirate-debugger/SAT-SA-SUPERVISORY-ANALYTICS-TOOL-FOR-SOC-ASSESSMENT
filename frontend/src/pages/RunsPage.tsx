import React, { useState, useEffect } from 'react';
import { History, Play, CheckCircle, Clock } from 'lucide-react';
import { AnalysisRun } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';

interface RunsPageProps {
  onRunAnalysis: () => void;
  isRunningAnalysis: boolean;
}

export const RunsPage: React.FC<RunsPageProps> = ({ onRunAnalysis, isRunningAnalysis }) => {
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [loading, setLoading] = useState(false);

  const loadRuns = () => {
    setLoading(true);
    api.getAnalysisRuns()
      .then((data) => setRuns(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRuns();
  }, []);

  return (
    <div className="page-container">
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Supervisory Assessment Runs</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Historical record of all offline analytical executions, ruleset versions, and deterministic findings
          </p>
        </div>

        <button
          className="btn btn-primary btn-sm"
          onClick={onRunAnalysis}
          disabled={isRunningAnalysis}
        >
          <Play size={14} />
          {isRunningAnalysis ? 'Executing Assessment...' : 'Trigger New Assessment'}
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>Loading assessment run records...</div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Timestamp</th>
                <th>Ruleset Version</th>
                <th>Dataset Version</th>
                <th>Entities Evaluated</th>
                <th>Alerts Ingested</th>
                <th>Findings Created</th>
                <th>Execution Time</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.run_id}>
                  <td className="font-mono" style={{ color: '#60a5fa', fontWeight: 600 }}>
                    {r.run_id}
                  </td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {r.timestamp ? r.timestamp.replace('T', ' ').substring(0, 19) : '—'}
                  </td>
                  <td className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {r.ruleset_version}
                  </td>
                  <td style={{ fontSize: '0.8rem' }}>{r.dataset_version}</td>
                  <td>{r.entities_analyzed_count}</td>
                  <td>{r.alerts_analyzed_count}</td>
                  <td style={{ fontWeight: 600, color: r.findings_count > 0 ? '#f87171' : 'var(--low)' }}>
                    {r.findings_count}
                  </td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {r.execution_time_seconds}s
                  </td>
                  <td><StatusBadge type="status" value={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
