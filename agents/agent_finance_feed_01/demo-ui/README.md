# NANDA Agent Demo UI

A beautiful, interactive React demo showcasing the Finance Feed Agent and Consumer Agent with Data Facts and A2A communication.

## Features

- **💬 Interactive Query Interface** - Chat-style interface with real-time flow visualization
- **📊 Live Stock Prices** - Real-time stock data with Data Facts metadata
- **🏗️ Interactive Architecture Diagram** - Clickable components with animated flows
- **📈 Agent Dashboard** - Live metrics and health monitoring
- **🔍 Registry Explorer** - Visual agent discovery from registry
- **⚖️ Comparison View** - Side-by-side A2A vs Data Facts comparison
- **🧪 Test Suite Runner** - Run comprehensive test scenarios
- **🛠️ API Playground** - Interactive endpoint testing
- **📋 Log Viewer** - Real-time log stream with filtering
- **🎬 Guided Demo** - Step-by-step automated walkthrough

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Agents should be running (or update `src/config.ts` with your endpoints)

### Installation

```bash
cd demo-ui
npm install
```

### Running the App

```bash
npm start
```

The app will open at `http://localhost:3000`

### Building for Production

```bash
npm run build
```

This creates an optimized production build in the `build` folder.

## Configuration

Update agent endpoints in `src/config.ts`:

```typescript
export const CONFIG = {
  financeFeedAgent: {
    a2a: 'http://YOUR_FINANCE_IP:6000/a2a',
    dataFacts: 'http://YOUR_FINANCE_IP:8000/data_facts/public_stock_ticker.json',
    stockData: 'http://YOUR_FINANCE_IP:8000/stock_data',
  },
  consumerAgent: {
    a2a: 'http://YOUR_CONSUMER_IP:6001/a2a',
  },
  registry: {
    url: 'http://registry.chat39.com:6900',
    list: 'http://registry.chat39.com:6900/list',
  },
};
```

## Architecture

```
demo-ui/
├── src/
│   ├── components/
│   │   ├── QueryInterface.tsx       # Chat interface with flow visualization
│   │   ├── StockPriceDisplay.tsx    # Live stock prices + Data Facts
│   │   ├── ArchitectureDiagram.tsx  # Interactive architecture diagram
│   │   ├── AgentDashboard.tsx       # Live metrics dashboard
│   │   ├── RegistryExplorer.tsx     # Agent discovery UI
│   │   ├── ComparisonView.tsx       # A2A vs Data Facts comparison
│   │   ├── TestSuiteRunner.tsx      # Test execution UI
│   │   ├── APIPlayground.tsx        # Interactive API tester
│   │   ├── LogViewer.tsx            # Log stream viewer
│   │   └── GuidedDemo.tsx           # Step-by-step demo
│   ├── App.tsx                      # Main app component
│   ├── App.css                      # Global styles
│   └── config.ts                    # Configuration
└── package.json
```

## Usage

### Query Interface
1. Type a query like "what are the current stock prices?"
2. Watch the real-time step-by-step flow
3. See the complete communication path

### Stock Prices
- View live stock prices (updates every 10 seconds)
- See Data Facts metadata with freshness indicator
- Click endpoints to view directly

### Architecture Diagram
- Click components to see details
- Click flow buttons to see animated communication paths
- Run all flows to see the complete system in action

### Guided Demo
- Click "Start Guided Demo" for automated walkthrough
- Or navigate steps manually with Previous/Next buttons

## Troubleshooting

### CORS Errors
If you see CORS errors, the agents may need CORS headers. The finance feed agent already includes Flask-CORS.

### Connection Timeouts
- Verify agents are running: `npm start` or check deployment
- Check endpoints in `src/config.ts`
- Ensure agents are accessible from your browser

### Type Errors
Run `npm install` to ensure all TypeScript types are installed.

## Deployment

### Build and Deploy

```bash
npm run build
# Deploy the 'build' folder to any static hosting (Netlify, Vercel, AWS S3, etc.)
```

### Example: Deploy to Netlify

```bash
npm run build
netlify deploy --prod --dir=build
```

### Example: Deploy to Vercel

```bash
npm run build
vercel --prod
```

## License

Part of the NANDA project.
