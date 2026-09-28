import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, FolderMinus, Filter, ExternalLink, Search } from 'lucide-react';
import { Finding } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';

interface FindingsPageProps {
  onOpenFinding: (findingId: string) => void;
  initialCategory?: string;
}

export const FindingsPage: React.FC<FindingsPageProps> = ({ onOpenFinding, initialCategory }) => {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<string>(initialCategory || 'ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const loadFindings = () => {
    setLoading(true);
    api.getFindings()
      .then((data) => setFindings(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadFindings();
  }, []);

  const filtered = findings.filter((f) => {
    if (categoryFilter !== 'ALL' && f.category !== categoryFilter) return false;
    if (severityFilter !== 'ALL' && f.severity !== severityFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        f.finding_type.toLowerCase().includes(q) ||
        f.entity_id.toLowerCase().includes(q) ||
        f.reason.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="page-container">
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Supervisory Findings & Weaknesses</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Explainable supervisory deviations detected across ingested operational SOC datasets
          </p>
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={{
              padding: '0.45rem 0.75rem',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              color: 'var(--text-main)',
              fontSize: '0.85rem'
            }}
          >
            <option value="ALL">All Categories</option>
            <option value="EXECUTION_GAP">Execution Gaps</option>
            <option value="NEGATIVE_SPACE">Negative Space</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            style={{
              padding: '0.45rem 0.75rem',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              color: 'var(--text-main)',
              fontSize: '0.85rem'
            }}
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
          </select>

          <input
            type="text"
            placeholder="Search findings..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: '0.45rem 0.75rem',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              color: 'var(--text-main)',
              fontSize: '0.85rem',
              width: '200px'
            }}
          />
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>Loading findings...</div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Finding ID</th>
                <th>Entity</th>
                <th>Category</th>
                <th>Severity</th>
                <th>Confidence</th>
                <th>Reason / Operational Weakness</th>
                <th>Evidence Link</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No findings match the selected filter criteria.
                  </td>
                </tr>
              ) : (
                filtered.map((f) => (
                  <tr key={f.finding_id}>
                    <td className="font-mono" style={{ color: '#60a5fa', fontWeight: 600 }}>
                      {f.finding_id}
                    </td>
                    <td style={{ fontWeight: 600 }}>{f.entity_id}</td>
                    <td><StatusBadge type="category" value={f.category} /></td>
                    <td><StatusBadge type="severity" value={f.severity} /></td>
                    <td className="font-mono" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      {(f.confidence * 100).toFixed(0)}%
                    </td>
                    <td style={{ fontSize: '0.825rem', maxWidth: '440px', lineHeight: 1.4 }}>
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
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
