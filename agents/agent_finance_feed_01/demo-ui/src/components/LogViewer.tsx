import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';

interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'INFO' | 'WARN' | 'ERROR';
  source: 'finance' | 'consumer' | 'system';
  message: string;
}

const LogViewer: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<{ level?: string; source?: string }>({});
  const [search, setSearch] = useState('');

  // Simulated log generation (in real app, these would come from WebSocket or API)
  useEffect(() => {
    const interval = setInterval(() => {
      const newLog: LogEntry = {
        id: Date.now().toString(),
        timestamp: new Date(),
        level: ['INFO', 'WARN', 'ERROR'][Math.floor(Math.random() * 3)] as 'INFO' | 'WARN' | 'ERROR',
        source: Math.random() > 0.5 ? 'finance' : 'consumer',
        message: [
          'A2A message received',
          'Data Facts fetched successfully',
          'Registry query completed',
          'Stock data updated',
          'Checksum verified',
          'Freshness check passed',
        ][Math.floor(Math.random() * 6)],
      };
      setLogs(prev => [newLog, ...prev].slice(0, 100)); // Keep last 100 logs
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const filteredLogs = logs.filter(log => {
    if (filter.level && log.level !== filter.level) return false;
    if (filter.source && log.source !== filter.source) return false;
    if (search && !log.message.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR': return '#dc3545';
      case 'WARN': return '#ffc107';
      default: return '#28a745';
    }
  };

  return (
    <div className="log-viewer">
      <div className="card">
        <h2 className="card-title">📋 Log Viewer</h2>
        <p style={{ color: '#666', marginBottom: '1rem' }}>
          Real-time log stream from both agents with filtering and search capabilities.
        </p>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '200px' }}>
            <input
              type="text"
              className="input"
              placeholder="Search logs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            className="input"
            style={{ width: '150px' }}
            value={filter.level || ''}
            onChange={(e) => setFilter({ ...filter, level: e.target.value || undefined })}
          >
            <option value="">All Levels</option>
            <option value="INFO">INFO</option>
            <option value="WARN">WARN</option>
            <option value="ERROR">ERROR</option>
          </select>
          <select
            className="input"
            style={{ width: '150px' }}
            value={filter.source || ''}
            onChange={(e) => setFilter({ ...filter, source: e.target.value || undefined })}
          >
            <option value="">All Sources</option>
            <option value="finance">Finance Agent</option>
            <option value="consumer">Consumer Agent</option>
            <option value="system">System</option>
          </select>
          <button
            className="button"
            onClick={() => { setFilter({}); setSearch(''); }}
            style={{ background: '#6c757d' }}
          >
            Clear Filters
          </button>
        </div>

        {/* Logs */}
        <div style={{
          height: '500px',
          overflowY: 'auto',
          border: '1px solid #e0e0e0',
          borderRadius: '8px',
          background: '#1e1e1e',
          color: '#d4d4d4',
          fontFamily: 'monospace',
          fontSize: '0.85rem',
          padding: '1rem',
        }}>
          {filteredLogs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#888' }}>
              No logs match the current filters
            </div>
          ) : (
            filteredLogs.map((log) => (
              <div
                key={log.id}
                style={{
                  padding: '0.5rem 0',
                  borderBottom: '1px solid #333',
                  display: 'flex',
                  gap: '1rem',
                }}
              >
                <span style={{ color: '#888', minWidth: '80px' }}>
                  {format(log.timestamp, 'HH:mm:ss')}
                </span>
                <span style={{
                  color: getLevelColor(log.level),
                  minWidth: '60px',
                  fontWeight: 600,
                }}>
                  {log.level}
                </span>
                <span style={{ color: '#4ec9b0', minWidth: '100px' }}>
                  [{log.source}]
                </span>
                <span style={{ flex: 1 }}>{log.message}</span>
              </div>
            ))
          )}
        </div>

        <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: '0.9rem', color: '#666' }}>
            Showing {filteredLogs.length} of {logs.length} logs
          </div>
          <button
            className="button"
            onClick={() => setLogs([])}
            style={{ background: '#6c757d', padding: '0.5rem 1rem', fontSize: '0.9rem' }}
          >
            Clear Logs
          </button>
        </div>
      </div>
    </div>
  );
};

export default LogViewer;
