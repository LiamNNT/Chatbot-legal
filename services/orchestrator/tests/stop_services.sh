#!/bin/bash
# Script dừng RAG Service và Orchestrator Service

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Stopping services...${NC}"

# Kill by PID files
if [ -f /tmp/rag_service.pid ]; then
    PID=$(cat /tmp/rag_service.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo -e "${GREEN}✓ Stopped RAG Service (PID: $PID)${NC}"
    fi
    rm /tmp/rag_service.pid
fi

if [ -f /tmp/orchestrator_service.pid ]; then
    PID=$(cat /tmp/orchestrator_service.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo -e "${GREEN}✓ Stopped Orchestrator (PID: $PID)${NC}"
    fi
    rm /tmp/orchestrator_service.pid
fi

# Kill by ports (backup)
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:8001 | xargs kill -9 2>/dev/null || true

echo -e "${GREEN}✓ All services stopped${NC}"
