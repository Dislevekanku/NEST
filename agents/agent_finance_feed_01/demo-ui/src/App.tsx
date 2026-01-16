import React, { useState } from 'react';
import './App.css';
import QueryInterface from './components/QueryInterface';
import StockPriceDisplay from './components/StockPriceDisplay';
import ArchitectureDiagram from './components/ArchitectureDiagram';
import AgentDashboard from './components/AgentDashboard';
import RegistryExplorer from './components/RegistryExplorer';
import ComparisonView from './components/ComparisonView';
import TestSuiteRunner from './components/TestSuiteRunner';
import APIPlayground from './components/APIPlayground';
import LogViewer from './components/LogViewer';
import GuidedDemo from './components/GuidedDemo';

type TabType = 'query' | 'stocks' | 'architecture' | 'dashboard' | 'registry' | 'comparison' | 'tests' | 'api' | 'logs' | 'demo';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('query');

  const tabs = [
    { id: 'query' as TabType, label: '💬 Query Interface', icon: '💬' },
    { id: 'stocks' as TabType, label: '📊 Stock Prices', icon: '📊' },
    { id: 'architecture' as TabType, label: '🏗️ Architecture', icon: '🏗️' },
    { id: 'dashboard' as TabType, label: '📈 Dashboard', icon: '📈' },
    { id: 'registry' as TabType, label: '🔍 Registry', icon: '🔍' },
    { id: 'comparison' as TabType, label: '⚖️ Compare', icon: '⚖️' },
    { id: 'tests' as TabType, label: '🧪 Tests', icon: '🧪' },
    { id: 'api' as TabType, label: '🛠️ API Playground', icon: '🛠️' },
    { id: 'logs' as TabType, label: '📋 Logs', icon: '📋' },
    { id: 'demo' as TabType, label: '🎬 Guided Demo', icon: '🎬' },
  ];

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <h1>🚀 NANDA Agent Demo</h1>
          <p className="subtitle">Finance Feed Agent & Consumer Agent - Data Facts & A2A Communication</p>
        </div>
      </header>

      <nav className="tab-navigation">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-label">{tab.label.replace(/[^\w\s]/g, '').trim()}</span>
          </button>
        ))}
      </nav>

      <main className="main-content">
        {activeTab === 'query' && <QueryInterface />}
        {activeTab === 'stocks' && <StockPriceDisplay />}
        {activeTab === 'architecture' && <ArchitectureDiagram />}
        {activeTab === 'dashboard' && <AgentDashboard />}
        {activeTab === 'registry' && <RegistryExplorer />}
        {activeTab === 'comparison' && <ComparisonView />}
        {activeTab === 'tests' && <TestSuiteRunner />}
        {activeTab === 'api' && <APIPlayground />}
        {activeTab === 'logs' && <LogViewer />}
        {activeTab === 'demo' && <GuidedDemo />}
      </main>

      <footer className="app-footer">
        <p>Finance Feed Agent: <code>54.172.251.235</code> | Consumer Agent: <code>44.223.52.126</code></p>
      </footer>
    </div>
  );
};

export default App;
