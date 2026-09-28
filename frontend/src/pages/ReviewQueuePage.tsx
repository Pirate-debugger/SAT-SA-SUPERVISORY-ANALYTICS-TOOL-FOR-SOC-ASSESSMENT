import React, { useState, useEffect } from 'react';
import { ClipboardList, CheckCircle2, MessageSquare, AlertCircle, ArrowUpRight, ExternalLink } from 'lucide-react';
import { ReviewItem } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';

interface ReviewQueuePageProps {
  onOpenFinding: (findingId: string) => void;
  onRefreshBadge: () => void;
}

export const ReviewQueuePage: React.FC<ReviewQueuePageProps> = ({ onOpenFinding, onRefreshBadge }) => {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState<ReviewItem | null>(null);
  const [noteText, setNoteText] = useState('');
  const [assignedReviewer, setAssignedReviewer] = useState('SUPERVISOR_LEAD');

  const loadItems = () => {
    setLoading(true);
    api.getReviewQueue()
      .then((data) => {
        setItems(data);
        onRefreshBadge();
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadItems();
  }, []);

  const handleUpdateStatus = async (reviewId: string, status: string, customNote?: string) => {
    try {
      await api.updateReviewItem(reviewId, {
        status,
        notes: customNote || undefined,
        assigned_reviewer: assignedReviewer,
        action_name: `STATUS_CHANGE_TO_${status}`
      });
      loadItems();
      setSelectedItem(null);
      setNoteText('');
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    }
  };

  return (
    <div className="page-container">
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Supervisory Review Queue</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Actionable supervisory decision queue for tracking verified gaps, investigations, and formal directives
          </p>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>Loading review queue...</div>
      ) : items.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          No open supervisory review items. Run an assessment to populate the queue.
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Priority</th>
                <th>Entity</th>
                <th>Finding ID</th>
                <th>Supervisory Reason</th>
                <th>Status</th>
                <th>Assigned Reviewer</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.review_id}>
                  <td><StatusBadge type="severity" value={item.priority} /></td>
                  <td style={{ fontWeight: 600 }}>{item.entity_id}</td>
                  <td className="font-mono" style={{ color: '#60a5fa', fontSize: '0.8rem' }}>
                    {item.finding_id}
                  </td>
                  <td style={{ fontSize: '0.825rem', maxWidth: '380px', lineHeight: 1.4 }}>
                    {item.finding_reason || 'Supervisory signal requiring manual inspection'}
                    {item.notes && (
                      <div style={{ marginTop: '0.35rem', color: '#93c5fd', fontSize: '0.75rem', fontStyle: 'italic' }}>
                        Notes: {item.notes}
                      </div>
                    )}
                  </td>
                  <td><StatusBadge type="status" value={item.status} /></td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {item.assigned_reviewer || 'Unassigned'}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <button
                        className="btn btn-outline btn-sm"
                        title="View Full Evidence"
                        onClick={() => onOpenFinding(item.finding_id)}
                      >
                        <ExternalLink size={12} />
                      </button>

                      {item.status !== 'REVIEWED' && (
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ color: '#34d399' }}
                          title="Mark Reviewed"
                          onClick={() => handleUpdateStatus(item.review_id, 'REVIEWED', 'Verified by supervisor')}
                        >
                          <CheckCircle2 size={12} /> Review
                        </button>
                      )}

                      {item.status !== 'ESCALATED' && (
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ color: '#f87171' }}
                          title="Escalate for Formal Audit"
                          onClick={() => handleUpdateStatus(item.review_id, 'ESCALATED', 'Escalated to national supervisory authority')}
                        >
                          <ArrowUpRight size={12} /> Escalate
                        </button>
                      )}

                      <button
                        className="btn btn-outline btn-sm"
                        title="Add Note"
                        onClick={() => setSelectedItem(item)}
                      >
                        <MessageSquare size={12} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Note Modal */}
      {selectedItem && (
        <div className="modal-overlay" onClick={() => setSelectedItem(null)}>
          <div className="modal-content" style={{ maxWidth: '500px' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Supervisory Review Note</h3>
            </div>
            <div className="modal-body">
              <div style={{ fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                Item: <strong>{selectedItem.finding_id}</strong> ({selectedItem.entity_id})
              </div>
              <textarea
                rows={4}
                placeholder="Enter supervisory notes or audit directive instructions..."
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  backgroundColor: 'var(--bg-app)',
                  border: '1px solid var(--border)',
                  borderRadius: '6px',
                  color: 'var(--text-main)',
                  fontSize: '0.85rem'
                }}
              />
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline btn-sm" onClick={() => setSelectedItem(null)}>
                Cancel
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => handleUpdateStatus(selectedItem.review_id, selectedItem.status, noteText)}
              >
                Save Supervisory Note
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
