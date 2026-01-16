import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { CONFIG } from '../config';

const AgentDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState({
    financeAgent: { online: false, uptime: 0, requests: 0 },
    consumerAgent: { online: false, uptime: 0, requests: 0 },
    a2aMessages: 0,
    dataFactsRequests: 0,
    avgResponseTime: 0,
  });

  const [requestHistory, setRequestHistory] = useState<Array<{ time: string; count: number }>>([]);

  const checkAgentHealth = async () => {
    try {
      const financeHealth = await axios.get(CONFIG.financeFeedAgent.health, { timeout: 5000 });
      setMetrics(prev => ({
        ...prev,
        financeAgent: { ...prev.financeAgent, online: financeHealth.status === 200 },
      }));
    } catch {
      setMetrics(prev => ({
        ...prev,
        financeAgent: { ...prev.financeAgent, online: false },
      }));
    }

    try {
      const consumerHealth = await axios.get(CONFIG.consumerAgent.health, { timeout: 5000 });
      setMetrics(prev => ({
        ...prev,
        consumerAgent: { ...prev.consumerAgent, online: consumerHealth.status === 200 },
      }));
    } catch {
      setMetrics(prev => ({
        ...prev,
        consumerAgent: { ...prev.consumerAgent, online: false },
      }));
    }
  };

  useEffect(() => {
    checkAgentHealth();
    const interval = setInterval(checkAgentHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="agent-dashboard">
      <div className="card">
        <h2 className="card-title">📈 Live Agent Dashboard</h2>
        
        {/* Agent Status Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          <div style={{ padding: '1.5rem', background: '#f8f9fa', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ fontSize: '1.2rem', fontWeight: 600 }}>Finance Feed Agent</div>
              <span className={`badge ${metrics.financeAgent.online ? 'badge-success' : 'badge-error'}`}>
                {metrics.financeAgent.online ? '🟢 Online' : '🔴 Offline'}
              </span>
            </div>
            <div style={{ fontSize: '0.9rem', color: '#666' }}>
              <div>Endpoint: <code>{CONFIG.financeFeedAgent.a2a}</code></div>
              <div>Data Facts: <code>{CONFIG.financeFeedAgent.dataFacts}</code></div>
            </div>
          </div>

          <div style={{ padding: '1.5rem', background: '#f8f9fa', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ fontSize: '1.2rem', fontWeight: 600 }}>Consumer Agent</div>
              <span className={`badge ${metrics.consumerAgent.online ? 'badge-success' : 'badge-error'}`}>
                {metrics.consumerAgent.online ? '🟢 Online' : '🔴 Offline'}
              </span>
            </div>
            <div style={{ fontSize: '0.9rem', color: '#666' }}>
              <div>Endpoint: <code>{CONFIG.consumerAgent.a2a}</code></div>
              <div>Discovers agents via registry</div>
            </div>
          </div>
        </div>

        {/* Metrics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div style={{ padding: '1rem', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{metrics.a2aMessages}</div>
            <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>A2A Messages</div>
          </div>
          <div style={{ padding: '1rem', background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{metrics.dataFactsRequests}</div>
            <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>Data Facts Requests</div>
          </div>
          <div style={{ padding: '1rem', background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', color: 'white', borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{metrics.avgResponseTime}ms</div>
            <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>Avg Response Time</div>
          </div>
        </div>

        <button
          className="button"
          onClick={checkAgentHealth}
          style={{ marginTop: '1.5rem', background: '#6c757d' }}
        >
          🔄 Refresh Status
        </button>
      </div>
    </div>
  );
};

export default AgentDashboard;
