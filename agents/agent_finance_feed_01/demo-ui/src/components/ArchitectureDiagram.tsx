import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ComponentInfo {
  id: string;
  name: string;
  description: string;
  endpoints?: string[];
  details?: string;
}

const ArchitectureDiagram: React.FC = () => {
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);
  const [animatedFlow, setAnimatedFlow] = useState<string | null>(null);

  const components: Record<string, ComponentInfo> = {
    registry: {
      id: 'registry',
      name: 'Registry',
      description: 'Central agent discovery service',
      endpoints: ['http://registry.chat39.com:6900/list'],
      details: 'Stores agent metadata including agent_id, agent_url, and data_facts_url. Agents register themselves and others can discover them.',
    },
    consumer: {
      id: 'consumer',
      name: 'Consumer Agent',
      description: 'Data consumer agent',
      endpoints: ['http://44.223.52.126:6001/a2a'],
      details: 'Discovers agents via registry, reads Data Facts, accesses datasets, and communicates via A2A protocol.',
    },
    finance: {
      id: 'finance',
      name: 'Finance Feed Agent',
      description: 'Stock price data provider',
      endpoints: [
        'http://54.172.251.235:6000/a2a',
        'http://54.172.251.235:8000/data_facts/public_stock_ticker.json',
        'http://54.172.251.235:8000/stock_data',
      ],
      details: 'Provides real-time stock prices via Data Facts endpoint and A2A communication. Exposes TSLA, AAPL, and ETH-USD prices.',
    },
  };

  const flows = [
    { id: 'discovery', from: 'consumer', to: 'registry', label: 'Registry Discovery', color: '#007bff' },
    { id: 'a2a', from: 'consumer', to: 'finance', label: 'A2A Communication', color: '#28a745' },
    { id: 'datafacts', from: 'consumer', to: 'finance', label: 'Data Facts Access', color: '#ffc107' },
    { id: 'dataset', from: 'consumer', to: 'finance', label: 'Dataset Access', color: '#dc3545' },
  ];

  const runFlowAnimation = (flowId: string) => {
    setAnimatedFlow(flowId);
    setTimeout(() => setAnimatedFlow(null), 3000);
  };

  return (
    <div className="architecture-diagram">
      <div className="card">
        <h2 className="card-title">🏗️ Interactive Architecture Diagram</h2>
        <p style={{ color: '#666', marginBottom: '1.5rem' }}>
          Click on components to see details. Click flow buttons to see animated communication paths.
        </p>

        {/* Flow Controls */}
        <div style={{ marginBottom: '2rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {flows.map(flow => (
            <button
              key={flow.id}
              className="button"
              onClick={() => runFlowAnimation(flow.id)}
              style={{
                background: flow.color,
                fontSize: '0.85rem',
                padding: '0.5rem 1rem',
              }}
            >
              ▶ {flow.label}
            </button>
          ))}
          <button
            className="button"
            onClick={() => {
              flows.forEach((flow, i) => {
                setTimeout(() => runFlowAnimation(flow.id), i * 1000);
              });
            }}
            style={{
              background: '#6c757d',
              fontSize: '0.85rem',
              padding: '0.5rem 1rem',
            }}
          >
            ▶ Run All Flows
          </button>
        </div>

        {/* Diagram */}
        <div style={{ position: 'relative', minHeight: '500px', background: '#f8f9fa', borderRadius: '12px', padding: '2rem' }}>
          <svg width="100%" height="500" style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}>
            {/* Flow arrows */}
            {flows.map(flow => {
              const fromComp = components[flow.from];
              const toComp = components[flow.to];
              const fromX = fromComp.id === 'consumer' ? 150 : fromComp.id === 'registry' ? 400 : 650;
              const fromY = 250;
              const toX = toComp.id === 'consumer' ? 150 : toComp.id === 'registry' ? 400 : 650;
              const toY = 250;

              const isActive = animatedFlow === flow.id;
              
              return (
                <motion.g
                  key={flow.id}
                  initial={{ opacity: 0.3 }}
                  animate={{ opacity: isActive ? 1 : 0.3 }}
                  transition={{ duration: 0.5 }}
                >
                  <motion.path
                    d={`M ${fromX + 100} ${fromY} Q ${(fromX + toX) / 2} ${fromY - 50} ${toX} ${toY}`}
                    stroke={flow.color}
                    strokeWidth={isActive ? 4 : 2}
                    fill="none"
                    strokeDasharray={isActive ? '0' : '5,5'}
                    initial={{ pathLength: 0 }}
                    animate={isActive ? { pathLength: 1 } : {}}
                    transition={{ duration: 1.5, repeat: isActive ? Infinity : 0 }}
                  />
                  <motion.circle
                    cx={fromX + 100}
                    cy={fromY}
                    r={5}
                    fill={flow.color}
                    animate={isActive ? { scale: [1, 1.5, 1], opacity: [1, 0.5, 1] } : {}}
                    transition={{ duration: 1, repeat: isActive ? Infinity : 0 }}
                  />
                </motion.g>
              );
            })}
          </svg>

          {/* Components */}
          <div style={{ position: 'relative', display: 'flex', justifyContent: 'space-around', alignItems: 'center', height: '100%' }}>
            {Object.values(components).map((comp) => {
              const x = comp.id === 'consumer' ? 50 : comp.id === 'registry' ? 350 : 650;
              const isSelected = selectedComponent === comp.id;

              return (
                <motion.div
                  key={comp.id}
                  className="architecture-component"
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: isSelected ? 1.1 : 1, opacity: 1 }}
                  whileHover={{ scale: 1.05 }}
                  onClick={() => setSelectedComponent(isSelected ? null : comp.id)}
                  style={{
                    width: '200px',
                    padding: '1.5rem',
                    background: isSelected ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'white',
                    color: isSelected ? 'white' : '#333',
                    borderRadius: '12px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    border: isSelected ? '3px solid #667eea' : '2px solid #e0e0e0',
                    zIndex: isSelected ? 10 : 1,
                  }}
                >
                  <div style={{ fontSize: '2rem', marginBottom: '0.5rem', textAlign: 'center' }}>
                    {comp.id === 'registry' ? '📋' : comp.id === 'consumer' ? '🔄' : '📊'}
                  </div>
                  <div style={{ fontWeight: 600, marginBottom: '0.25rem', textAlign: 'center' }}>
                    {comp.name}
                  </div>
                  <div style={{ fontSize: '0.85rem', opacity: 0.8, textAlign: 'center' }}>
                    {comp.description}
                  </div>
                  {isSelected && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.3)' }}
                    >
                      <div style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>{comp.details}</div>
                      {comp.endpoints && (
                        <div>
                          <div style={{ fontSize: '0.75rem', opacity: 0.9, marginBottom: '0.25rem' }}>Endpoints:</div>
                          {comp.endpoints.map((endpoint, i) => (
                            <div key={i} style={{ fontSize: '0.7rem', fontFamily: 'monospace', marginBottom: '0.25rem', wordBreak: 'break-all' }}>
                              {endpoint}
                            </div>
                          ))}
                        </div>
                      )}
                    </motion.div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Flow Legend */}
        <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
          <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Flow Types:</div>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            {flows.map(flow => (
              <div key={flow.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ width: '30px', height: '2px', background: flow.color }} />
                <span style={{ fontSize: '0.9rem' }}>{flow.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ArchitectureDiagram;
