#!/bin/bash#!/bin/bash

# ──────────────────────────────────────────────

# Chatbot-UIT Frontend (Streamlit) — start script# Chatbot UIT Frontend - Development Server

# ──────────────────────────────────────────────# This script starts the frontend development server



set -eecho "🚀 Starting Chatbot UIT Frontend..."

echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"# Check if node_modules exists

if [ ! -d "node_modules" ]; then

echo "🎓 Chatbot-UIT — Streamlit Frontend"    echo "📦 Installing dependencies..."

echo ""    npm install

    echo ""

# Install dependencies if neededfi

if ! python -c "import streamlit" 2>/dev/null; then

    echo "📦 Installing dependencies..."# Check if .env exists

    pip install -r requirements.txtif [ ! -f ".env" ]; then

    echo ""    echo "⚙️  Creating .env file from .env.example..."

fi    cp .env.example .env

    echo ""

echo "✅ Starting Streamlit..."fi

echo "📱 Frontend: http://localhost:8501"

echo "🔗 Orchestrator API expected at: http://localhost:8001"echo "✅ Starting development server..."

echo "🔗 RAG Service expected at:      http://localhost:8002"echo "📱 Frontend will be available at: http://localhost:5173"

echo ""echo "🔗 Backend API should be running at: http://localhost:8001"

echo "Press Ctrl+C to stop"echo ""

echo ""echo "Press Ctrl+C to stop the server"

echo ""

streamlit run app.py \

    --server.port 8501 \# Start dev server

    --server.address 0.0.0.0 \npm run dev

    --browser.gatherUsageStats false
