import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { CONFIG } from '../config';
import { motion } from 'framer-motion';

interface StockData {
  TSLA?: number;
  AAPL?: number;
  'ETH-USD'?: number;
  timestamp?: number;
}

interface DataFacts {
  dataset_id: string;
  dataset_description: string;
  access_type: string;
  endpoint: string;
  evidence: {
    last_updated: string;
    checksum_sha256: string;
    source: string;
  };
  ttl_seconds: number;
  update_frequency: string;
}

const StockPriceDisplay: React.FC = () => {
  const [stockData, setStockData] = useState<StockData>({});
  const [dataFacts, setDataFacts] = useState<DataFacts | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [freshnessStatus, setFreshnessStatus] = useState<'fresh' | 'stale' | 'expired'>('fresh');

  const fetchStockData = async () => {
    try {
      const response = await axios.get(CONFIG.financeFeedAgent.stockData);
      setStockData(response.data);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error fetching stock data:', error);
    }
  };

  const fetchDataFacts = async () => {
    try {
      const response = await axios.get(CONFIG.financeFeedAgent.dataFacts);
      setDataFacts(response.data);
      
      // Check freshness
      if (response.data.evidence?.last_updated) {
        const lastUpdated = new Date(response.data.evidence.last_updated);
        const ageSeconds = (new Date().getTime() - lastUpdated.getTime()) / 1000;
        const ttl = response.data.ttl_seconds || 600;
        
        if (ageSeconds <= ttl) {
          setFreshnessStatus('fresh');
        } else if (ageSeconds <= ttl * 2) {
          setFreshnessStatus('stale');
        } else {
          setFreshnessStatus('expired');
        }
      }
      
      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching data facts:', error);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDataFacts();
    fetchStockData();
    
    // Auto-refresh every 10 seconds
    const interval = setInterval(() => {
      fetchDataFacts();
      fetchStockData();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  const formatPrice = (price?: number) => {
    if (!price) return 'N/A';
    return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const getFreshnessBadge = () => {
    const styles = {
      fresh: { bg: '#d4edda', color: '#155724', icon: '🟢' },
      stale: { bg: '#fff3cd', color: '#856404', icon: '🟡' },
      expired: { bg: '#f8d7da', color: '#721c24', icon: '🔴' },
    };
    const style = styles[freshnessStatus];
    return (
      <span className="badge" style={{ background: style.bg, color: style.color }}>
        {style.icon} {freshnessStatus.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="stock-price-display">
      {/* Stock Price Cards */}
      <div className="card">
        <h2 className="card-title">📊 Live Stock Prices</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
          {(['TSLA', 'AAPL', 'ETH-USD'] as const).map((symbol) => (
            <motion.div
              key={symbol}
              className="stock-card"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              whileHover={{ scale: 1.05 }}
              style={{
                background: `linear-gradient(135deg, ${symbol === 'TSLA' ? '#e11d48' : symbol === 'AAPL' ? '#0071e3' : '#627eea'} 0%, ${symbol === 'TSLA' ? '#be185d' : symbol === 'AAPL' ? '#0066cc' : '#764ba2'} 100%)`,
                color: 'white',
                padding: '1.5rem',
                borderRadius: '12px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              }}
            >
              <div style={{ fontSize: '0.9rem', opacity: 0.9, marginBottom: '0.5rem' }}>{symbol}</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                {isLoading ? '...' : formatPrice(stockData[symbol])}
              </div>
              <div style={{ fontSize: '0.85rem', opacity: 0.8 }}>
                Updated: {lastUpdate.toLocaleTimeString()}
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Data Facts Panel */}
      <div className="card">
        <h2 className="card-title">📋 Data Facts Metadata</h2>
        {dataFacts ? (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <div style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  {dataFacts.dataset_id}
                </div>
                <div style={{ color: '#666', marginBottom: '0.5rem' }}>
                  {dataFacts.dataset_description}
                </div>
              </div>
              {getFreshnessBadge()}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.25rem' }}>Access Type</div>
                <div style={{ fontWeight: 600 }}>
                  <span className="badge badge-success">{dataFacts.access_type}</span>
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.25rem' }}>Update Frequency</div>
                <div style={{ fontWeight: 600 }}>{dataFacts.update_frequency}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.25rem' }}>TTL</div>
                <div style={{ fontWeight: 600 }}>{dataFacts.ttl_seconds} seconds</div>
              </div>
            </div>

            <div style={{ marginBottom: '1rem', padding: '1rem', background: '#f8f9fa', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.5rem' }}>Evidence</div>
              <div style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                <div>Last Updated: <strong>{new Date(dataFacts.evidence.last_updated).toLocaleString()}</strong></div>
                <div>Source: <strong>{dataFacts.evidence.source}</strong></div>
                <div>Checksum: <strong>{dataFacts.evidence.checksum_sha256.substring(0, 32)}...</strong></div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <a
                href={CONFIG.financeFeedAgent.dataFacts}
                target="_blank"
                rel="noopener noreferrer"
                className="button"
                style={{ textDecoration: 'none', display: 'inline-block' }}
              >
                🔗 Open Data Facts URL
              </a>
              <a
                href={CONFIG.financeFeedAgent.stockData}
                target="_blank"
                rel="noopener noreferrer"
                className="button"
                style={{ textDecoration: 'none', display: 'inline-block', background: '#28a745' }}
              >
                📊 Open Dataset Endpoint
              </a>
              <button
                className="button"
                onClick={() => { fetchDataFacts(); fetchStockData(); }}
                style={{ background: '#6c757d' }}
              >
                🔄 Refresh
              </button>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            {isLoading ? <div className="spinner" /> : <div>No data facts available</div>}
          </div>
        )}
      </div>
    </div>
  );
};

export default StockPriceDisplay;
