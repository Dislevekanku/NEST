import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { CONFIG } from '../config';
import { motion } from 'framer-motion';

interface AgentInfo {
  agent_id: string;
  agent_name?: string;
  agent_url?: string;
  data_facts_url?: string;
  [key: string]: any;
}

const RegistryExplorer: React.FC = () => {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null);

  const fetchAgents = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(CONFIG.registry.list, { timeout: 10000 });
      const agentList = Array.isArray(response.data) ? response.data : response.data.agents || [];
      
      // Filter for finance/consumer agents or show all
      const filteredAgents = agentList.filter((agent: AgentInfo) => 
        agent.agent_id?.toLowerCase().includes('finance') ||
        agent.agent_id?.toLowerCase().includes('consumer') ||
        agent.data_facts_url
      );
      
      setAgents(filteredAgents.length > 0 ? filteredAgents : agentList.slice(0, 10));
    } catch (error: any) {
      console.error('Error fetching agents:', error);
      // Show mock data for demo
      setAgents([
        {
          agent_id: 'finance-feed-agent',
          agent_name: 'Finance Feed Agent',
          agent_url: CONFIG.financeFeedAgent.a2a,
          data_facts_url: CONFIG.financeFeedAgent.dataFacts,
        },
        {
          agent_id: 'data-consumer-agent',
          agent_name: 'Data Consumer Agent',
          agent_url: CONFIG.consumerAgent.a2a,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  return (
    <div className="registry-explorer">
      <div className="card">
        <h2 className="card-title">🔍 Registry Explorer</h2>
        <p style={{ color: '#666', marginBottom: '1rem' }}>
          Browse agents registered in the NANDA registry and discover available datasets.
        </p>

        <button className="button" onClick={fetchAgents} style={{ marginBottom: '1.5rem', background: '#6c757d' }}>
          🔄 Refresh Agent List
        </button>

        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div className="spinner" />
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {agents.map((agent, index) => (
              <motion.div
                key={agent.agent_id || index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="agent-card"
                onClick={() => setSelectedAgent(selectedAgent?.agent_id === agent.agent_id ? null : agent)}
                style={{
                  padding: '1.5rem',
                  border: '2px solid',
                  borderColor: selectedAgent?.agent_id === agent.agent_id ? '#667eea' : '#e0e0e0',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  background: selectedAgent?.agent_id === agent.agent_id ? '#f0f4ff' : 'white',
                  transition: 'all 0.3s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                  <div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                      {agent.agent_name || agent.agent_id}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#666', fontFamily: 'monospace' }}>
                      ID: {agent.agent_id}
                    </div>
                  </div>
                  {agent.data_facts_url && (
                    <span className="badge badge-info">📊 Has Data Facts</span>
                  )}
                </div>

                {agent.agent_url && (
                  <div style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
                    <strong>A2A URL:</strong> <code style={{ fontSize: '0.85rem' }}>{agent.agent_url}</code>
                  </div>
                )}

                {selectedAgent?.agent_id === agent.agent_id && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #e0e0e0' }}
                  >
                    <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                      <strong>Full Metadata:</strong>
                    </div>
                    <pre style={{
                      background: '#f8f9fa',
                      padding: '1rem',
                      borderRadius: '4px',
                      overflow: 'auto',
                      fontSize: '0.85rem',
                      maxHeight: '300px',
                    }}>
                      {JSON.stringify(agent, null, 2)}
                    </pre>
                    {agent.data_facts_url && (
                      <a
                        href={agent.data_facts_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="button"
                        style={{
                          marginTop: '1rem',
                          textDecoration: 'none',
                          display: 'inline-block',
                        }}
                      >
                        🔗 View Data Facts
                      </a>
                    )}
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
        )}

        {agents.length === 0 && !isLoading && (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
            No agents found in registry
          </div>
        )}
      </div>
    </div>
  );
};

export default RegistryExplorer;
