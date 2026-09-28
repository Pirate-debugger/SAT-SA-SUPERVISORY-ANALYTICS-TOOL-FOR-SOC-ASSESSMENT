import React, { useState, useEffect } from 'react';
import { UploadCloud, FileText, CheckCircle, AlertOctagon, RefreshCw, Sparkles, FileCheck } from 'lucide-react';
import { IngestionBatch, IngestionValidationReport } from '../types';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';

interface IngestionPageProps {
  onRefreshAll: () => void;
}

export const IngestionPage: React.FC<IngestionPageProps> = ({ onRefreshAll }) => {
  const [batches, setBatches] = useState<IngestionBatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [inspectData, setInspectData] = useState<any | null>(null);
  const [uploadReport, setUploadReport] = useState<IngestionValidationReport | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSeedingDemo, setIsSeedingDemo] = useState(false);

  const loadBatches = () => {
    setLoading(true);
    api.getIngestionBatches()
      .then((data) => setBatches(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadBatches();
  }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setInspectData(null);
      setUploadReport(null);
      try {
        setIsProcessing(true);
        const inspected = await api.inspectFile(file);
        setInspectData(inspected);
      } catch (err: any) {
        alert(`Inspection failed: ${err.message}`);
      } finally {
        setIsProcessing(false);
      }
    }
  };

  const handleExecuteUpload = async () => {
    if (!selectedFile) return;
    try {
      setIsProcessing(true);
      const report = await api.uploadFile(selectedFile);
      setUploadReport(report);
      loadBatches();
      onRefreshAll();
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleGenerateDemoData = async () => {
    if (!confirm('Generate 5 CSE Synthetic SOC Datasets and seed the local database?')) return;
    try {
      setIsSeedingDemo(true);
      const res = await api.generateSyntheticData(3200);
      alert(`Synthetic Dataset Generated!\nEntities: ${res.entities_count}\nAlerts: ${res.alerts_count}\nCases: ${res.cases_count}\nInitial Findings: ${res.initial_findings_count || 0}`);
      loadBatches();
      onRefreshAll();
    } catch (err: any) {
      alert(`Generation failed: ${err.message}`);
    } finally {
      setIsSeedingDemo(false);
    }
  };

  return (
    <div className="page-container">
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Data Ingestion & Ingestion Safety</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Ingest heterogeneous periodic SOC logs (CSV/JSON), normalize schemas, and validate data integrity
          </p>
        </div>

        <button
          id="btn-seed-synthetic"
          className="btn btn-primary btn-sm"
          onClick={handleGenerateDemoData}
          disabled={isSeedingDemo}
          style={{ backgroundColor: '#7c3aed' }}
        >
          <Sparkles size={14} />
          {isSeedingDemo ? 'Generating Demo Dataset...' : 'Generate 5-CSE Demo Dataset'}
        </button>
      </div>

      {/* Upload & Inspection Panel */}
      <div className="grid-2" style={{ marginBottom: '1.75rem' }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">Select SOC File (CSV / JSON)</span>
            <UploadCloud size={16} color="#60a5fa" />
          </div>

          <div
            style={{
              border: '2px dashed var(--border)',
              borderRadius: '8px',
              padding: '2rem 1.5rem',
              textAlign: 'center',
              backgroundColor: 'var(--bg-app)',
              marginBottom: '1rem',
              cursor: 'pointer'
            }}
            onClick={() => document.getElementById('file-upload-input')?.click()}
          >
            <input
              id="file-upload-input"
              type="file"
              accept=".csv,.json"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
            <FileText size={32} color="#60a5fa" style={{ margin: '0 auto 0.75rem' }} />
            <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>
              {selectedFile ? selectedFile.name : 'Click to select or drop CSV / JSON SOC file'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Automatic schema detection & field normalization will execute
            </div>
          </div>

          {selectedFile && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.type || 'text/plain'}
              </span>
              <button
                id="btn-run-ingest"
                className="btn btn-primary btn-sm"
                onClick={handleExecuteUpload}
                disabled={isProcessing}
              >
                {isProcessing ? 'Ingesting...' : 'Ingest & Validate Records'}
              </button>
            </div>
          )}
        </div>

        {/* Schema Inspection Result */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Schema Detection & Field Mapping</span>
            <FileCheck size={16} color="#34d399" />
          </div>

          {!inspectData ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Select a file to preview auto-detected columns, categories, and field mapping suggestions.
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <span className="badge badge-low">{inspectData.detected_data_category} DATASET</span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Detected {inspectData.columns_detected?.length} columns in {inspectData.total_rows_detected} rows
                </span>
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                Mapped Columns:
              </div>
              <div
                style={{
                  maxHeight: '130px',
                  overflowY: 'auto',
                  backgroundColor: 'var(--bg-app)',
                  padding: '0.5rem',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontFamily: 'monospace'
                }}
              >
                {Object.entries(inspectData.suggested_mappings || {}).map(([src, tgt]) => (
                  <div key={src} style={{ color: '#93c5fd' }}>
                    {src} ➔ <strong>{tgt as string}</strong>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Ingestion Report if just uploaded */}
      {uploadReport && (
        <div className="card" style={{ marginBottom: '1.75rem', borderLeft: '4px solid var(--low)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <CheckCircle size={18} color="#10b981" />
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Ingestion Validation Safety Report</h3>
            <StatusBadge type="status" value={uploadReport.status} />
          </div>

          <div className="grid-4" style={{ marginBottom: '1rem' }}>
            <div style={{ backgroundColor: 'var(--bg-app)', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Records</div>
              <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700 }}>{uploadReport.total_records}</div>
            </div>
            <div style={{ backgroundColor: 'var(--bg-app)', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Valid Ingested</div>
              <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--low)' }}>{uploadReport.valid_records}</div>
            </div>
            <div style={{ backgroundColor: 'var(--bg-app)', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Rejected Invalid</div>
              <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: uploadReport.invalid_records ? 'var(--critical)' : 'var(--text-muted)' }}>
                {uploadReport.invalid_records}
              </div>
            </div>
            <div style={{ backgroundColor: 'var(--bg-app)', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Duplicate IDs</div>
              <div className="font-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: uploadReport.duplicate_records ? 'var(--moderate)' : 'var(--text-muted)' }}>
                {uploadReport.duplicate_records}
              </div>
            </div>
          </div>

          {uploadReport.invalid_samples?.length > 0 && (
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--critical)', marginBottom: '0.35rem' }}>
                Rejected Row Samples with Explicit Reasons:
              </div>
              <div className="table-wrapper" style={{ maxHeight: '150px' }}>
                <table>
                  <thead>
                    <tr>
                      <th>Row #</th>
                      <th>Error Type</th>
                      <th>Details / Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {uploadReport.invalid_samples.slice(0, 5).map((inv: any, idx: number) => (
                      <tr key={idx}>
                        <td>{inv.row_index}</td>
                        <td style={{ color: 'var(--critical)', fontWeight: 600 }}>{inv.error_type}</td>
                        <td className="font-mono" style={{ fontSize: '0.75rem' }}>
                          {inv.field ? `${inv.field} (val: ${inv.value})` : JSON.stringify(inv.details || inv.raw)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Past Ingestion Batches Table */}
      <div>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>
          Ingestion History & Audit Batches ({batches.length})
        </h3>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Batch ID</th>
                <th>Filename</th>
                <th>Type</th>
                <th>Status</th>
                <th>Total</th>
                <th>Valid</th>
                <th>Invalid</th>
                <th>Duplicates</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((b) => (
                <tr key={b.batch_id}>
                  <td className="font-mono" style={{ color: '#60a5fa' }}>{b.batch_id}</td>
                  <td>{b.filename}</td>
                  <td><span className="badge" style={{ backgroundColor: 'var(--bg-subtle)' }}>{b.file_type}</span></td>
                  <td><StatusBadge type="status" value={b.status} /></td>
                  <td>{b.total_records}</td>
                  <td style={{ color: 'var(--low)', fontWeight: 600 }}>{b.valid_records}</td>
                  <td style={{ color: b.invalid_records ? 'var(--critical)' : 'var(--text-muted)' }}>{b.invalid_records}</td>
                  <td style={{ color: b.duplicate_records ? 'var(--moderate)' : 'var(--text-muted)' }}>{b.duplicate_records}</td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {b.created_at ? b.created_at.replace('T', ' ').substring(0, 19) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
