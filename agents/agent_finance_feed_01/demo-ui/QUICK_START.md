# Quick Start Guide

## 🚀 Get the Demo Running in 3 Steps

### Step 1: Install Dependencies

```bash
cd demo-ui
npm install
```

### Step 2: Verify Configuration

The app is already configured with deployed agent endpoints:
- Finance Feed Agent: `54.172.251.235`
- Consumer Agent: `44.223.52.126`

If you need to change them, edit `src/config.ts`

### Step 3: Start the App

```bash
npm start
```

The app will open automatically at `http://localhost:3000`

---

## 🎯 Try These Features First

1. **Query Interface** - Type "what are the current stock prices?" and watch the flow
2. **Stock Prices** - See live prices updating every 10 seconds
3. **Architecture Diagram** - Click components and run flows
4. **Guided Demo** - Click "Start Guided Demo" for a walkthrough

---

## 🎨 Visual Highlights

- **Gradient backgrounds** - Purple gradient theme throughout
- **Smooth animations** - Framer Motion for fluid interactions
- **Real-time updates** - Live data from deployed agents
- **Responsive design** - Works on desktop, tablet, and mobile

---

## 📱 Features Overview

| Feature | What It Shows |
|---------|--------------|
| 💬 Query Interface | Real-time A2A communication flow |
| 📊 Stock Prices | Live data with freshness validation |
| 🏗️ Architecture | Interactive system diagram |
| 📈 Dashboard | Agent health and metrics |
| 🔍 Registry | Discovered agents and metadata |
| ⚖️ Comparison | A2A vs Data Facts side-by-side |
| 🧪 Tests | Run validation tests |
| 🛠️ API Playground | Test endpoints interactively |
| 📋 Logs | Real-time log stream |
| 🎬 Guided Demo | Automated walkthrough |

---

## 🔧 Troubleshooting

**Agents not responding?**
- Check agents are running: `ssh -i key.pem ubuntu@IP 'ps aux | grep agent'`
- Verify endpoints in browser console
- Check CORS is enabled on agents

**Build errors?**
- Run `npm install` again
- Clear node_modules: `rm -rf node_modules && npm install`

**Type errors?**
- Run `npm install @types/node @types/react` if needed

---

## 🎉 Demo Tips

1. **Start with Guided Demo** - Best for first-time viewers
2. **Then try Query Interface** - Most impressive feature
3. **Show Stock Prices** - Visual and easy to understand
4. **Run Test Suite** - Validates everything works

---

Enjoy your demo! 🚀
