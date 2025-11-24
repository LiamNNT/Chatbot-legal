# 3-Tier Config Quick Reference

## 🚀 **5-Second Changes**

### **Switch Model** (No code needed)

```bash
# Edit .env
TIER3_MODEL_ID=anthropic/claude-3.5-sonnet  # Change this line
# Restart: docker-compose restart rag_service
```

### **Update Prompt** (No code needed)

```bash
# Edit config/prompts/three_tier_prompts.yaml
tier3_rules:
  system_prompt: |
    [Your new prompt here]
# Restart: docker-compose restart rag_service
```

---

## 📋 **Available Models**

### **Tier 2 (Entity Extraction - FREE)**

```bash
# Current (FREE experimental)
TIER2_MODEL_ID=google/gemini-2.0-flash-exp:free

# Alternatives (also FREE)
TIER2_MODEL_ID=meta-llama/llama-3.1-8b-instruct:free
```

### **Tier 3 (Complex Rules - MODERATE COST)**

```bash
# Current (Best value - $0.50/1M)
TIER3_MODEL_ID=x-ai/grok-4.1-fast

# Alternatives:
TIER3_MODEL_ID=google/gemini-pro-1.5              # $1.25/1M
TIER3_MODEL_ID=anthropic/claude-3.5-sonnet        # $3.00/1M (highest quality)
TIER3_MODEL_ID=openai/gpt-4-turbo                 # $10.00/1M
```

See all: https://openrouter.ai/models

---

## 📝 **Config Files**

| File | Purpose | When to Edit |
|------|---------|-------------|
| `.env` | Model IDs, parameters | Switch models, tune temperature |
| `config/prompts/three_tier_prompts.yaml` | All prompts | Improve extraction quality |
| `config/three_tier_extraction_config.py` | Loader logic | Add new tiers/features |

---

## 🧪 **Quick Test**

```bash
# Validate config
cd services/rag_services
python config/three_tier_extraction_config.py

# Should show:
# ✅ Prompts Yaml Exists
# ✅ Tier2 Model Id Set
# ✅ Tier3 Model Id Set
# ✅ All checks passed
```

---

## 💡 **Common Tasks**

### **A/B Test Models**

```bash
# Terminal 1: Run with Grok
TIER3_MODEL_ID=x-ai/grok-4.1-fast python scripts/build_graph_phase2_rules.py --test

# Terminal 2: Run with Claude
TIER3_MODEL_ID=anthropic/claude-3.5-sonnet python scripts/build_graph_phase2_rules.py --test
```

### **Cost Estimation**

```python
from config.three_tier_extraction_config import ThreeTierConfigLoader
config = ThreeTierConfigLoader()
print(config.estimate_cost(num_pages=100))
# Output: {'total_cost': 0.16, 'savings_percent': 98.9}
```

### **Get Current Config**

```python
from config.three_tier_extraction_config import ThreeTierConfigLoader
config = ThreeTierConfigLoader()
config.print_config_summary()
```

---

## 🔧 **Troubleshooting**

### **Error: "Prompts YAML not found"**

```bash
# Check file exists
ls -la config/prompts/three_tier_prompts.yaml
# If missing, re-run setup
```

### **Error: "TIER3_MODEL_ID not set"**

```bash
# Add to .env
echo "TIER3_MODEL_ID=x-ai/grok-4.1-fast" >> .env
```

### **Prompts not updating**

```bash
# Config is cached - restart Python process
# OR restart service
docker-compose restart rag_service
```

---

## 📊 **Cost Reference**

| Document Size | Tier 1 | Tier 2 | Tier 3 (Grok) | Total |
|---------------|--------|--------|---------------|-------|
| 10 pages | $0.00 | $0.00 | $0.02 | **$0.02** |
| 100 pages | $0.00 | $0.00 | $0.16 | **$0.16** |
| 1000 pages | $0.00 | $0.00 | $1.60 | **$1.60** |

**vs Claude Sonnet**: $15 per 100 pages = **98.9% savings**

---

## ✅ **Validation Checklist**

Before deploying config changes:

- [ ] Run `python config/three_tier_extraction_config.py`
- [ ] All validation checks pass (✅✅✅✅✅✅)
- [ ] Test with 1-2 clauses (`--test` flag)
- [ ] Check cost estimate is acceptable
- [ ] Commit changes to git

---

**Last Updated**: November 20, 2025  
**Full Docs**: `docs/CLEAN_CODE_REFACTORING_3TIER_CONFIG.md`
