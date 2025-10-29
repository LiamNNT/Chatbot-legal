#!/bin/bash
# Quick commands reference for Chatbot-UIT

cat << 'EOF'
╔════════════════════════════════════════════════════════════════════╗
║              Chatbot-UIT - Quick Reference                         ║
╚════════════════════════════════════════════════════════════════════╝

📦 SETUP (One-time)
───────────────────────────────────────────────────────────────────────
  conda create -n chatbot-UIT python=3.11 -y
  conda activate chatbot-UIT
  cd services/rag_services && pip install -r requirements.txt
  cd ../orchestrator && pip install -r requirements.txt

🚀 START BACKEND
───────────────────────────────────────────────────────────────────────
  conda activate chatbot-UIT
  python start_backend.py

🛑 STOP BACKEND
───────────────────────────────────────────────────────────────────────
  python stop_backend.py
  # hoặc: Ctrl+C

🔍 CHECK STATUS
───────────────────────────────────────────────────────────────────────
  curl http://localhost:8000/v1/health           # RAG Service
  curl http://localhost:8001/api/v1/health       # Orchestrator
  docker ps                                       # Docker containers

📚 API DOCS
───────────────────────────────────────────────────────────────────────
  http://localhost:8000/docs                     # RAG API
  http://localhost:8001/docs                     # Orchestrator API
  http://localhost:5601                          # OpenSearch Dashboard

🧪 TEST
───────────────────────────────────────────────────────────────────────
  python services/orchestrator/tests/demo_agent_rag.py

🐛 TROUBLESHOOT
───────────────────────────────────────────────────────────────────────
  lsof -i :8000,8001,9200,8090                   # Check ports
  docker logs opensearch-node1                   # OpenSearch logs
  docker logs vietnamese-rag-weaviate            # Weaviate logs
  lsof -ti:8000 | xargs kill -9                  # Kill port 8000
  lsof -ti:8001 | xargs kill -9                  # Kill port 8001

📖 MORE INFO
───────────────────────────────────────────────────────────────────────
  See: BACKEND_SETUP.md

EOF
