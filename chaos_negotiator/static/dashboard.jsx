import React, { useEffect, useState } from 'react';
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
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [historyRes, canaryRes] = await Promise.all([
          fetch('/api/dashboard/history'),
          fetch('/api/dashboard/canary'),
        ]);

        if (!historyRes.ok || !canaryRes.ok) {
          throw new Error('Failed to fetch dashboard data');
        }

        const [history, canary] = await Promise.all([
          historyRes.json(),
          canaryRes.json(),
        ]);

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
    const interval = setInterval(fetchDashboardData, 30000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let ws;
    let reconnectTimeout;

    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      ws = new WebSocket(`${protocol}//${window.location.host}/ws/risk`);

      ws.onopen = () => {
        setWsConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          setRiskData(JSON.parse(event.data));
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection error');
      };

      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimeout = setTimeout(connectWebSocket, 3000);
      };
    };

    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
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
        <div className="connection-status">
          <span className={`status-indicator ${wsConnected ? 'connected' : 'disconnected'}`}></span>
          <span>{wsConnected ? 'Real-time connected' : 'Connecting...'}</span>
        </div>
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
