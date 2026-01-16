import React, { useState } from 'react';
import axios from 'axios';
import { CONFIG } from '../config';
import { motion } from 'framer-motion';

const ComparisonView: React.FC = () => {
  const [a2aResult, setA2aResult] = useState<any>(null);
  const [dataFactsResult, setDataFactsResult] = useState<any>(null);
  const [a2aLoading, setA2aLoading] = useState(false);
  const [dataFactsLoading, setDataFactsLoading] = useState(false);
  const [a2aTime, setA2aTime] = useState<number | null>(null);
  const [dataFactsTime, setDataFactsTime] = useState<number | null>(null);

  const testA2A = async () => {
    setA2aLoading(true);
    const startTime = Date.now();
    try {
      const response = await axios.post(
        CONFIG.consumerAgent.a2a,
        {
          content: { text: 'what are the current stock prices?', type: 'text' },
          role: 'user',
          conversation_id: `comparison-a2a-${Date.now()}`,
        },
        { timeout: 30000 }
      );
      const endTime = Date.now();
      setA2aTime(endTime - startTime);
      setA2aResult(response.data);
    } catch (error: any) {
      setA2aResult({ error: error.message });
    } finally {
      setA2aLoading(false);
    }
  };

  const testDataFacts = async () => {
    setDataFactsLoading(true);
    const startTime = Date.now();
    try {
      const dataFactsResponse = await axios.get(CONFIG.financeFeedAgent.dataFacts);
      const datasetResponse = await axios.get(dataFactsResponse.data.endpoint);
      const endTime = Date.now();
      setDataFactsTime(endTime - startTime);
      setDataFactsResult({
        dataFacts: dataFactsResponse.data,
        dataset: datasetResponse.data,
      });
    } catch (error: any) {
      setDataFactsResult({ error: error.message });
    } finally {
      setDataFactsLoading(false);
    }
  };

  return (
    <div className="comparison-view">
      <div className="card">
        <h2 className="card-title">⚖️ A2A vs Data Facts Comparison</h2>
        <p style={{ color: '#666', marginBottom: '1.5rem' }}>
          Compare both communication methods side-by-side to see their differences and use cases.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          {/* A2A Panel */}
          <div style={{ border: '2px solid #28a745', borderRadius: '8px', padding: '1.5rem' }}>
            <h3 style={{ color: '#28a745', marginBottom: '1rem' }}>🟢 A2A Communication</h3>
            <div style={{ marginBottom: '1rem' }}>
              <button className="button" onClick={testA2A} disabled={a2aLoading} style={{ background: '#28a745', width: '100%' }}>
                {a2aLoading ? '⏳ Testing...' : '▶ Test A2A'}
              </button>
            </div>

            {a2aTime && (
              <div style={{ marginBottom: '1rem', padding: '0.75rem', background: '#d4edda', borderRadius: '4px' }}>
                <strong>Response Time: {a2aTime}ms</strong>
              </div>
            )}

            <div style={{ marginBottom: '1rem' }}>
              <strong>Use Cases:</strong>
              <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                <li>Real-time queries and conversations</li>
                <li>Complex multi-turn interactions</li>
                <li>Agent-to-agent collaboration</li>
              </ul>
            </div>

            {a2aResult && (
              <div style={{ marginTop: '1rem', padding: '1rem', background: '#f8f9fa', borderRadius: '4px', maxHeight: '300px', overflow: 'auto' }}>
                <strong>Response:</strong>
                <pre style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
                  {JSON.stringify(a2aResult, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Data Facts Panel */}
          <div style={{ border: '2px solid #ffc107', borderRadius: '8px', padding: '1.5rem' }}>
            <h3 style={{ color: '#856404', marginBottom: '1rem' }}>🟡 Data Facts Access</h3>
            <div style={{ marginBottom: '1rem' }}>
              <button className="button" onClick={testDataFacts} disabled={dataFactsLoading} style={{ background: '#ffc107', color: '#333', width: '100%' }}>
                {dataFactsLoading ? '⏳ Testing...' : '▶ Test Data Facts'}
              </button>
            </div>

            {dataFactsTime && (
              <div style={{ marginBottom: '1rem', padding: '0.75rem', background: '#fff3cd', borderRadius: '4px' }}>
                <strong>Response Time: {dataFactsTime}ms</strong>
              </div>
            )}

            <div style={{ marginBottom: '1rem' }}>
              <strong>Use Cases:</strong>
              <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                <li>Direct dataset access</li>
                <li>Metadata discovery</li>
                <li>Bulk data retrieval</li>
              </ul>
            </div>

            {dataFactsResult && (
              <div style={{ marginTop: '1rem', padding: '1rem', background: '#f8f9fa', borderRadius: '4px', maxHeight: '300px', overflow: 'auto' }}>
                <strong>Response:</strong>
                <pre style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
                  {JSON.stringify(dataFactsResult, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Comparison Table */}
        <div style={{ marginTop: '2rem', padding: '1.5rem', background: '#f8f9fa', borderRadius: '8px' }}>
          <h3 style={{ marginBottom: '1rem' }}>Comparison Matrix</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#e9ecef' }}>
                <th style={{ padding: '0.75rem', textAlign: 'left', border: '1px solid #dee2e6' }}>Feature</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', border: '1px solid #dee2e6' }}>A2A Communication</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', border: '1px solid #dee2e6' }}>Data Facts</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>Protocol</td>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>A2A (Agent-to-Agent)</td>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>REST API</td>
              </tr>
              <tr style={{ background: '#f8f9fa' }}>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>Interaction Type</td>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>Conversational</td>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>Direct Access</td>
              </tr>
              <tr>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>Best For</td>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>Queries, Q&A, Agent Collaboration</td>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>Dataset Discovery, Metadata, Bulk Data</td>
              </tr>
              <tr style={{ background: '#f8f9fa' }}>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>Response Format</td>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>Natural Language</td>
                <td style={{ padding: '0.75rem', border: '1px solid #dee2e6' }}>Structured JSON</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ComparisonView;
