#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Finance Feed NEST Agent

A NEST agent that serves financial data (stock prices) via Data Facts.
Uses Yahoo Finance API to fetch real stock prices and exposes them through:
- Data Facts endpoint: /data_facts/public_stock_ticker.json
- Stock data endpoint: /stock_data
- A2A communication: /a2a (standard NEST pattern)
"""
import os
import sys
import json
import hashlib
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        try:
            import codecs
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
            if hasattr(sys.stderr, 'buffer'):
                sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
        except Exception:
            pass

def safe_print(*args, **kwargs):
    """Print function that handles Unicode encoding errors gracefully."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode('ascii', 'replace').decode('ascii'))
            else:
                safe_args.append(arg)
        print(*safe_args, **kwargs)

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nanda_core.core.adapter import NANDA
from dotenv import load_dotenv
load_dotenv()

# Try to import yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    safe_print("⚠️ Warning: yfinance library not available. Install with: pip install yfinance")

# Try to import Flask for HTTP endpoints
try:
    from flask import Flask, jsonify
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    safe_print("⚠️ Warning: Flask library not available. Install with: pip install flask flask-cors")

# =============================================================================
# DATA FACTS AND STOCK DATA SERVER
# =============================================================================

class FinanceDataServer:
    """HTTP server for Data Facts and stock data endpoints"""
    
    def __init__(self, port: int = 8000, public_url: Optional[str] = None):
        self.port = port
        self.public_url = public_url or f"http://localhost:{port}"
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS
        self.server_thread = None
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes for Data Facts and stock data"""
        
        @self.app.route('/data_facts/public_stock_ticker.json', methods=['GET'])
        def get_data_facts():
            """Serve Data Facts JSON"""
            try:
                # Fetch current stock data to update evidence
                stock_data = self._fetch_stock_data()
                checksum = self._compute_checksum(stock_data)
                now_iso = datetime.now(timezone.utc).isoformat()
                
                # Build Data Facts response
                data_facts = {
                    "dataset_id": "public_stock_ticker",
                    "dataset_description": "Live stock price feed for TSLA, AAPL, ETH-USD via Yahoo Finance API. Updates every 10 minutes.",
                    "update_frequency": "10 minutes",
                    "data_owner": os.getenv("AGENT_ID", "finance-feed-agent"),
                    "access_type": "public",
                    "endpoint": f"{self.public_url}/stock_data",
                    "evidence": {
                        "last_updated": now_iso,
                        "checksum_sha256": checksum,
                        "source": "yahoo_finance_api"
                    },
                    "ttl_seconds": 600
                }
                
                return jsonify(data_facts)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/stock_data', methods=['GET'])
        @self.app.route('/stock_prices', methods=['GET'])  # Alias for backward compatibility
        def get_stock_data():
            """Serve stock data JSON"""
            try:
                data = self._fetch_stock_data()
                return jsonify(data)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({"status": "ok", "service": "finance-feed"})
    
    def _fetch_stock_data(self) -> Dict[str, Any]:
        """Fetch stock data from Yahoo Finance API"""
        if not YFINANCE_AVAILABLE:
            raise RuntimeError("yfinance library not available")
        
        tickers = ["TSLA", "AAPL", "ETH-USD"]
        data = {}
        
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                if 'currentPrice' in info and info['currentPrice']:
                    data[ticker] = round(float(info['currentPrice']), 2)
                elif 'regularMarketPrice' in info and info['regularMarketPrice']:
                    data[ticker] = round(float(info['regularMarketPrice']), 2)
                else:
                    # Fallback: use history
                    hist = stock.history(period="1d", interval="1m")
                    if not hist.empty:
                        latest_price = float(hist['Close'].iloc[-1])
                        data[ticker] = round(latest_price, 2)
                    else:
                        data[ticker] = None
            except Exception as e:
                safe_print(f"Error fetching {ticker}: {e}")
                data[ticker] = None
        
        data["timestamp"] = int(time.time())
        return data
    
    def _compute_checksum(self, data: dict) -> str:
        """Compute SHA256 checksum of data (excluding timestamp)"""
        data_copy = {k: v for k, v in data.items() if k != "timestamp"}
        serialized = json.dumps(data_copy, sort_keys=True).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()
    
    def start(self):
        """Start the Flask server in a background thread"""
        def run():
            self.app.run(
                host='0.0.0.0',
                port=self.port,
                debug=False,
                use_reloader=False
            )
        
        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()
        safe_print(f"📊 Finance data server started: http://localhost:{self.port}/stock_data")
        safe_print(f"📋 Data Facts: http://localhost:{self.port}/data_facts/public_stock_ticker.json")
    
    def stop(self):
        """Stop the server (not typically needed for daemon thread)"""
        # Flask doesn't have a clean way to stop in a thread
        # The daemon thread will exit when main process exits
        pass

# =============================================================================
# AGENT LOGIC
# =============================================================================

def create_finance_agent_logic(data_server: FinanceDataServer):
    """Create agent logic function for finance feed agent"""
    
    def agent_logic(message: str, conversation_id: str) -> str:
        """Simple agent logic that responds to messages"""
        message_lower = message.lower()
        
        if "hello" in message_lower or "hi" in message_lower:
            return "Hello! I'm a Finance Feed Agent. I provide real-time stock price data via Data Facts. You can access stock prices for TSLA, AAPL, and ETH-USD through my public dataset."
        
        if "stock" in message_lower or "price" in message_lower:
            try:
                stock_data = data_server._fetch_stock_data()
                prices = {k: v for k, v in stock_data.items() if k != "timestamp"}
                price_str = ", ".join([f"{k}: ${v}" if v else f"{k}: N/A" for k, v in prices.items()])
                return f"Current stock prices: {price_str}"
            except Exception as e:
                return f"Sorry, I couldn't fetch stock prices right now: {str(e)}"
        
        if "data facts" in message_lower or "dataset" in message_lower:
            data_facts_url = f"{data_server.public_url}/data_facts/public_stock_ticker.json"
            return f"You can access my Data Facts at: {data_facts_url}. The dataset includes real-time stock prices for TSLA, AAPL, and ETH-USD."
        
        if "help" in message_lower:
            return """I'm a Finance Feed Agent. I can help you with:
- Stock prices: Ask me about current stock prices
- Data Facts: I can tell you about my public dataset
- Data access: My dataset is accessible via Data Facts endpoint"""
        
        return "I'm a Finance Feed Agent providing stock market data. Ask me about stock prices or my Data Facts endpoint!"
    
    return agent_logic

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function to start the finance feed agent"""
    # Get configuration from environment variables
    agent_id = os.getenv("AGENT_ID", "finance-feed-agent")
    agent_name = os.getenv("AGENT_NAME", "Finance Feed Agent")
    registry_url = os.getenv("REGISTRY_URL", None)
    public_url = os.getenv("PUBLIC_URL", None)
    port = int(os.getenv("PORT", "6000"))
    data_server_port = int(os.getenv("DATA_SERVER_PORT", "8000"))  # Port for Data Facts/stock data
    
    safe_print("=" * 60)
    safe_print(f"🤖 {agent_name}")
    safe_print(f"📊 Agent ID: {agent_id}")
    safe_print("=" * 60)
    
    if not YFINANCE_AVAILABLE:
        safe_print("❌ Error: yfinance library is required. Install with: pip install yfinance")
        sys.exit(1)
    
    if not FLASK_AVAILABLE:
        safe_print("❌ Error: Flask library is required. Install with: pip install flask flask-cors")
        sys.exit(1)
    
    # Determine public URL for data server
    # If public_url is set, use same host but data_server_port
    # Otherwise use localhost with data_server_port
    if public_url:
        from urllib.parse import urlparse
        parsed = urlparse(public_url)
        data_server_public_url = f"{parsed.scheme}://{parsed.hostname}:{data_server_port}"
    else:
        data_server_public_url = f"http://localhost:{data_server_port}"
    
    # Start finance data server (Data Facts and stock data)
    data_server = FinanceDataServer(port=data_server_port, public_url=data_server_public_url)
    data_server.start()
    
    # Wait a moment for server to start
    time.sleep(0.5)
    
    # Create agent logic
    agent_logic = create_finance_agent_logic(data_server)
    
    # Build data_facts_url for registry registration
    data_facts_url = f"{data_server_public_url}/data_facts/public_stock_ticker.json"
    
    if registry_url:
        safe_print(f"🌐 Registry: {registry_url}")
        safe_print(f"📋 Data Facts URL: {data_facts_url}")
    
    # Create NANDA agent
    nanda = NANDA(
        agent_id=agent_id,
        agent_logic=agent_logic,
        port=port,
        registry_url=registry_url,
        public_url=public_url,
        enable_telemetry=False,  # Disable telemetry for simplicity
        data_facts_url=data_facts_url  # Register Data Facts URL
    )
    
    safe_print(f"🚀 A2A endpoint: http://localhost:{port}/a2a")
    safe_print(f"📊 Stock data: http://localhost:{data_server_port}/stock_data")
    safe_print(f"📋 Data Facts: {data_facts_url}")
    safe_print("\n💡 Try sending A2A messages or accessing the endpoints directly")
    safe_print("🛑 Press Ctrl+C to stop")
    safe_print("=" * 60)
    
    # Start the agent (this blocks)
    try:
        nanda.start()
    except KeyboardInterrupt:
        safe_print("\n🛑 Shutting down...")
        data_server.stop()
        nanda.stop()

if __name__ == "__main__":
    main()

