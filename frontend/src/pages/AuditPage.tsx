import React, { useState, useEffect } from 'react';
import { FileCheck2, ShieldCheck, User } from 'lucide-react';
import { AuditLog } from '../types';
import { api } from '../services/api';

export const AuditPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.getAuditLogs(100)
      .then((data) => setLogs(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-container">
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Supervisory Audit Trail</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Tamper-evident chronological audit logs recording data ingestion, analytic runs, and reviewer actions
        </p>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>Loading audit logs...</div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Timestamp (UTC)</th>
                <th>Action</th>
                <th>Entity Target</th>
                <th>Actor</th>
                <th>Details Payload</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td className="font-mono" style={{ color: 'var(--text-muted)' }}>#{log.id}</td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {log.timestamp ? log.timestamp.replace('T', ' ').substring(0, 19) : '—'}
                  </td>
                  <td>
                    <span className="badge" style={{ backgroundColor: 'var(--primary-subtle)', color: '#93c5fd' }}>
                      {log.action}
                    </span>
                  </td>
                  <td>{log.entity_id || 'SYSTEM'}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}>
                      <User size={12} color="var(--text-muted)" />
                      {log.actor}
                    </div>
                  </td>
                  <td className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', maxWidth: '400px' }}>
                    {log.details ? JSON.stringify(log.details) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
