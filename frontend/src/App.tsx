import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { EvidenceModal } from './components/EvidenceModal';
import { DashboardPage } from './pages/DashboardPage';
import { EntitiesPage } from './pages/EntitiesPage';
import { FindingsPage } from './pages/FindingsPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { IngestionPage } from './pages/IngestionPage';
import { RunsPage } from './pages/RunsPage';
import { AuditPage } from './pages/AuditPage';
import { DashboardSummary, EntitySupervisoryCard } from './types';
import { api } from './services/api';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [entities, setEntities] = useState<EntitySupervisoryCard[]>([]);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [activeFindingId, setActiveFindingId] = useState<string | null>(null);
  const [reviewCount, setReviewCount] = useState<number>(0);
  const [isRunningAnalysis, setIsRunningAnalysis] = useState<boolean>(false);

  const fetchGlobalData = async () => {
    try {
      const [sum, ents, reviews] = await Promise.all([
        api.getDashboardSummary(),
        api.getEntities(),
        api.getReviewQueue('OPEN')
      ]);
      setSummary(sum);
      setEntities(ents);
      setReviewCount(reviews.length);
    } catch (err) {
      console.error('Failed to fetch dashboard metrics:', err);
    }
  };

  useEffect(() => {
    fetchGlobalData();
  }, []);

  const handleRunAnalysis = async () => {
    try {
      setIsRunningAnalysis(true);
      const res = await api.triggerAnalysisRun();
      alert(`Assessment Run Completed!\nRun ID: ${res.run_id}\nEntities Evaluated: ${res.entities_analyzed_count}\nFindings Generated: ${res.findings_count}\nDuration: ${res.execution_time_seconds}s`);
      await fetchGlobalData();
    } catch (err: any) {
      alert(`Assessment run error: ${err.message}`);
    } finally {
      setIsRunningAnalysis(false);
    }
  };

  const handleSelectEntity = (entityId: string | null) => {
    setSelectedEntityId(entityId);
    setActiveTab('entities');
  };

  const handleOpenFinding = (findingId: string) => {
    setActiveFindingId(findingId);
  };

  return (
    <div className="app-container">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          if (tab !== 'entities') setSelectedEntityId(null);
          setActiveTab(tab);
        }}
        reviewCount={reviewCount}
        criticalFindingsCount={summary?.high_risk_findings || 0}
      />

      <div className="main-content">
        <Header
          onRunAnalysis={handleRunAnalysis}
          onRefresh={fetchGlobalData}
          isRunningAnalysis={isRunningAnalysis}
        />

        {activeTab === 'dashboard' && (
          <DashboardPage
            summary={summary}
            entities={entities}
            onSelectEntity={handleSelectEntity}
            onViewFindings={(category) => {
              setActiveTab('findings');
            }}
          />
        )}

        {activeTab === 'entities' && (
          <EntitiesPage
            entities={entities}
            selectedEntityId={selectedEntityId}
            onSelectEntity={setSelectedEntityId}
            onOpenFinding={handleOpenFinding}
          />
        )}

        {activeTab === 'findings' && (
          <FindingsPage
            onOpenFinding={handleOpenFinding}
          />
        )}

        {activeTab === 'review-queue' && (
          <ReviewQueuePage
            onOpenFinding={handleOpenFinding}
            onRefreshBadge={fetchGlobalData}
          />
        )}

        {activeTab === 'ingestion' && (
          <IngestionPage
            onRefreshAll={fetchGlobalData}
          />
        )}

        {activeTab === 'runs' && (
          <RunsPage
            onRunAnalysis={handleRunAnalysis}
            isRunningAnalysis={isRunningAnalysis}
          />
        )}

        {activeTab === 'audit' && (
          <AuditPage />
        )}
      </div>

      {/* Global Drill-Down Evidence Modal */}
      <EvidenceModal
        findingId={activeFindingId}
        onClose={() => setActiveFindingId(null)}
      />
    </div>
  );
};

export default App;
