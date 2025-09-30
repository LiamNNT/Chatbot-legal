# Hướng Dẫn Cài Đặt OpenSearch cho Hybrid RAG System

## 📋 Tổng Quan

Hướng dẫn này sẽ giúp bạn cài đặt và cấu hình OpenSearch để sử dụng với hệ thống RAG Hybrid (BM25 + Vector + Cross-Encoder).

## 🔧 Yêu Cầu Hệ Thống

- **RAM**: Tối thiểu 2GB, khuyến nghị 4GB+
- **Disk**: Tối thiểu 4GB trống
- **OS**: Linux, macOS, hoặc Windows
- **Java**: OpenJDK 11 hoặc 17 (tự động cài với Docker)

## 🐳 Cài Đặt OpenSearch với Docker (Khuyến Nghị)

### 1. Tạo Docker Compose File

Tạo file `docker-compose.opensearch.yml`:

```yaml
version: '3'
services:
  opensearch-node1:
    image: opensearchproject/opensearch:2.12.0
    container_name: opensearch-node1
    environment:
      - cluster.name=opensearch-cluster
      - node.name=opensearch-node1
      - discovery.seed_hosts=opensearch-node1
      - cluster.initial_cluster_manager_nodes=opensearch-node1
      - bootstrap.memory_lock=true
      - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
      - "DISABLE_INSTALL_DEMO_CONFIG=true"
      - "DISABLE_SECURITY_PLUGIN=true"
    ulimits:
      memlock:
        soft: -1
        hard: -1
      nofile:
        soft: 65536
        hard: 65536
    volumes:
      - opensearch-data1:/usr/share/opensearch/data
    ports:
      - 9200:9200
      - 9600:9600
    networks:
      - opensearch-net

  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:2.12.0
    container_name: opensearch-dashboards
    ports:
      - 5601:5601
    expose:
      - "5601"
    environment:
      - 'OPENSEARCH_HOSTS=["http://opensearch-node1:9200"]'
      - "DISABLE_SECURITY_DASHBOARDS_PLUGIN=true"
    networks:
      - opensearch-net

volumes:
  opensearch-data1:

networks:
  opensearch-net:
```

### 2. Khởi Động OpenSearch

```bash
# Khởi động OpenSearch
docker-compose -f docker-compose.opensearch.yml up -d

# Kiểm tra trạng thái
docker-compose -f docker-compose.opensearch.yml ps

# Xem logs
docker-compose -f docker-compose.opensearch.yml logs -f opensearch-node1
```

### 3. Kiểm Tra Kết Nối

```bash
# Kiểm tra OpenSearch API
curl -X GET "localhost:9200/_cluster/health?pretty"

# Kết quả mong đợi:
# {
#   "cluster_name" : "opensearch-cluster",
#   "status" : "green",
#   "timed_out" : false,
#   ...
# }
```

### 4. Truy Cập OpenSearch Dashboards

- URL: http://localhost:5601
- Không cần đăng nhập (security disabled)

## 🖥️ Cài Đặt OpenSearch Trực Tiếp (Alternative)

### Ubuntu/Debian

```bash
# 1. Cài đặt Java
sudo apt update
sudo apt install openjdk-11-jdk

# 2. Thêm OpenSearch repository
curl -o- https://artifacts.opensearch.org/publickeys/opensearch.pgp | sudo gpg --dearmor --batch --yes -o /usr/share/keyrings/opensearch-keyring
echo "deb [signed-by=/usr/share/keyrings/opensearch-keyring] https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/apt stable main" | sudo tee /etc/apt/sources.list.d/opensearch-2.x.list

# 3. Cài đặt OpenSearch
sudo apt update
sudo apt install opensearch

# 4. Cấu hình
sudo nano /etc/opensearch/opensearch.yml
```

### CentOS/RHEL

```bash
# 1. Cài đặt Java
sudo yum install java-11-openjdk

# 2. Thêm repository
sudo curl -SL https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/opensearch-2.12.0-linux-x64.rpm -o opensearch-2.12.0-linux-x64.rpm

# 3. Cài đặt
sudo yum install opensearch-2.12.0-linux-x64.rpm

# 4. Cấu hình
sudo nano /etc/opensearch/opensearch.yml
```

### macOS

```bash
# Sử dụng Homebrew
brew install opensearch

# Hoặc tải về trực tiếp
wget https://artifacts.opensearch.org/releases/bundle/opensearch/2.12.0/opensearch-2.12.0-darwin-x64.tar.gz
tar -xzf opensearch-2.12.0-darwin-x64.tar.gz
cd opensearch-2.12.0
```

## ⚙️ Cấu Hình OpenSearch cho RAG

### 1. File Cấu Hình Cơ Bản

Tạo/sửa file `opensearch.yml`:

```yaml
# Cluster
cluster.name: rag-opensearch-cluster
node.name: rag-node-1

# Network
network.host: 0.0.0.0
http.port: 9200
discovery.type: single-node

# Memory
bootstrap.memory_lock: true

# Security (disable cho development)
plugins.security.disabled: true

# Performance tuning for RAG
indices.query.bool.max_clause_count: 10000
search.max_buckets: 65536
```

### 2. Cấu Hình JVM (quan trọng)

File `jvm.options`:

```bash
# Heap size (tùy chỉnh theo RAM của bạn)
-Xms1g
-Xmx1g

# GC tuning
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
```

### 3. Khởi Động Service

```bash
# Ubuntu/Debian
sudo systemctl enable opensearch
sudo systemctl start opensearch
sudo systemctl status opensearch

# Manual start
cd opensearch-2.12.0
./bin/opensearch
```

## 🔌 Cấu Hình RAG Service

### 1. Cập nhật Environment Variables

Tạo file `.env` trong thư mục RAG service:

```env
# OpenSearch Configuration
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_INDEX=rag_documents
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=admin
OPENSEARCH_USE_SSL=false
OPENSEARCH_VERIFY_CERTS=false

# Hybrid Search Configuration
USE_HYBRID_SEARCH=true
BM25_WEIGHT=0.5
VECTOR_WEIGHT=0.5
RRF_RANK_CONSTANT=60
```

### 2. Cài Đặt Python Dependencies

```bash
cd services/rag_services
pip install opensearch-py==2.4.2 rank-bm25==0.2.2
```

### 3. Test Kết Nối

```python
# Test script
python -c "
from store.opensearch.client import get_opensearch_client
client = get_opensearch_client()
print('Health:', client.health_check())
print('Stats:', client.get_index_stats())
"
```

## 📊 Đồng Bộ Dữ Liệu

### 1. Sync Documents từ Vector Store sang OpenSearch

```bash
cd services/rag_services
python scripts/sync_to_opensearch.py
```

### 2. Kiểm Tra Indexing Status

```bash
# Qua API
curl "http://localhost:8000/v1/opensearch/stats"

# Trực tiếp OpenSearch
curl "http://localhost:9200/rag_documents/_count"
```

## 🧪 Test Hybrid Search

### 1. Chạy Test Suite

```bash
cd services/rag_services
python scripts/test_hybrid_search.py
```

### 2. Test API Endpoints

```bash
# Health check
curl "http://localhost:8000/v1/opensearch/health"

# BM25 search
curl -X POST "http://localhost:8000/v1/opensearch/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "thông tin tuyển sinh",
    "size": 5
  }'

# Hybrid search
curl -X POST "http://localhost:8000/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "học tập tại trường đại học",
    "top_k": 5,
    "search_mode": "hybrid",
    "use_rerank": true
  }'
```

## 🔧 Troubleshooting

### Lỗi Thường Gặp

1. **Out of Memory**
   ```bash
   # Tăng heap size trong jvm.options
   -Xms2g
   -Xmx2g
   ```

2. **Port Already in Use**
   ```bash
   # Kiểm tra process sử dụng port
   sudo lsof -i :9200
   # Kill process nếu cần
   sudo kill -9 <PID>
   ```

3. **Permission Denied**
   ```bash
   # Fix ownership
   sudo chown -R opensearch:opensearch /var/lib/opensearch
   sudo chmod -R 755 /var/lib/opensearch
   ```

4. **Connection Refused**
   - Kiểm tra firewall: `sudo ufw allow 9200`
   - Kiểm tra bind address trong config
   - Verify service status: `sudo systemctl status opensearch`

### Monitoring

```bash
# System resources
htop
df -h

# OpenSearch logs
tail -f /var/log/opensearch/opensearch.log

# Docker logs
docker logs opensearch-node1 -f
```

## 🚀 Tối Ưu Performance

### 1. Index Settings cho RAG

```json
PUT /rag_documents/_settings
{
  "index": {
    "refresh_interval": "30s",
    "number_of_replicas": 0,
    "max_result_window": 50000
  }
}
```

### 2. Mapping Optimization

```json
PUT /rag_documents
{
  "mappings": {
    "properties": {
      "text": {
        "type": "text",
        "analyzer": "standard",
        "index_options": "freqs"
      }
    }
  }
}
```

## 📈 Giám Sát Hệ Thống

### 1. OpenSearch Dashboards

- URL: http://localhost:5601
- Tạo index patterns cho monitoring
- Setup visualizations cho search metrics

### 2. API Monitoring

```bash
# Cluster health
GET /_cluster/health

# Index stats
GET /rag_documents/_stats

# Search performance
GET /_nodes/stats/indices/search
```

## ✅ Checklist Hoàn Thiện

- [ ] OpenSearch running on port 9200
- [ ] Dashboards accessible on port 5601
- [ ] RAG service connects successfully
- [ ] Documents synced to OpenSearch
- [ ] Hybrid search API working
- [ ] Cross-encoder reranking functional
- [ ] Performance monitoring setup

## 🔗 Tài Liệu Tham Khảo

- [OpenSearch Documentation](https://opensearch.org/docs/)
- [OpenSearch Docker Guide](https://opensearch.org/docs/latest/install-and-configure/install-opensearch/docker/)
- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
