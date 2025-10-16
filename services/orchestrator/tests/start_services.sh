#!/bin/bash
# Script khởi động RAG Service và Orchestrator Service để test agent + RAG

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Starting Services for Agent + RAG Integration           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get project root (we are in services/orchestrator/tests)
# Go up 3 levels: tests -> orchestrator -> services -> project_root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
echo -e "${YELLOW}Project root: ${PROJECT_ROOT}${NC}"

# Paths
RAG_DIR="${PROJECT_ROOT}/services/rag_services"
ORCHESTRATOR_DIR="${PROJECT_ROOT}/services/orchestrator"

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Killing process on port $port...${NC}"
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
    sleep 1
}

# Check if services are already running
echo -e "\n${BLUE}Checking for existing services...${NC}"

if check_port 8000; then
    echo -e "${YELLOW}⚠️  RAG Service already running on port 8000${NC}"
    read -p "Kill and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill_port 8000
    fi
fi

if check_port 8001; then
    echo -e "${YELLOW}⚠️  Orchestrator already running on port 8001${NC}"
    read -p "Kill and restart? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill_port 8001
    fi
fi

# Start RAG Service
echo -e "\n${BLUE}[1/2] Starting RAG Service...${NC}"
cd "$RAG_DIR"

if [ ! -f "start_server.py" ]; then
    echo -e "${RED}Error: start_server.py not found in $RAG_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}Starting RAG on port 8000...${NC}"
python start_server.py > /tmp/rag_service.log 2>&1 &
RAG_PID=$!
echo -e "${GREEN}✓ RAG Service started (PID: $RAG_PID)${NC}"

# Wait for RAG to be ready
echo -e "${YELLOW}Waiting for RAG service to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ RAG Service is ready!${NC}"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Start Orchestrator Service
echo -e "\n${BLUE}[2/2] Starting Orchestrator Service...${NC}"
cd "$ORCHESTRATOR_DIR"

if [ ! -f "start_server.sh" ]; then
    echo -e "${RED}Error: start_server.sh not found in $ORCHESTRATOR_DIR${NC}"
    echo -e "${YELLOW}Trying alternative start method...${NC}"
    
    if [ -f "app/main.py" ]; then
        echo -e "${GREEN}Starting Orchestrator on port 8001...${NC}"
        python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > /tmp/orchestrator_service.log 2>&1 &
        ORCHESTRATOR_PID=$!
    else
        echo -e "${RED}Cannot find main.py${NC}"
        kill $RAG_PID
        exit 1
    fi
else
    echo -e "${GREEN}Starting Orchestrator on port 8001...${NC}"
    ./start_server.sh > /tmp/orchestrator_service.log 2>&1 &
    ORCHESTRATOR_PID=$!
fi

echo -e "${GREEN}✓ Orchestrator started (PID: $ORCHESTRATOR_PID)${NC}"

# Wait for Orchestrator to be ready
echo -e "${YELLOW}Waiting for Orchestrator to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Orchestrator is ready!${NC}"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Summary
echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Services Started Successfully                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Service URLs:${NC}"
echo -e "  RAG Service:         ${GREEN}http://localhost:8000${NC}"
echo -e "  Orchestrator:        ${GREEN}http://localhost:8001${NC}"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  RAG logs:            ${YELLOW}/tmp/rag_service.log${NC}"
echo -e "  Orchestrator logs:   ${YELLOW}/tmp/orchestrator_service.log${NC}"
echo ""
echo -e "${BLUE}Test với:${NC}"
echo -e "  ${YELLOW}python services/orchestrator/tests/demo_agent_rag.py${NC}"
echo ""
echo -e "${BLUE}Stop services:${NC}"
echo -e "  ${YELLOW}kill $RAG_PID $ORCHESTRATOR_PID${NC}"
echo -e "  hoặc: ${YELLOW}./services/orchestrator/tests/stop_services.sh${NC}"
echo ""

# Save PIDs
echo "$RAG_PID" > /tmp/rag_service.pid
echo "$ORCHESTRATOR_PID" > /tmp/orchestrator_service.pid

echo -e "${GREEN}✨ Ready to test Agent + RAG integration!${NC}\n"
