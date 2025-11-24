# Dependency Management Strategy

**Purpose:** Ensure consistent dependencies across microservices while allowing service-specific requirements.

---

## 🎯 Strategy Overview

### Shared Dependencies
- Core libraries used by multiple services (pydantic, fastapi, etc.)
- Must maintain **version compatibility** across services

### Service-Specific Dependencies
- Libraries unique to each service
- Can have independent versions

---

## 📦 Current Services

### 1. RAG Service (`services/rag_services/`)
**Purpose:** Document indexing, vector search, graph operations

**Key Dependencies:**
```
fastapi==0.117.1
pydantic==2.11.9
opensearch-py==2.4.2
weaviate-client==4.9.3
sentence-transformers==5.1.1
PyPDF2==3.0.1

# Week 2 additions
fuzzywuzzy==0.18.0
openai>=1.0.0
google-generativeai>=0.3.0
```

### 2. Orchestrator Service (`services/orchestrator/`)
**Purpose:** Request routing, agent coordination, policy management

**Key Dependencies:**
```
fastapi==0.117.1
pydantic==2.11.9
httpx==0.27.0
PyYAML==6.0.2
```

---

## ⚠️ Version Conflicts to Watch

### Critical Shared Dependencies

| Library | RAG Service | Orchestrator | Status | Action |
|---------|-------------|--------------|--------|--------|
| `fastapi` | 0.117.1 | ? | ⚠️ Check | Sync to 0.117.1 |
| `pydantic` | 2.11.9 | ? | ⚠️ Check | Sync to 2.11.9 |
| `uvicorn` | 0.37.0 | ? | ⚠️ Check | Sync to 0.37.0 |
| `python-dotenv` | 1.1.1 | ? | ⚠️ Check | Sync to 1.1.1 |
| `PyYAML` | 6.0.2 | 6.0.2 | ✅ OK | - |
| `requests` | 2.32.5 | ? | ⚠️ Check | Sync versions |
| `httpx` | 0.27.0 | 0.27.0 | ✅ OK | - |

---

## 📝 Recommended Structure

### Option 1: Shared Base + Service Specific

```
# Root level
requirements-base.txt          # Shared dependencies
├── fastapi==0.117.1
├── pydantic==2.11.9
├── uvicorn==0.37.0
├── python-dotenv==1.1.1
└── PyYAML==6.0.2

# Service level
services/rag_services/requirements.txt
├── -r ../../requirements-base.txt
├── opensearch-py==2.4.2
├── weaviate-client==4.9.3
└── sentence-transformers==5.1.1

services/orchestrator/requirements.txt
├── -r ../../requirements-base.txt
└── # service-specific deps
```

### Option 2: Poetry/PDM (Recommended for Large Projects)

```toml
# pyproject.toml at root
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "0.117.1"
pydantic = "2.11.9"

[tool.poetry.group.rag]
optional = true
dependencies = ["opensearch-py", "weaviate-client"]

[tool.poetry.group.orchestrator]
optional = true
dependencies = []
```

---

## 🔧 Implementation Plan

### Phase 1: Audit Current Dependencies ✅

```bash
# Check RAG service
cd services/rag_services
pip list | grep -E "(fastapi|pydantic|uvicorn|httpx|yaml)"

# Check Orchestrator
cd services/orchestrator
pip list | grep -E "(fastapi|pydantic|uvicorn|httpx|yaml)"
```

### Phase 2: Create Shared Requirements

Create `requirements-base.txt` at root:

```txt
# Core Framework
fastapi==0.117.1
uvicorn==0.37.0
pydantic==2.11.9
pydantic-settings==2.11.0

# HTTP Clients
httpx==0.27.0
requests==2.32.5
aiohttp==3.12.15

# Configuration & Utilities
python-dotenv==1.1.1
PyYAML==6.0.2

# Data Processing (shared)
numpy>=1.24.0
```

### Phase 3: Update Service Requirements

**RAG Service:**
```txt
# services/rag_services/requirements.txt

# Shared dependencies
-r ../../requirements-base.txt

# Vector & Search
opensearch-py==2.4.2
rank-bm25==0.2.2
weaviate-client==4.9.3

# ML & Embeddings
sentence-transformers==5.1.1
transformers==4.56.2
torch==2.8.0

# Document Processing
PyPDF2==3.0.1

# Data Processing
pandas==2.2.3
scikit-learn==1.7.2
tqdm==4.67.1

# Week 2: Graph & LLM
fuzzywuzzy==0.18.0
python-Levenshtein==0.25.0
openai>=1.0.0
google-generativeai>=0.3.0
```

**Orchestrator:**
```txt
# services/orchestrator/requirements.txt

# Shared dependencies
-r ../../requirements-base.txt

# Orchestrator-specific
# (add any unique dependencies here)
```

### Phase 4: Testing

```bash
# Test each service independently
cd services/rag_services
pip install -r requirements.txt
python -m pytest

cd services/orchestrator
pip install -r requirements.txt
python -m pytest
```

### Phase 5: Documentation

Update README files with dependency info.

---

## 🚨 Conflict Prevention Rules

### 1. Pin Major Versions
```
# Good
fastapi==0.117.1
pydantic>=2.11.0,<3.0.0

# Avoid
fastapi>=0.100.0  # Too loose
pydantic==*        # Dangerous
```

### 2. Lock Files
```bash
# Generate lock file
pip freeze > requirements.lock

# Or use pip-tools
pip-compile requirements.in
```

### 3. Regular Audits
```bash
# Check for security vulnerabilities
pip-audit

# Check for outdated packages
pip list --outdated
```

### 4. Testing Matrix
```yaml
# .github/workflows/test.yml
strategy:
  matrix:
    python-version: [3.11, 3.12]
    service: [rag_services, orchestrator]
```

---

## 📋 Dependency Update Process

### Monthly Review Checklist

- [ ] Check for security updates (`pip-audit`)
- [ ] Review outdated packages (`pip list --outdated`)
- [ ] Test compatibility in staging
- [ ] Update shared `requirements-base.txt`
- [ ] Update service-specific requirements
- [ ] Run full test suite
- [ ] Update CHANGELOG.md
- [ ] Deploy to production

### Breaking Change Protocol

1. Create feature branch
2. Update dependencies
3. Run tests in all services
4. Fix compatibility issues
5. Update documentation
6. Create PR with migration guide
7. Review and merge
8. Announce to team

---

## 🔍 Current Action Items

### Immediate (This Week)

- [x] Create `requirements-base.txt`
- [ ] Audit orchestrator dependencies
- [ ] Sync fastapi/pydantic versions
- [ ] Test both services with shared deps
- [ ] Update documentation

### Short-term (Next Sprint)

- [ ] Implement pip-tools or Poetry
- [ ] Set up dependency vulnerability scanning
- [ ] Create dependency update CI/CD job
- [ ] Document upgrade procedures

### Long-term

- [ ] Consider monorepo tools (Nx, Turborepo)
- [ ] Evaluate dependency caching strategies
- [ ] Implement version pinning policy
- [ ] Set up automated dependency updates (Dependabot)

---

## 💡 Best Practices

### DO ✅

- Pin exact versions for shared dependencies
- Use `-r` to include shared requirements
- Document why specific versions are needed
- Test across all services before updating
- Keep a CHANGELOG for dependency changes
- Use virtual environments per service

### DON'T ❌

- Use `*` for version specifiers
- Update dependencies without testing
- Ignore security warnings
- Mix package managers (pip, conda, poetry)
- Forget to update lock files
- Install packages globally

---

## 📚 Resources

- [pip-tools](https://github.com/jazzband/pip-tools) - Requirements management
- [Poetry](https://python-poetry.org/) - Dependency management
- [pip-audit](https://pypi.org/project/pip-audit/) - Security scanning
- [Dependabot](https://github.com/dependabot) - Automated updates

---

**Last Updated:** November 19, 2025  
**Owner:** DevOps Team  
**Review Schedule:** Monthly
