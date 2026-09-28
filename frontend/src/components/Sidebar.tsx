import React from 'react';
import {
  LayoutDashboard,
  Building2,
  AlertOctagon,
  Scale,
  ScanSearch,
  Activity,
  TrendingUp,
  ClipboardList,
  FileText,
  FileCheck2,
  UploadCloud,
  History,
  ShieldCheck
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  reviewCount: number;
  criticalFindingsCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  reviewCount,
  criticalFindingsCount
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Supervisory Overview', icon: LayoutDashboard },
    { id: 'entities', label: 'Entities (CSEs)', icon: Building2 },
    {
      id: 'findings',
      label: 'Supervisory Findings',
      icon: AlertOctagon,
      badge: criticalFindingsCount > 0 ? criticalFindingsCount : undefined
    },
    { id: 'peer-benchmark', label: 'Peer Benchmarking', icon: Scale },
    { id: 'negative-space', label: 'Negative Space', icon: ScanSearch },
    { id: 'anomalies', label: 'Operational Anomalies', icon: Activity },
    { id: 'trends', label: 'Temporal Drift & Trends', icon: TrendingUp },
    {
      id: 'review-queue',
      label: 'Review Queue',
      icon: ClipboardList,
      badge: reviewCount > 0 ? reviewCount : undefined
    },
    { id: 'reports', label: 'Supervisory Reports', icon: FileText },
    { id: 'audit', label: 'Tamper-Evident Audit', icon: FileCheck2 },
    { id: 'ingestion', label: 'Data Ingestion & Demo', icon: UploadCloud },
    { id: 'runs', label: 'Assessment Runs', icon: History }
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="logo-badge">SIH26157 SUPERVISORY</span>
        <h1 className="sidebar-title">SAT-SA</h1>
        <p className="sidebar-subtitle">Supervisory Analytics Tool for SOC Assessment</p>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <div
              key={item.id}
              id={`nav-${item.id}`}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
              {item.badge !== undefined && (
                <span
                  className="nav-badge"
                  style={{
                    backgroundColor: item.id === 'findings' ? 'var(--critical-bg)' : undefined,
                    color: item.id === 'findings' ? '#f87171' : undefined
                  }}
                >
                  {item.badge}
                </span>
              )}
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <ShieldCheck size={14} color="#60a5fa" />
          <strong style={{ color: 'var(--text-secondary)' }}>SIH26157 Core Engine</strong>
        </div>
        <div>Offline Deterministic Ruleset v1.0.0</div>
      </div>
    </aside>
  );
};
