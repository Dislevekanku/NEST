#!/usr/bin/env python3
"""
Minimal in-memory registry for local experiments.
Exposes POST /register and GET /list (same shape as registry.chat39.com).
Run before ecosystem + Exp 1 when testing locally without deploy.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

agents: list[dict] = []


def create_app():
    from flask import Flask, request, jsonify
    app = Flask(__name__)

    @app.route("/register", methods=["POST"])
    def register():
        data = request.get_json() or {}
        agents.append({
            "agent_id": data.get("agent_id"),
            "agent_url": data.get("agent_url"),
            "data_facts_url": data.get("data_facts_url"),
        })
        return jsonify({"status": "ok"}), 200

    @app.route("/list", methods=["GET"])
    def list_agents():
        return jsonify(agents)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "agents": len(agents)}), 200

    return app


def main():
    import os
    port = int(os.environ.get("LOCAL_REGISTRY_PORT", "6900"))
    app = create_app()
    print(f"[local-registry] http://localhost:{port} (agents={len(agents)})")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
