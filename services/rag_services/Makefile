# Vietnamese Hybrid RAG System Makefile
# Commands for managing the BM25 + Vector + Cross-Encoder system

.PHONY: help install start stop restart status clean test demo sample-data

# Default target
help:
	@echo "🚀 Vietnamese Hybrid RAG System"
	@echo "================================="
	@echo ""
	@echo "Available commands:"
	@echo "  📦 install        - Install Python dependencies"
	@echo "  🚀 start          - Start all services (OpenSearch + RAG)"
	@echo "  ⏹️  stop           - Stop all services"
	@echo "  🔄 restart        - Restart all services"
	@echo "  📊 status         - Check service status"
	@echo "  🧹 clean          - Clean up containers and volumes"
	@echo ""
	@echo "  📚 sample-data    - Create sample Vietnamese documents"
	@echo "  🧪 test-vietnamese - Test Vietnamese search capabilities"
	@echo "  🎯 demo           - Run complete hybrid search demo"
	@echo "  🔬 test-full      - Run complete test pipeline"
	@echo ""
	@echo "  📂 opensearch-*   - OpenSearch index management"
	@echo "  ❓ help           - Show this help message"

# Installation
install:
	@echo "📦 Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed!"

# Service management
start:
	@echo "🚀 Starting Vietnamese Hybrid RAG services..."
	@echo "📂 Starting OpenSearch..."
	cd docker && docker-compose up -d opensearch
	@echo "⏳ Waiting for OpenSearch to be ready..."
	@sleep 15
	@echo "🤖 Starting RAG service..."
	python app/main.py &
	@echo "✅ All services started!"
	@echo "🌐 RAG API: http://localhost:8000"
	@echo "🔍 OpenSearch: http://localhost:9200"

start-dev:
	@echo "🚀 Starting development environment..."
	cd docker && docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 15
	@echo "✅ Development environment ready!"

stop:
	@echo "⏹️  Stopping services..."
	pkill -f "python app/main.py" || true
	cd docker && docker-compose down
	@echo "✅ All services stopped!"

restart: stop start
	@echo "🔄 Services restarted!"

status:
	@echo "📊 Service Status:"
	@echo "=================="
	@echo -n "🤖 RAG Service: "
	@curl -s http://localhost:8000/v1/health > /dev/null 2>&1 && echo "✅ Running" || echo "❌ Down"
	@echo -n "🔍 OpenSearch: "
	@curl -s http://localhost:9200 > /dev/null 2>&1 && echo "✅ Running" || echo "❌ Down"
	@echo -n "📦 Docker Services: "
	@cd docker && docker-compose ps --services --filter status=running | wc -l | xargs -I {} echo "{} running"

# Development commands
dev-run:
	@echo "🛠️  Running in development mode..."
	python app/main.py

dev-shell:
	@echo "🐚 Opening development shell..."
	cd docker && docker-compose exec opensearch bash

# Sample data management
sample-data:
	@echo "📚 Creating sample Vietnamese data..."
	python scripts/create_sample_data.py

# Testing commands
test-vietnamese:
	@echo "🇻🇳 Testing Vietnamese search capabilities..."
	python scripts/test_vietnamese_search.py

test-components:
	@echo "🧪 Testing system components without Docker..."
	python scripts/test_without_docker.py

# Complete system demo
demo:
	@echo "🚀 Running complete hybrid search demo..."
	python scripts/demo_hybrid_search.py

# Full test pipeline
test-full: sample-data test-vietnamese demo
	@echo "✅ Complete testing pipeline finished!"

# OpenSearch management
opensearch-create:
	@echo "📂 Creating OpenSearch index with Vietnamese analyzer..."
	python -c "import requests; r=requests.post('http://localhost:8000/v1/opensearch/create-index'); print(f'Status: {r.status_code}')"

opensearch-delete:
	@echo "🗑️  Deleting OpenSearch index..."
	python -c "import requests; r=requests.delete('http://localhost:8000/v1/opensearch/delete-index'); print(f'Status: {r.status_code}')"

opensearch-reset: opensearch-delete opensearch-create
	@echo "🔄 OpenSearch index reset complete!"

opensearch-stats:
	@echo "📊 Getting OpenSearch index statistics..."
	python -c "import requests; r=requests.get('http://localhost:8000/v1/opensearch/stats'); print(r.json() if r.status_code == 200 else f'Error: {r.status_code}')"

opensearch-health:
	@echo "🏥 Checking OpenSearch health..."
	python -c "import requests; r=requests.get('http://localhost:8000/v1/opensearch/health'); print(r.json() if r.status_code == 200 else f'Error: {r.status_code}')"

# Index management
index-sample:
	@echo "📝 Indexing sample documents..."
	python -c "from scripts.create_sample_data import index_sample_data; index_sample_data()"

index-clear:
	@echo "🧹 Clearing all indexed documents..."
	python -c "import requests; r=requests.delete('http://localhost:8000/v1/opensearch/clear'); print(f'Status: {r.status_code}')"

# Search testing
search-test:
	@echo "🔍 Running search tests..."
	python -c "import requests; r=requests.post('http://localhost:8000/v1/search', json={'query': 'tuyển sinh', 'search_mode': 'hybrid'}); print(f'Found: {len(r.json().get(\"hits\", []))} results')"

# Cleanup
clean:
	@echo "🧹 Cleaning up..."
	cd docker && docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "✅ Cleanup complete!"

clean-cache:
	@echo "🧹 Cleaning Python cache..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	@echo "✅ Cache cleaned!"

# Logs
logs:
	@echo "📋 Showing service logs..."
	cd docker && docker-compose logs -f

logs-opensearch:
	@echo "📋 Showing OpenSearch logs..."
	cd docker && docker-compose logs -f opensearch

# Performance testing
perf-test:
	@echo "⚡ Running performance tests..."
	python scripts/performance_test.py

# System info
info:
	@echo "ℹ️  System Information"
	@echo "====================="
	@echo "🐍 Python: $(shell python --version)"
	@echo "🐳 Docker: $(shell docker --version 2>/dev/null || echo 'Not installed')"
	@echo "📁 Project: $(shell pwd)"
	@echo "📦 Dependencies:"
	@pip list | grep -E "(opensearch|faiss|sentence|transformers)" || echo "   No key dependencies found"

# Documentation
docs:
	@echo "📚 Documentation Links"
	@echo "====================="
	@echo "🌐 API Docs: http://localhost:8000/docs"
	@echo "🔍 OpenSearch: http://localhost:9200"
	@echo "📊 Health Check: http://localhost:8000/v1/health"
	@echo "🧪 Test endpoint: make search-test"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  1. make install"
	@echo "  2. make start"
	@echo "  3. make sample-data"
	@echo "  4. make demo"
