// Configuration for agent endpoints
export const CONFIG = {
  financeFeedAgent: {
    a2a: 'http://54.172.251.235:6000/a2a',
    dataFacts: 'http://54.172.251.235:8000/data_facts/public_stock_ticker.json',
    stockData: 'http://54.172.251.235:8000/stock_data',
    health: 'http://54.172.251.235:8000/health',
  },
  consumerAgent: {
    a2a: 'http://44.223.52.126:6001/a2a',
    health: 'http://44.223.52.126:6001/health',
  },
  registry: {
    url: 'http://registry.chat39.com:6900',
    list: 'http://registry.chat39.com:6900/list',
  },
};

export type AgentEndpoint = keyof typeof CONFIG.financeFeedAgent | keyof typeof CONFIG.consumerAgent;
