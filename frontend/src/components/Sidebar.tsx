import React from 'react';
import {
  LayoutDashboard,
  Building2,
  AlertOctagon,
  ClipboardList,
  UploadCloud,
  History,
  ShieldAlert,
  FileCheck2
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
    {
      id: 'review-queue',
      label: 'Review Queue',
      icon: ClipboardList,
      badge: reviewCount > 0 ? reviewCount : undefined
    },
    { id: 'ingestion', label: 'Data Ingestion & Demo', icon: UploadCloud },
    { id: 'runs', label: 'Assessment Runs', icon: History },
    { id: 'audit', label: 'Audit Trail', icon: FileCheck2 }
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="logo-badge">SIH26157 PROTOTYPE</span>
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
                <span className="nav-badge" style={{ backgroundColor: item.id === 'findings' ? 'var(--critical-bg)' : undefined, color: item.id === 'findings' ? '#f87171' : undefined }}>
                  {item.badge}
                </span>
              )}
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <ShieldAlert size={14} color="#60a5fa" />
          <strong style={{ color: 'var(--text-secondary)' }}>Phase 1 Foundation</strong>
        </div>
        <div>Offline Deterministic Ruleset Active</div>
      </div>
    </aside>
  );
};
