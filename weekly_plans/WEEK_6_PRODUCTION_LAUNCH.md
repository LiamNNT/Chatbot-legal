# Week 6: Production Deployment & Launch 🚀

**Duration:** Week 6 (Dec 18-24, 2025)  
**Phase:** Production Launch  
**Objective:** Deploy CatRAG to production, final polish, user training, celebration!

---

## 🎯 Week Goals

### Team A (Deployment & Infrastructure)
- 🚀 Production environment setup
- 🚀 Database migration and data population
- 🚀 Scaling configuration (horizontal/vertical)
- 🚀 Backup and disaster recovery
- 🚀 Production monitoring and alerting

### Team B (Launch Preparation)
- ✨ Final UI polish and bug fixes
- ✨ User training materials
- ✨ Launch announcement and marketing
- ✨ Support documentation
- ✨ Post-launch monitoring

### Integration Goal
- **Wednesday:** Production deployment complete  
- **Thursday:** Soft launch (limited users)  
- **Friday:** Official launch announcement! 🎉

---

## 📋 Detailed Tasks

### **Team A: Production Deployment**

#### Task A1: Production Environment Setup (Monday - 8h)
**Owner:** DevOps + Senior Backend Developer  
**Priority:** P0 (Blocker)

**Infrastructure Checklist:**

**1. Server Provisioning:**
```bash
# Production server specs (recommended)
- Application Server: 8 vCPU, 16GB RAM, 100GB SSD (x2 for redundancy)
- Neo4j Server: 8 vCPU, 32GB RAM, 500GB SSD
- Redis Cache: 4 vCPU, 8GB RAM, 50GB SSD
- PostgreSQL: 4 vCPU, 16GB RAM, 200GB SSD (for metadata)

# Or Docker Swarm/Kubernetes cluster
- Manager nodes: 3
- Worker nodes: 5+
- Load balancer: Nginx/HAProxy
```

**2. Docker Compose Production:**
```yaml
# docker-compose.prod.yml

version: '3.8'

services:
  # CatRAG API
  catrag-api:
    image: uitchatbot/catrag-api:1.0.0
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
    environment:
      - ENVIRONMENT=production
      - NEO4J_URI=bolt://neo4j-prod:7687
      - REDIS_URI=redis://redis-prod:6379
      - LOG_LEVEL=INFO
    depends_on:
      - neo4j-prod
      - redis-prod
    networks:
      - catrag-network
  
  # Neo4j Graph Database
  neo4j-prod:
    image: neo4j:5.15-enterprise
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '4'
          memory: 16G
    environment:
      - NEO4J_AUTH=neo4j/STRONG_PRODUCTION_PASSWORD
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_memory_heap_max__size=8G
      - NEO4J_dbms_memory_pagecache_size=4G
    volumes:
      - neo4j-data-prod:/data
      - neo4j-logs-prod:/logs
    networks:
      - catrag-network
  
  # Redis Cache
  redis-prod:
    image: redis:7-alpine
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '1'
          memory: 2G
    command: redis-server --maxmemory 1.5gb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data-prod:/data
    networks:
      - catrag-network
  
  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - catrag-api
    networks:
      - catrag-network

volumes:
  neo4j-data-prod:
  neo4j-logs-prod:
  redis-data-prod:

networks:
  catrag-network:
    driver: overlay
```

**3. Environment Variables:**
```bash
# .env.production

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
API_VERSION=v1

# Neo4j
NEO4J_URI=bolt://neo4j-prod:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=${NEO4J_PROD_PASSWORD}

# Redis
REDIS_URI=redis://redis-prod:6379
REDIS_PASSWORD=${REDIS_PROD_PASSWORD}

# LLM
OPENAI_API_KEY=${OPENAI_API_KEY}
LLM_MODEL=gpt-4-turbo-preview

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# Security
ALLOWED_ORIGINS=https://chatbot.uit.edu.vn
CORS_ENABLED=true
RATE_LIMIT=100/minute
```

**4. SSL/TLS Configuration:**
```nginx
# nginx/nginx.conf

upstream catrag_backend {
    least_conn;
    server catrag-api:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name chatbot.uit.edu.vn;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    
    location /api/ {
        proxy_pass http://catrag_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name chatbot.uit.edu.vn;
    return 301 https://$server_name$request_uri;
}
```

**Deliverables:**
- ✅ Production servers provisioned
- ✅ Docker Compose production config
- ✅ Nginx reverse proxy configured
- ✅ SSL certificates installed
- ✅ Environment variables secured (vault/secrets manager)

**Acceptance Criteria:**
- [ ] All services start successfully
- [ ] HTTPS working with valid certificate
- [ ] Load balancer distributes traffic
- [ ] Health checks pass on all services

---

#### Task A2: Database Migration & Population (Monday-Tuesday - 10h)
**Owner:** Backend Developer + DBA  
**Priority:** P0 (Critical)

**Migration Strategy:**

**1. Export Existing Data:**
```bash
# Export current RAG data
python scripts/export_existing_data.py \
  --source weaviate \
  --output data/migration/weaviate_export.json

# Export crawled data
python scripts/prepare_migration_data.py \
  --input data/crawled_programs/ \
  --output data/migration/graph_ready.json
```

**2. Graph Population Pipeline:**
```python
# scripts/populate_production_graph.py

import asyncio
from pathlib import Path

async def populate_production_graph():
    """Populate production Neo4j with UIT data"""
    
    print("🚀 Starting production graph population...")
    
    # Step 1: Create schema
    print("1️⃣ Creating graph schema...")
    await run_cypher_scripts([
        "scripts/cypher/01_create_constraints.cypher",
        "scripts/cypher/02_create_indexes.cypher"
    ])
    
    # Step 2: Load course data (500+ courses)
    print("2️⃣ Loading course data...")
    courses_data = load_json("data/migration/courses.json")
    await graph_builder.batch_add_courses(courses_data, batch_size=100)
    print(f"   ✅ Loaded {len(courses_data)} courses")
    
    # Step 3: Load departments and programs
    print("3️⃣ Loading departments and programs...")
    depts_data = load_json("data/migration/departments.json")
    await graph_builder.batch_add_departments(depts_data)
    print(f"   ✅ Loaded {len(depts_data)} departments")
    
    # Step 4: Extract and create prerequisite relationships
    print("4️⃣ Extracting prerequisite relationships...")
    prereq_texts = load_json("data/migration/prerequisite_texts.json")
    
    total_relations = 0
    for text_batch in batch(prereq_texts, 50):
        # Use LLM to extract relations
        relations = await llm_extractor.extract_relations_batch(text_batch)
        
        # Create relationships in graph
        await graph_builder.batch_add_relationships(relations)
        total_relations += len(relations)
        
        print(f"   Progress: {total_relations} relationships created")
    
    print(f"   ✅ Created {total_relations} prerequisite relationships")
    
    # Step 5: Load regulations
    print("5️⃣ Loading regulations...")
    regulations = load_json("data/migration/regulations.json")
    await graph_builder.batch_add_regulations(regulations)
    print(f"   ✅ Loaded {len(regulations)} regulations")
    
    # Step 6: Verify data integrity
    print("6️⃣ Verifying data integrity...")
    stats = await graph_repo.get_graph_stats()
    
    print("\n📊 Final Statistics:")
    print(f"   - Total nodes: {stats['total_nodes']}")
    print(f"   - Total relationships: {stats['total_relationships']}")
    print(f"   - MON_HOC nodes: {stats['node_counts']['MON_HOC']}")
    print(f"   - KHOA nodes: {stats['node_counts']['KHOA']}")
    print(f"   - Prerequisite relationships: {stats['rel_counts']['DIEU_KIEN_TIEN_QUYET']}")
    
    # Validation
    assert stats['node_counts']['MON_HOC'] >= 500, "Not enough courses loaded"
    assert stats['rel_counts']['DIEU_KIEN_TIEN_QUYET'] >= 300, "Not enough prerequisites"
    
    print("\n✅ Production graph population complete!")

if __name__ == "__main__":
    asyncio.run(populate_production_graph())
```

**3. Vector Store Migration:**
```python
# Migrate Weaviate data
python scripts/migrate_vector_store.py \
  --source http://localhost:8080 \
  --target http://weaviate-prod:8080 \
  --schema uit_documents \
  --batch-size 500
```

**4. Validation Queries:**
```cypher
// Verify prerequisite chains
MATCH path = (course:MON_HOC {ma_mon: 'IT003'})-[:DIEU_KIEN_TIEN_QUYET*]->(prereq)
RETURN length(path), count(*)

// Check orphaned nodes
MATCH (n)
WHERE NOT (n)--()
RETURN labels(n), count(*)

// Verify all courses have department
MATCH (m:MON_HOC)
WHERE NOT (m)-[:THUOC_KHOA]->(:KHOA)
RETURN m.ma_mon
```

**Deliverables:**
- ✅ Production graph populated (500+ courses, 300+ prerequisites)
- ✅ Vector store migrated
- ✅ Data validation report
- ✅ Rollback script (if needed)

**Acceptance Criteria:**
- [ ] 500+ courses loaded
- [ ] 300+ prerequisite relationships
- [ ] No orphaned nodes
- [ ] All validation queries pass
- [ ] Migration time: <2 hours

---

#### Task A3: Scaling & Performance Tuning (Tuesday-Wednesday - 8h)
**Owner:** DevOps + Senior Developer  
**Priority:** P1

**Horizontal Scaling:**

```bash
# Scale CatRAG API to 5 replicas
docker service scale catrag-api=5

# Auto-scaling with Kubernetes (if using K8s)
kubectl autoscale deployment catrag-api \
  --min=3 --max=10 \
  --cpu-percent=70
```

**Neo4j Performance Tuning:**

```properties
# neo4j.conf (production settings)

# Memory settings (for 32GB server)
dbms.memory.heap.initial_size=16g
dbms.memory.heap.max_size=16g
dbms.memory.pagecache.size=8g

# Transaction settings
dbms.transaction.timeout=60s
dbms.lock.acquisition.timeout=30s

# Query settings
dbms.query.cache_size=1000
cypher.min_replan_interval=5s

# Bolt connector
dbms.connector.bolt.thread_pool_min_size=50
dbms.connector.bolt.thread_pool_max_size=400

# Logging
dbms.logs.query.enabled=true
dbms.logs.query.threshold=500ms
```

**Redis Tuning:**

```bash
# redis.conf

maxmemory 4gb
maxmemory-policy allkeys-lru

# Persistence (RDB + AOF)
save 900 1
save 300 10
save 60 10000

appendonly yes
appendfsync everysec
```

**Load Balancing:**

```nginx
# nginx/upstream.conf

upstream catrag_backend {
    least_conn;
    
    server catrag-api-1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server catrag-api-2:8000 weight=1 max_fails=3 fail_timeout=30s;
    server catrag-api-3:8000 weight=1 max_fails=3 fail_timeout=30s;
    server catrag-api-4:8000 weight=1 max_fails=3 fail_timeout=30s;
    server catrag-api-5:8000 weight=1 max_fails=3 fail_timeout=30s;
    
    keepalive 32;
}
```

**Deliverables:**
- ✅ Auto-scaling configured
- ✅ Neo4j performance tuned
- ✅ Redis configured for production
- ✅ Load balancing optimized

**Acceptance Criteria:**
- [ ] Handles 500 concurrent users
- [ ] P95 latency < 500ms under load
- [ ] Auto-scaling triggers correctly
- [ ] No single point of failure

---

#### Task A4: Backup & Disaster Recovery (Wednesday - 6h)
**Owner:** DevOps  
**Priority:** P1

**Backup Strategy:**

```bash
# scripts/backup_production.sh

#!/bin/bash
set -e

BACKUP_DIR="/backups/catrag/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 1. Neo4j backup
echo "Backing up Neo4j..."
docker exec neo4j-prod neo4j-admin dump \
  --database=neo4j \
  --to=/backups/neo4j-dump.dump

docker cp neo4j-prod:/backups/neo4j-dump.dump \
  $BACKUP_DIR/neo4j-dump.dump

# 2. Redis backup
echo "Backing up Redis..."
docker exec redis-prod redis-cli SAVE
docker cp redis-prod:/data/dump.rdb \
  $BACKUP_DIR/redis-dump.rdb

# 3. PostgreSQL backup (if used)
echo "Backing up PostgreSQL..."
docker exec postgres-prod pg_dump -U postgres catrag_db > \
  $BACKUP_DIR/postgres-dump.sql

# 4. Application config
echo "Backing up configs..."
cp -r /opt/catrag/config $BACKUP_DIR/

# 5. Compress
echo "Compressing backup..."
tar -czf $BACKUP_DIR.tar.gz -C /backups $(basename $BACKUP_DIR)
rm -rf $BACKUP_DIR

# 6. Upload to S3 (optional)
aws s3 cp $BACKUP_DIR.tar.gz \
  s3://uit-catrag-backups/$(date +%Y%m%d)/

echo "✅ Backup complete: $BACKUP_DIR.tar.gz"
```

**Automated Backups:**

```bash
# /etc/cron.d/catrag-backup

# Daily backup at 2 AM
0 2 * * * /opt/catrag/scripts/backup_production.sh >> /var/log/catrag-backup.log 2>&1

# Weekly full backup on Sunday at 3 AM
0 3 * * 0 /opt/catrag/scripts/backup_full.sh >> /var/log/catrag-backup.log 2>&1
```

**Disaster Recovery Plan:**

```bash
# scripts/restore_from_backup.sh

#!/bin/bash
BACKUP_FILE=$1

echo "⚠️  WARNING: This will overwrite production data!"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled"
    exit 1
fi

# Extract backup
tar -xzf $BACKUP_FILE -C /tmp/

# Restore Neo4j
echo "Restoring Neo4j..."
docker exec neo4j-prod neo4j-admin load \
  --from=/tmp/restore/neo4j-dump.dump \
  --database=neo4j --force

# Restore Redis
echo "Restoring Redis..."
docker cp /tmp/restore/redis-dump.rdb redis-prod:/data/dump.rdb
docker restart redis-prod

echo "✅ Restore complete"
```

**Deliverables:**
- ✅ Automated backup scripts
- ✅ Disaster recovery plan
- ✅ Backup testing (restore from backup)
- ✅ Backup retention policy (30 days)

**Acceptance Criteria:**
- [ ] Daily backups automated
- [ ] Restore tested successfully
- [ ] RTO (Recovery Time Objective) < 1 hour
- [ ] RPO (Recovery Point Objective) < 24 hours

---

### **Team B: Launch Preparation**

#### Task B1: Final UI Polish & Bug Fixes (Monday-Tuesday - 10h)
**Owner:** Frontend Developer + Designer  
**Priority:** P0

**Bug Fixes from UAT:**
- Fix: Mobile responsiveness on graph visualization
- Fix: Loading spinner timing
- Fix: Error messages not displaying
- Fix: Session timeout handling

**UI Enhancements:**
- Add loading skeleton screens
- Improve error message clarity
- Add success animations
- Polish routing decision display
- Add keyboard shortcuts (Enter to send, etc.)

**Deliverables:**
- ✅ All UAT bugs fixed
- ✅ UI polish complete
- ✅ Cross-browser testing (Chrome, Firefox, Safari, Edge)
- ✅ Mobile testing (iOS, Android)

**Acceptance Criteria:**
- [ ] Zero critical bugs
- [ ] <5 minor bugs
- [ ] UI works on all major browsers
- [ ] Mobile responsive

---

#### Task B2: User Training Materials (Tuesday-Wednesday - 8h)
**Owner:** Technical Writer + Both Teams  
**Priority:** P1

**Training Materials:**

**1. User Guide:**
```markdown
# CatRAG Chatbot User Guide

## What is CatRAG?
CatRAG (Category-guided Retrieval-Augmented Generation) is an intelligent chatbot that helps UIT students find information about courses, prerequisites, regulations, and academic planning.

## How to Use

### Basic Queries
**Ask about prerequisites:**
- "Môn IT003 cần học gì trước?"
- "Điều kiện để học SE104?"

**Ask about course content:**
- "Môn IT001 học về gì?"
- "Nội dung môn Cấu trúc dữ liệu?"

**Ask for study planning:**
- "Tôi đã học IT001, IT002, tôi nên học gì tiếp?"
- "Lộ trình học cho ngành CNTT?"

### Understanding Responses
- 🔵 Blue badge = Graph search (for prerequisites)
- 🟢 Green badge = Vector search (for descriptions)
- 🟣 Purple badge = Hybrid search (for regulations)

### Tips for Better Results
1. Be specific with course codes (IT003, not "môn lập trình")
2. Use follow-up questions in same conversation
3. Check confidence score (higher = more reliable)
```

**2. Video Tutorial (5 minutes):**
- Script for screen recording
- Narration in Vietnamese
- Demonstrations of key features

**3. FAQ Document:**
- Q: "How accurate is the prerequisite information?"
- Q: "Can I trust the course recommendations?"
- Q: "What if I get an error?"

**Deliverables:**
- ✅ User guide (PDF + web page)
- ✅ Video tutorial (YouTube/internal)
- ✅ FAQ document
- ✅ Quick reference card

**Acceptance Criteria:**
- [ ] User guide covers all features
- [ ] Video tutorial < 5 minutes
- [ ] FAQ addresses common issues

---

#### Task B3: Launch Announcement (Wednesday-Thursday - 4h)
**Owner:** Marketing + Product Owner  
**Priority:** P2

**Announcement Materials:**

**1. Email to Students:**
```
Subject: 🚀 New AI-Powered Chatbot for UIT Students!

Dear UIT Students,

We're excited to announce the launch of our new CatRAG Chatbot - your intelligent assistant for academic information!

What can it do?
✅ Find course prerequisites instantly
✅ Get personalized study recommendations
✅ Search university regulations
✅ Plan your academic path

Try it now: https://chatbot.uit.edu.vn

Best regards,
UIT IT Department
```

**2. Social Media Posts:**
- Facebook post with demo video
- Zalo group announcements
- Student forum posts

**3. Website Banner:**
- Eye-catching banner on UIT homepage
- Link to chatbot

**Deliverables:**
- ✅ Email announcement drafted
- ✅ Social media posts prepared
- ✅ Website banner designed

**Acceptance Criteria:**
- [ ] Announcements scheduled for launch day
- [ ] All materials reviewed and approved

---

#### Task B4: Support & Monitoring (Thursday-Friday - Full week)
**Owner:** Both Teams  
**Priority:** P0

**Support Setup:**

**1. Support Channels:**
- Email: catrag-support@uit.edu.vn
- Telegram group: UIT CatRAG Support
- GitHub issues: For bug reports

**2. On-Call Schedule:**
```
Week 6 (Launch week):
- Monday-Wednesday: Team A (infrastructure issues)
- Thursday-Friday: Team B (user issues)
- Weekend: Rotating on-call

Post-launch (Week 7+):
- Business hours: Regular support
- After hours: Critical issues only
```

**3. Issue Triage:**
- P0 (Critical): System down, data loss → Response: 15 min
- P1 (High): Major feature broken → Response: 1 hour
- P2 (Medium): Minor bug → Response: 1 day
- P3 (Low): Enhancement request → Response: 1 week

**Deliverables:**
- ✅ Support documentation
- ✅ On-call schedule
- ✅ Issue tracking system
- ✅ Escalation procedures

**Acceptance Criteria:**
- [ ] Support channels operational
- [ ] Team responds within SLA
- [ ] Issues tracked and resolved

---

## 🎬 Launch Timeline

### **Monday-Tuesday:** Deployment Preparation
- Infrastructure setup
- Data migration
- Testing in production environment

### **Wednesday:** Production Deployment
- 9:00 AM: Final go/no-go decision
- 10:00 AM: Deploy to production
- 11:00 AM - 2:00 PM: Smoke testing
- 2:00 PM - 5:00 PM: Monitoring and adjustments

### **Thursday:** Soft Launch
- 9:00 AM: Enable access for 50 beta users
- Monitor usage and performance
- Collect feedback
- Fix any critical issues

### **Friday:** Official Launch! 🎉
- 9:00 AM: Send launch announcements
- 10:00 AM: Enable public access
- 12:00 PM: Team lunch celebration! 🍕
- 2:00 PM - 5:00 PM: Active monitoring
- 5:00 PM: Launch retrospective meeting

---

## 📊 Success Metrics (Week 1 Post-Launch)

### **Usage Metrics:**
- Target: 500+ unique users
- Target: 2000+ queries
- Target: 60%+ user satisfaction

### **Performance Metrics:**
- P95 latency < 500ms
- Uptime > 99.5%
- Error rate < 1%

### **Quality Metrics:**
- Query success rate > 90%
- Follow-up resolution > 85%
- Positive feedback > 70%

---

## 🎉 Celebration & Retrospective

### **Friday 5:00 PM: Team Retrospective**

**Topics:**
1. What went well?
2. What could be improved?
3. Key learnings
4. Next iteration plans

**Recognition:**
- Acknowledge individual contributions
- Team photo!
- Certificates of completion

---

## 🔜 Post-Launch (Week 7+)

**Immediate (Week 7-8):**
- Monitor and fix bugs
- Collect user feedback
- Optimize based on real usage

**Short-term (Month 2-3):**
- Add new features based on feedback
- Improve intent classification accuracy
- Expand knowledge base

**Long-term (Month 4-6):**
- Advanced analytics dashboard
- Multi-language support (English)
- Mobile app (optional)
- Integration with UIT student portal

---

## ✅ Final Checklist

### **Pre-Launch (Wednesday morning):**
- [ ] All services deployed to production
- [ ] Data migration complete and validated
- [ ] SSL certificates valid
- [ ] Monitoring and alerting configured
- [ ] Backups automated
- [ ] Support channels ready
- [ ] Announcement materials prepared

### **Launch Day (Friday):**
- [ ] Announcements sent
- [ ] Public access enabled
- [ ] Team on standby for support
- [ ] Monitoring dashboards open
- [ ] Incident response plan ready

### **Post-Launch (Week 7):**
- [ ] Week 1 metrics collected
- [ ] User feedback analyzed
- [ ] Bug triage completed
- [ ] Retrospective documented
- [ ] Next iteration planned

---

**🎊 Congratulations on completing the 6-week CatRAG implementation!**

From concept to production in 6 weeks - an incredible achievement for both teams. The UIT community now has an intelligent, graph-powered chatbot that will help thousands of students navigate their academic journey.

Thank you to Team A (Graph Infrastructure) and Team B (NLP/ML) for the hard work, collaboration, and dedication!

---

**Last Updated:** November 13, 2025  
**Status:** 🚀 READY FOR LAUNCH!
