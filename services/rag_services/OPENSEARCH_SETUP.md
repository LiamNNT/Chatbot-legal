# OpenSearch Setup Guide for Developers 🔍

Complete guide for setting up OpenSearch with Vietnamese language support for the Hybrid RAG system.

## 🚀 Quick Setup (Recommended)

### Option 1: Docker Compose (Easiest)
```bash
# From the rag_services directory
cd docker
docker-compose up -d opensearch

# Wait for startup
sleep 15

# Verify
curl http://localhost:9200/_cluster/health
```

### Option 2: Automated Script
```bash
# Run the complete setup
./scripts/quick_start.sh
```

### Option 3: Makefile Commands
```bash
make start          # Start all services
make opensearch-health  # Check OpenSearch status
make opensearch-create  # Create Vietnamese index
```

## 🛠️ Manual OpenSearch Setup

### 1. Prerequisites

#### System Requirements
- **Memory**: Minimum 2GB RAM for OpenSearch
- **Disk**: At least 5GB free space
- **Java**: OpenSearch requires Java 11+ (handled by Docker)
- **Docker**: Docker Engine 20.10+ and Docker Compose

#### Check Prerequisites
```bash
# Check available memory (should be >2GB)
free -h

# Check disk space
df -h

# Check Docker
docker --version
docker-compose --version
```

### 2. Docker Compose Configuration

The system includes a complete OpenSearch configuration in `docker/docker-compose.yml`:

```yaml
version: '3.8'

services:
  opensearch:
    image: opensearchproject/opensearch:2.12.0
    container_name: vietnamese-rag-opensearch
    environment:
      # Cluster settings
      - cluster.name=vietnamese-rag-cluster
      - node.name=vietnamese-rag-node
      - discovery.type=single-node
      
      # Security (disabled for development)
      - plugins.security.disabled=true
      - DISABLE_INSTALL_DEMO_CONFIG=true
      
      # Performance settings
      - "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g"
      - bootstrap.memory_lock=true
      
      # Vietnamese plugin
      - plugins.mandatory=analysis-icu
      
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
        
    ports:
      - "9200:9200"  # REST API
      - "9600:9600"  # Performance Analyzer
      
    volumes:
      - opensearch-data:/usr/share/opensearch/data
      - ./opensearch.yml:/usr/share/opensearch/config/opensearch.yml
      
    networks:
      - rag-network
      
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

volumes:
  opensearch-data:
    driver: local

networks:
  rag-network:
    driver: bridge
```

### 3. Vietnamese Language Configuration

#### Analysis ICU Plugin
The system uses the ICU Analysis plugin for Vietnamese text processing:

```yaml
# In opensearch.yml
plugins:
  - analysis-icu

# Vietnamese analyzer configuration (set via API)
analysis:
  analyzer:
    vietnamese_analyzer:
      tokenizer: icu_tokenizer
      char_filter:
        - icu_normalizer
      filter:
        - icu_folding
        - vietnamese_stop
        - lowercase
        
  filter:
    vietnamese_stop:
      type: stop
      stopwords: [và, của, trong, với, để, là, có, được, các, một, này, đó, theo, về, từ, cho, đã, sẽ, bằng, những, nhiều, cần, phải, việc, khi, nếu, mà, sau, trước, giữa, ngoài, dưới, trên]
```

### 4. Step-by-Step Manual Setup

#### Step 1: Start OpenSearch
```bash
cd /path/to/rag_services/docker
docker-compose up -d opensearch
```

#### Step 2: Wait for Startup
```bash
# Check health (wait until status is green)
while [ "$(curl -s http://localhost:9200/_cluster/health | jq -r '.status')" != "green" ]; do
  echo "Waiting for OpenSearch..."
  sleep 5
done
echo "OpenSearch is ready!"
```

#### Step 3: Verify ICU Plugin
```bash
curl http://localhost:9200/_nodes/plugins | jq '.nodes[].plugins[] | select(.name=="analysis-icu")'
```

#### Step 4: Create Vietnamese Index
```bash
# Create index with Vietnamese analyzer
curl -X PUT http://localhost:9200/vietnamese-docs \
-H "Content-Type: application/json" \
-d '{
  "settings": {
    "analysis": {
      "analyzer": {
        "vietnamese_analyzer": {
          "tokenizer": "icu_tokenizer",
          "char_filter": ["icu_normalizer"],
          "filter": ["icu_folding", "vietnamese_stop", "lowercase"]
        }
      },
      "filter": {
        "vietnamese_stop": {
          "type": "stop",
          "stopwords": ["và", "của", "trong", "với", "để", "là", "có", "được", "các", "một", "này", "đó", "theo", "về", "từ", "cho", "đã", "sẽ", "bằng", "những", "nhiều", "cần", "phải", "việc", "khi", "nếu", "mà", "sau", "trước", "giữa", "ngoài", "dưới", "trên"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "text": {
        "type": "text",
        "analyzer": "vietnamese_analyzer",
        "search_analyzer": "vietnamese_analyzer"
      },
      "title": {
        "type": "text", 
        "analyzer": "vietnamese_analyzer"
      },
      "doc_type": {"type": "keyword"},
      "faculty": {"type": "keyword"},
      "year": {"type": "integer"},
      "subject": {"type": "keyword"},
      "language": {"type": "keyword"}
    }
  }
}'
```

#### Step 5: Test Vietnamese Analysis
```bash
# Test tokenization
curl -X POST http://localhost:9200/vietnamese-docs/_analyze \
-H "Content-Type: application/json" \
-d '{
  "analyzer": "vietnamese_analyzer",
  "text": "Trường Đại học Công nghệ Thông tin"
}'
```

### 5. Production Configuration

#### Memory Settings
For production, increase memory allocation:

```yaml
environment:
  - "OPENSEARCH_JAVA_OPTS=-Xms4g -Xmx4g"  # Increase heap size
```

#### Security Configuration
Enable security for production:

```yaml
environment:
  - plugins.security.disabled=false  # Enable security
  - DISABLE_INSTALL_DEMO_CONFIG=false
```

#### Cluster Configuration
For multi-node setup:

```yaml
environment:
  - discovery.type=zen
  - discovery.seed_hosts=opensearch-node1,opensearch-node2
  - cluster.initial_cluster_manager_nodes=opensearch-node1,opensearch-node2
```

## 🧪 Testing OpenSearch Setup

### 1. Health Checks
```bash
# Cluster health
curl http://localhost:9200/_cluster/health

# Node info
curl http://localhost:9200/_nodes

# Index stats
curl http://localhost:9200/vietnamese-docs/_stats
```

### 2. Vietnamese Analysis Test
```bash
# Test Vietnamese text processing
curl -X POST http://localhost:9200/vietnamese-docs/_analyze \
-H "Content-Type: application/json" \
-d '{
  "analyzer": "vietnamese_analyzer",
  "text": "Điều kiện tuyển sinh và các quy định về tốt nghiệp"
}'
```

Expected output shows proper tokenization:
```json
{
  "tokens": [
    {"token": "điều", "start_offset": 0, "end_offset": 4},
    {"token": "kiện", "start_offset": 5, "end_offset": 10},
    {"token": "tuyển", "start_offset": 11, "end_offset": 17},
    {"token": "sinh", "start_offset": 18, "end_offset": 22},
    {"token": "quy", "start_offset": 27, "end_offset": 30},
    {"token": "định", "start_offset": 31, "end_offset": 35},
    {"token": "tốt", "start_offset": 39, "end_offset": 42},
    {"token": "nghiệp", "start_offset": 43, "end_offset": 49}
  ]
}
```

### 3. Search Test
```bash
# Index a test document
curl -X POST http://localhost:9200/vietnamese-docs/_doc/1 \
-H "Content-Type: application/json" \
-d '{
  "title": "Quy định tuyển sinh",
  "text": "Điều kiện tuyển sinh đại học năm 2024 theo quy định của Bộ Giáo dục",
  "doc_type": "regulation",
  "faculty": "CNTT",
  "year": 2024
}'

# Search test
curl -X POST http://localhost:9200/vietnamese-docs/_search \
-H "Content-Type: application/json" \
-d '{
  "query": {
    "match": {
      "text": "tuyển sinh đại học"
    }
  },
  "highlight": {
    "fields": {
      "text": {}
    }
  }
}'
```

## 🐛 Troubleshooting

### Common Issues

#### 1. OpenSearch Won't Start
```bash
# Check logs
docker logs vietnamese-rag-opensearch

# Common fixes:
# - Increase memory: vm.max_map_count
sudo sysctl -w vm.max_map_count=262144

# - Check ports
sudo netstat -tulnp | grep :9200
```

#### 2. Out of Memory Errors
```bash
# Check available memory
free -h

# Reduce heap size in docker-compose.yml:
- "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
```

#### 3. ICU Plugin Missing
```bash
# Verify plugin is installed
curl http://localhost:9200/_nodes/plugins

# If missing, the Docker image should auto-install
# Check container logs for plugin installation errors
```

#### 4. Index Creation Fails
```bash
# Check if index already exists
curl http://localhost:9200/_cat/indices

# Delete existing index if needed
curl -X DELETE http://localhost:9200/vietnamese-docs

# Recreate with proper mapping
```

### Performance Tuning

#### 1. Memory Optimization
```yaml
# In docker-compose.yml
environment:
  # Heap size (50% of container memory)
  - "OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g"
  
  # Disable swapping
  - bootstrap.memory_lock=true
```

#### 2. Indexing Performance
```yaml
# For bulk indexing
refresh_interval: "30s"
number_of_replicas: 0

# Restore after indexing
refresh_interval: "1s" 
number_of_replicas: 1
```

#### 3. Search Performance
```bash
# Enable caching
PUT /vietnamese-docs/_settings
{
  "index": {
    "cache.query.enable": true,
    "cache.request.enable": true
  }
}
```

## 📊 Monitoring

### Key Metrics to Monitor
```bash
# Cluster stats
curl http://localhost:9200/_cluster/stats

# Index performance
curl http://localhost:9200/vietnamese-docs/_stats

# Node stats
curl http://localhost:9200/_nodes/stats
```

### Performance Analyzer
Access Performance Analyzer (if enabled):
```
http://localhost:9600/_plugins/_performanceanalyzer/
```

## 🔧 Advanced Configuration

### Custom Vietnamese Stopwords
Add domain-specific stopwords:

```json
{
  "vietnamese_stop": {
    "type": "stop", 
    "stopwords": [
      "và", "của", "trong", "với", "để", "là", "có", "được",
      "sinh viên", "môn học", "tín chỉ", "học kỳ", "giảng viên"
    ]
  }
}
```

### Synonym Support
Add Vietnamese synonyms:

```json
{
  "vietnamese_synonyms": {
    "type": "synonym",
    "synonyms": [
      "CNTT,công nghệ thông tin,information technology",
      "ĐH,đại học,university", 
      "SV,sinh viên,student"
    ]
  }
}
```

### Field Boosting
Boost important fields:

```json
{
  "query": {
    "multi_match": {
      "query": "tuyển sinh",
      "fields": ["title^2", "text^1"],
      "analyzer": "vietnamese_analyzer"
    }
  }
}
```

## ✅ Verification Checklist

Before proceeding with the RAG system:

- [ ] OpenSearch is running (port 9200)
- [ ] Cluster health is green
- [ ] ICU plugin is installed
- [ ] Vietnamese analyzer works correctly
- [ ] Can create and search documents
- [ ] Memory usage is acceptable
- [ ] No error logs in containers

## 📚 References

- [OpenSearch Documentation](https://opensearch.org/docs/)
- [ICU Analysis Plugin](https://opensearch.org/docs/latest/analyzers/text-analyzers/icu/)
- [Vietnamese Text Processing](https://unicode-org.github.io/icu/userguide/locale/)
- [Docker Compose Guide](https://docs.docker.com/compose/)

---

**🎯 Once OpenSearch is set up, proceed with the RAG system using `make start` or `./scripts/quick_start.sh`**
