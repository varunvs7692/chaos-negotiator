import React, { useState, useEffect } from 'react';
import './dashboard.css';
import RiskCard from './components/RiskCard';
import CanaryTimeline from './components/CanaryTimeline';
import HistoryTable from './components/HistoryTable';
import ContractSummary from './components/ContractSummary';

export default function Dashboard() {
  const [riskData, setRiskData] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [canaryData, setCanaryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [riskRes, historyRes, canaryRes] = await Promise.all([
          fetch('/api/dashboard/risk'),
          fetch('/api/dashboard/history'),
          fetch('/api/dashboard/canary'),
        ]);

        if (!riskRes.ok || !historyRes.ok || !canaryRes.ok) {
          throw new Error('Failed to fetch dashboard data');
        }

        const [risk, history, canary] = await Promise.all([
          riskRes.json(),
          historyRes.json(),
          canaryRes.json(),
        ]);

        setRiskData(risk);
        setHistoryData(history);
        setCanaryData(canary);
        setError(null);
      } catch (err) {
        setError(err.message);
        console.error('Dashboard fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000); // Refresh every 10s

    return () => clearInterval(interval);
  }, []);

  if (loading && !riskData) {
    return (
      <div className="dashboard-container">
        <div className="loading">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>🚀 Chaos Negotiator Dashboard</h1>
        <p>Intelligent Deployment Risk & Reliability Management</p>
      </header>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      <div className="dashboard-grid">
        {/* Top Row: Risk Assessment */}
        <section className="dashboard-section full-width">
          <h2>Risk Assessment & Confidence</h2>
          {riskData && <RiskCard data={riskData} />}
        </section>

        {/* Middle Row: Canary Strategy */}
        <section className="dashboard-section full-width">
          <h2>Canary Deployment Strategy</h2>
          {canaryData && <CanaryTimeline data={canaryData} />}
        </section>

        {/* Bottom Row: Contract & History */}
        <section className="dashboard-section half-width">
          <h2>Guardrail Summary</h2>
          {canaryData && <ContractSummary data={canaryData} />}
        </section>

        <section className="dashboard-section half-width">
          <h2>Recent Deployment History</h2>
          {historyData && <HistoryTable data={historyData} />}
        </section>
      </div>

      <footer className="dashboard-footer">
        <p>Last updated: {new Date().toLocaleTimeString()}</p>
      </footer>
    </div>
  );
}
