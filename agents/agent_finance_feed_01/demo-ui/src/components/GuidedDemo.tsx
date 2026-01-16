import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { CONFIG } from '../config';

interface DemoStep {
  id: number;
  title: string;
  description: string;
  action?: () => Promise<void>;
  duration: number;
}

const GuidedDemo: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [stepResults, setStepResults] = useState<Record<number, any>>({});

  const steps: DemoStep[] = [
    {
      id: 1,
      title: 'Introduction',
      description: 'Welcome to the NANDA Agent Demo! This guided tour will walk you through the complete Data Facts and A2A communication flow.',
      duration: 3000,
    },
    {
      id: 2,
      title: 'Agent Discovery',
      description: 'The Consumer Agent queries the Registry to discover available agents, including the Finance Feed Agent.',
      action: async () => {
        try {
          const response = await axios.get(CONFIG.registry.list, { timeout: 10000 });
          setStepResults({ ...stepResults, 2: { success: true, agentsFound: Array.isArray(response.data) ? response.data.length : response.data.agents?.length || 0 } });
        } catch (error) {
          setStepResults({ ...stepResults, 2: { success: false, error: 'Registry query failed (may not be accessible)' } });
        }
      },
      duration: 2000,
    },
    {
      id: 3,
      title: 'A2A Communication',
      description: 'The Consumer Agent sends an A2A message to the Finance Feed Agent to request stock prices.',
      action: async () => {
        try {
          const response = await axios.post(CONFIG.consumerAgent.a2a, {
            content: { text: 'what are the current stock prices?', type: 'text' },
            role: 'user',
            conversation_id: `guided-demo-${Date.now()}`,
          }, { timeout: 30000 });
          setStepResults({ ...stepResults, 3: { success: true, response: response.data } });
        } catch (error: any) {
          setStepResults({ ...stepResults, 3: { success: false, error: error.message } });
        }
      },
      duration: 3000,
    },
    {
      id: 4,
      title: 'Data Facts Access',
      description: 'The Consumer Agent can also access data via Data Facts, fetching metadata and then the dataset itself.',
      action: async () => {
        try {
          const dataFacts = await axios.get(CONFIG.financeFeedAgent.dataFacts);
          const dataset = await axios.get(dataFacts.data.endpoint);
          setStepResults({ ...stepResults, 4: { success: true, dataFacts: dataFacts.data, dataset: dataset.data } });
        } catch (error: any) {
          setStepResults({ ...stepResults, 4: { success: false, error: error.message } });
        }
      },
      duration: 2500,
    },
    {
      id: 5,
      title: 'Freshness Validation',
      description: 'The system validates data freshness using TTL (Time To Live) to ensure data is up-to-date.',
      action: async () => {
        try {
          const dataFacts = await axios.get(CONFIG.financeFeedAgent.dataFacts);
          const lastUpdated = new Date(dataFacts.data.evidence.last_updated);
          const ageSeconds = (new Date().getTime() - lastUpdated.getTime()) / 1000;
          const isFresh = ageSeconds <= dataFacts.data.ttl_seconds;
          setStepResults({ ...stepResults, 5: { success: true, isFresh, ageSeconds, ttl: dataFacts.data.ttl_seconds } });
        } catch (error: any) {
          setStepResults({ ...stepResults, 5: { success: false, error: error.message } });
        }
      },
      duration: 2000,
    },
    {
      id: 6,
      title: 'Conclusion',
      description: 'Congratulations! You\'ve seen the complete flow: Registry Discovery → A2A Communication → Data Facts Access → Validation. Both methods work seamlessly together!',
      duration: 3000,
    },
  ];

  const runStep = async (step: DemoStep) => {
    if (step.action) {
      await step.action();
    }
  };

  const startDemo = async () => {
    setIsRunning(true);
    setCurrentStep(0);
    setStepResults({});

    for (let i = 0; i < steps.length; i++) {
      setCurrentStep(i);
      await runStep(steps[i]);
      await new Promise(resolve => setTimeout(resolve, steps[i].duration));
    }

    setIsRunning(false);
  };

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
      runStep(steps[currentStep + 1]);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const currentStepData = steps[currentStep];
  const progress = ((currentStep + 1) / steps.length) * 100;

  return (
    <div className="guided-demo">
      <div className="card">
        <h2 className="card-title">🎬 Guided Demo</h2>
        <p style={{ color: '#666', marginBottom: '1.5rem' }}>
          Take a step-by-step tour through the complete agent communication flow.
        </p>

        {/* Progress Bar */}
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.9rem', color: '#666' }}>
              Step {currentStep + 1} of {steps.length}
            </span>
            <span style={{ fontSize: '0.9rem', color: '#666' }}>
              {Math.round(progress)}% Complete
            </span>
          </div>
          <div style={{
            width: '100%',
            height: '8px',
            background: '#e0e0e0',
            borderRadius: '4px',
            overflow: 'hidden',
          }}>
            <motion.div
              style={{
                height: '100%',
                background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
                borderRadius: '4px',
              }}
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        {/* Current Step */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
            style={{
              padding: '2rem',
              background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
              borderRadius: '12px',
              marginBottom: '1.5rem',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>
              {currentStepData.id === 1 && '👋'}
              {currentStepData.id === 2 && '🔍'}
              {currentStepData.id === 3 && '💬'}
              {currentStepData.id === 4 && '📋'}
              {currentStepData.id === 5 && '✅'}
              {currentStepData.id === 6 && '🎉'}
            </div>
            <h3 style={{ fontSize: '1.8rem', marginBottom: '1rem', color: '#333' }}>
              {currentStepData.title}
            </h3>
            <p style={{ fontSize: '1.1rem', color: '#666', lineHeight: '1.6' }}>
              {currentStepData.description}
            </p>

            {stepResults[currentStepData.id] && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                style={{
                  marginTop: '1.5rem',
                  padding: '1rem',
                  background: stepResults[currentStepData.id].success ? '#d4edda' : '#f8d7da',
                  borderRadius: '8px',
                  border: `1px solid ${stepResults[currentStepData.id].success ? '#c3e6cb' : '#f5c6cb'}`,
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
                  {stepResults[currentStepData.id].success ? '✅ Success' : '❌ Error'}
                </div>
                <pre style={{ fontSize: '0.85rem', overflow: 'auto', maxHeight: '200px' }}>
                  {JSON.stringify(stepResults[currentStepData.id], null, 2)}
                </pre>
              </motion.div>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Controls */}
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <button
            className="button"
            onClick={prevStep}
            disabled={currentStep === 0 || isRunning}
            style={{ background: '#6c757d' }}
          >
            ← Previous
          </button>
          {!isRunning && currentStep === 0 && (
            <button
              className="button"
              onClick={startDemo}
              style={{ background: '#28a745', fontSize: '1.1rem', padding: '0.75rem 2rem' }}
            >
              ▶ Start Guided Demo
            </button>
          )}
          {isRunning && (
            <button className="button" disabled style={{ background: '#6c757d' }}>
              ⏳ Running...
            </button>
          )}
          <button
            className="button"
            onClick={nextStep}
            disabled={currentStep === steps.length - 1 || isRunning}
            style={{ background: '#6c757d' }}
          >
            Next →
          </button>
        </div>

        {/* Step Indicators */}
        <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {steps.map((step, index) => (
            <button
              key={step.id}
              onClick={() => {
                if (!isRunning) {
                  setCurrentStep(index);
                  runStep(step);
                }
              }}
              disabled={isRunning}
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                border: '2px solid',
                borderColor: index === currentStep ? '#667eea' : index < currentStep ? '#28a745' : '#e0e0e0',
                background: index === currentStep ? '#667eea' : index < currentStep ? '#28a745' : 'white',
                color: index <= currentStep ? 'white' : '#666',
                cursor: isRunning ? 'not-allowed' : 'pointer',
                fontWeight: 600,
                opacity: isRunning && index !== currentStep ? 0.5 : 1,
              }}
            >
              {index + 1}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default GuidedDemo;
