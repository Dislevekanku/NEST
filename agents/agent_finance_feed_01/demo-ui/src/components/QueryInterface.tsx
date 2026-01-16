import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { CONFIG } from '../config';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
  step?: string;
}

interface FlowStep {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  data?: any;
}

const QueryInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [flowSteps, setFlowSteps] = useState<FlowStep[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const addMessage = (role: 'user' | 'agent' | 'system', content: string, step?: string) => {
    const message: Message = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
      step,
    };
    setMessages(prev => [...prev, message]);
  };

  const updateFlowStep = (id: string, updates: Partial<FlowStep>) => {
    setFlowSteps(prev => prev.map(step => 
      step.id === id ? { ...step, ...updates } : step
    ));
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input;
    setInput('');
    setIsLoading(true);
    addMessage('user', userMessage);

    // Initialize flow steps
    const steps: FlowStep[] = [
      { id: '1', title: 'Consumer Agent receives query', description: 'Processing your request...', status: 'pending' },
      { id: '2', title: 'Discovering Finance Feed Agent', description: 'Querying registry...', status: 'pending' },
      { id: '3', title: 'Sending A2A message', description: 'Establishing communication...', status: 'pending' },
      { id: '4', title: 'Finance Feed Agent processing', description: 'Fetching stock data...', status: 'pending' },
      { id: '5', title: 'Response received', description: 'Formatting response...', status: 'pending' },
    ];
    setFlowSteps(steps);

    try {
      // Step 1: Consumer Agent receives query
      updateFlowStep('1', { status: 'active' });
      await new Promise(resolve => setTimeout(resolve, 500));
      updateFlowStep('1', { status: 'completed' });

      // Step 2: Discovering Finance Feed Agent (simulated registry lookup)
      updateFlowStep('2', { status: 'active' });
      await new Promise(resolve => setTimeout(resolve, 800));
      updateFlowStep('2', { 
        status: 'completed',
        data: { agentId: 'finance-feed-agent', url: CONFIG.financeFeedAgent.a2a }
      });
      addMessage('system', `✓ Found Finance Feed Agent at ${CONFIG.financeFeedAgent.a2a}`);

      // Step 3: Sending A2A message
      updateFlowStep('3', { status: 'active' });
      const a2aPayload = {
        content: { text: userMessage, type: 'text' },
        role: 'user',
        conversation_id: `demo-${Date.now()}`,
      };
      addMessage('system', `→ Sending A2A message to Finance Feed Agent...`);

      // Step 4: Finance Feed Agent processing
      updateFlowStep('3', { status: 'completed' });
      updateFlowStep('4', { status: 'active' });

      // Step 5: Get response from Consumer Agent (which proxies to Finance Feed Agent)
      const response = await axios.post(CONFIG.consumerAgent.a2a, a2aPayload, {
        headers: { 'Content-Type': 'application/json' },
        timeout: 30000,
      });

      updateFlowStep('4', { status: 'completed' });
      updateFlowStep('5', { status: 'active' });

      // Extract text from response
      let responseText = '';
      if (response.data?.parts?.[0]?.text) {
        responseText = response.data.parts[0].text;
      } else if (typeof response.data === 'string') {
        responseText = response.data;
      } else {
        responseText = JSON.stringify(response.data, null, 2);
      }

      // Clean up the response text
      responseText = responseText.replace(/Message\(content=.*?\)/g, '');
      responseText = responseText.replace(/\[data-consumer-agent\]|\[finance-feed-agent\]/g, '').trim();

      updateFlowStep('5', { status: 'completed', data: { response: responseText } });
      addMessage('agent', responseText);
    } catch (error: any) {
      const errorMessage = error.response?.data?.message || error.message || 'An error occurred';
      addMessage('system', `❌ Error: ${errorMessage}`);
      setFlowSteps(prev => prev.map(step => 
        step.status === 'active' ? { ...step, status: 'error' } : step
      ));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="query-interface">
      <div className="card">
        <h2 className="card-title">💬 Interactive Query Interface</h2>
        <p className="mb-3" style={{ color: '#666', marginBottom: '1rem' }}>
          Ask questions and watch the real-time communication flow between agents.
        </p>

        {/* Flow Visualization */}
        <div className="flow-visualization" style={{ marginBottom: '2rem', padding: '1.5rem', background: '#f8f9fa', borderRadius: '8px' }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: 600 }}>Communication Flow</h3>
          <div className="flow-steps">
            {flowSteps.map((step, index) => (
              <motion.div
                key={step.id}
                className="flow-step"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <div className="step-indicator" style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: '1rem',
                  backgroundColor: 
                    step.status === 'completed' ? '#28a745' :
                    step.status === 'active' ? '#007bff' :
                    step.status === 'error' ? '#dc3545' : '#e0e0e0',
                  color: 'white',
                  fontWeight: 'bold',
                  flexShrink: 0,
                }}>
                  {step.status === 'completed' ? '✓' : step.status === 'error' ? '✗' : index + 1}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{step.title}</div>
                  <div style={{ fontSize: '0.9rem', color: '#666' }}>{step.description}</div>
                  {step.status === 'active' && (
                    <div className="spinner" style={{ marginTop: '0.5rem', width: '20px', height: '20px' }} />
                  )}
                  {step.data && (
                    <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#555', fontFamily: 'monospace' }}>
                      {JSON.stringify(step.data, null, 2)}
                    </div>
                  )}
                </div>
                {index < flowSteps.length - 1 && (
                  <div style={{
                    position: 'absolute',
                    left: '15px',
                    top: '30px',
                    width: '2px',
                    height: '30px',
                    backgroundColor: step.status === 'completed' ? '#28a745' : '#e0e0e0',
                    zIndex: 0,
                  }} />
                )}
              </motion.div>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div className="messages-container" style={{
          height: '400px',
          overflowY: 'auto',
          border: '1px solid #e0e0e0',
          borderRadius: '8px',
          padding: '1rem',
          marginBottom: '1rem',
          background: '#fafafa',
        }}>
          <AnimatePresence>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`message message-${message.role}`}
                style={{
                  marginBottom: '1rem',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  background: message.role === 'user' ? '#667eea' : message.role === 'system' ? '#fff3cd' : '#e7f3ff',
                  color: message.role === 'user' ? 'white' : '#333',
                  marginLeft: message.role === 'user' ? 'auto' : '0',
                  marginRight: message.role === 'user' ? '0' : 'auto',
                  maxWidth: '80%',
                  wordWrap: 'break-word',
                }}
              >
                <div style={{ fontSize: '0.85rem', opacity: 0.8, marginBottom: '0.25rem' }}>
                  {message.role === 'user' ? '👤 You' : message.role === 'system' ? '⚙️ System' : '🤖 Agent'}
                </div>
                <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
                <div style={{ fontSize: '0.75rem', opacity: 0.7, marginTop: '0.5rem' }}>
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            className="input"
            placeholder="Ask about stock prices... (e.g., 'what are the current stock prices?')"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            disabled={isLoading}
          />
          <button
            className="button"
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? '⏳' : 'Send'}
          </button>
        </div>

        {/* Quick actions */}
        <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            className="button"
            style={{ padding: '0.5rem 1rem', fontSize: '0.9rem', background: '#6c757d' }}
            onClick={() => setInput("what are the current stock prices?")}
          >
            Stock Prices
          </button>
          <button
            className="button"
            style={{ padding: '0.5rem 1rem', fontSize: '0.9rem', background: '#6c757d' }}
            onClick={() => setInput("ask finance agent about TSLA")}
          >
            Ask About TSLA
          </button>
          <button
            className="button"
            style={{ padding: '0.5rem 1rem', fontSize: '0.9rem', background: '#6c757d' }}
            onClick={() => {
              setMessages([]);
              setFlowSteps([]);
            }}
          >
            Clear
          </button>
        </div>
      </div>

      <style>{`
        .flow-steps {
          position: relative;
          padding-left: 0;
        }
        .flow-step {
          display: flex;
          align-items: flex-start;
          padding: '1rem 0';
          position: relative;
          padding: 1rem 0;
        }
      `}</style>
    </div>
  );
};

export default QueryInterface;
