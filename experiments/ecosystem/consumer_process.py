#!/usr/bin/env python3
"""
Minimal consumer agent process: /health + /a2a.
Run one per consumer (port 6001..6050).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

AGENT_ID = os.environ.get("CONSUMER_AGENT_ID", "consumer_001")
PORT = int(os.environ.get("CONSUMER_PORT", "6001"))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "agent_id": AGENT_ID}), 200


@app.route("/a2a", methods=["POST"])
def a2a():
    """A2A stub: echoes request, can proxy to provider if needed."""
    try:
        data = request.get_json() or {}
        content = (data.get("content") or {}).get("text", "")
        return jsonify({
            "content": [{"type": "text", "text": f"[{AGENT_ID}] received: {content[:100]}"}],
            "role": "assistant",
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def main():
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
