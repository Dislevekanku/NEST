import React, { useState } from 'react';
import axios, { AxiosRequestConfig } from 'axios';
import { CONFIG } from '../config';

const APIPlayground: React.FC = () => {
  const [selectedEndpoint, setSelectedEndpoint] = useState<string>(CONFIG.financeFeedAgent.a2a);
  const [method, setMethod] = useState<'GET' | 'POST'>('POST');
  const [requestBody, setRequestBody] = useState<string>(JSON.stringify({
    content: { text: 'what are the current stock prices?', type: 'text' },
    role: 'user',
    conversation_id: 'api-playground-test',
  }, null, 2));
  const [response, setResponse] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [responseTime, setResponseTime] = useState<number | null>(null);

  const endpoints = [
    { label: 'Finance Feed A2A', value: CONFIG.financeFeedAgent.a2a, method: 'POST' },
    { label: 'Consumer Agent A2A', value: CONFIG.consumerAgent.a2a, method: 'POST' },
    { label: 'Data Facts', value: CONFIG.financeFeedAgent.dataFacts, method: 'GET' },
    { label: 'Stock Data', value: CONFIG.financeFeedAgent.stockData, method: 'GET' },
  ];

  const handleEndpointChange = (value: string) => {
    setSelectedEndpoint(value);
    const endpoint = endpoints.find(e => e.value === value);
    if (endpoint) {
      setMethod(endpoint.method as 'GET' | 'POST');
      if (endpoint.method === 'GET') {
        setRequestBody('');
      } else {
        setRequestBody(JSON.stringify({
          content: { text: 'hello', type: 'text' },
          role: 'user',
          conversation_id: 'api-playground-test',
        }, null, 2));
      }
    }
  };

  const sendRequest = async () => {
    setIsLoading(true);
    setResponse(null);
    const startTime = Date.now();

    try {
      const config: AxiosRequestConfig = {
        method,
        url: selectedEndpoint,
        headers: { 'Content-Type': 'application/json' },
        timeout: 30000,
      };

      if (method === 'POST' && requestBody) {
        config.data = JSON.parse(requestBody);
      }

      const result = await axios(config);
      setResponseTime(Date.now() - startTime);
      setResponse({
        status: result.status,
        statusText: result.statusText,
        headers: result.headers,
        data: result.data,
      });
    } catch (error: any) {
      setResponseTime(Date.now() - startTime);
      setResponse({
        error: true,
        message: error.message,
        status: error.response?.status,
        data: error.response?.data,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="api-playground">
      <div className="card">
        <h2 className="card-title">🛠️ API Playground</h2>
        <p style={{ color: '#666', marginBottom: '1.5rem' }}>
          Test agent endpoints interactively. Build and send requests to see responses.
        </p>

        <div style={{ display: 'grid', gap: '1.5rem' }}>
          {/* Request Builder */}
          <div style={{ padding: '1.5rem', background: '#f8f9fa', borderRadius: '8px' }}>
            <h3 style={{ marginBottom: '1rem' }}>Request Builder</h3>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Endpoint</label>
              <select
                className="input"
                value={selectedEndpoint}
                onChange={(e) => handleEndpointChange(e.target.value)}
              >
                {endpoints.map(ep => (
                  <option key={ep.value} value={ep.value}>{ep.label}</option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Method</label>
              <select
                className="input"
                value={method}
                onChange={(e) => setMethod(e.target.value as 'GET' | 'POST')}
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
              </select>
            </div>

            {method === 'POST' && (
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Request Body (JSON)</label>
                <textarea
                  className="input"
                  value={requestBody}
                  onChange={(e) => setRequestBody(e.target.value)}
                  rows={8}
                  style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
                />
              </div>
            )}

            <button
              className="button"
              onClick={sendRequest}
              disabled={isLoading}
              style={{ width: '100%' }}
            >
              {isLoading ? '⏳ Sending...' : '▶ Send Request'}
            </button>
          </div>

          {/* Response Viewer */}
          <div style={{ padding: '1.5rem', background: '#f8f9fa', borderRadius: '8px' }}>
            <h3 style={{ marginBottom: '1rem' }}>Response</h3>

            {responseTime && (
              <div style={{ marginBottom: '1rem', padding: '0.75rem', background: '#e7f3ff', borderRadius: '4px' }}>
                <strong>Response Time: {responseTime}ms</strong>
              </div>
            )}

            {response ? (
              <div>
                <div style={{ marginBottom: '0.5rem' }}>
                  <span className={`badge ${response.error ? 'badge-error' : 'badge-success'}`}>
                    {response.error ? '❌ Error' : `✅ ${response.status || 'Success'}`}
                  </span>
                </div>
                <pre style={{
                  background: 'white',
                  padding: '1rem',
                  borderRadius: '4px',
                  overflow: 'auto',
                  maxHeight: '500px',
                  fontSize: '0.85rem',
                  border: '1px solid #e0e0e0',
                }}>
                  {JSON.stringify(response, null, 2)}
                </pre>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
                No response yet. Send a request to see the response here.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default APIPlayground;
