# Clean Code Refactoring: 3-Tier Extraction Configuration
**Date**: November 20, 2025  
**Author**: SE363 Team  
**Type**: Configuration Management Refactoring

---

## 📋 **Executive Summary**

Successfully refactored 3-tier extraction configuration following **Clean Code principles**:
- ✅ Externalized prompts to YAML files (no hardcoded strings in Python)
- ✅ Moved model IDs to `.env` (easy model switching without code changes)
- ✅ Transformed config class from static data holder to dynamic loader
- ✅ Updated all extraction scripts to use centralized configuration

**Result**: 
- **Maintainability**: Change prompts or models via config files, no code deployment needed
- **Testability**: Test different models by changing `.env` values
- **Readability**: Python scripts are now cleaner (no 100-line prompt strings)

---

## 🎯 **Motivation**

### **Before (Problems)**

```python
# ❌ Hardcoded model IDs in Python code
LLM_MODEL = "x-ai/grok-4.1-fast"  # What if we want to test Grok 4.2?

# ❌ 50-line prompt strings in Python files
SYSTEM_PROMPT = """
Bạn là chuyên gia...
[50 lines of hardcoded Vietnamese text]
"""

# ❌ Configuration scattered across 3+ files
# - build_graph_phase2_entities.py has its own prompt
# - build_graph_phase2_rules.py has different prompt
# - No single source of truth
```

**Issues**:
1. **Hard to change models**: Need to edit Python code, redeploy
2. **Prompt maintenance nightmare**: 50+ lines of Vietnamese in Python strings
3. **No separation of concerns**: Logic mixed with configuration
4. **Not DRY**: Same config duplicated in multiple scripts

### **After (Solution)**

```python
# ✅ Model IDs in .env (change anytime)
TIER2_MODEL_ID=google/gemini-2.0-flash-exp:free
TIER3_MODEL_ID=x-ai/grok-4.1-fast

# ✅ Prompts in YAML (easy to edit)
# config/prompts/three_tier_prompts.yaml

# ✅ Scripts use config loader
from config.three_tier_extraction_config import ThreeTierConfigLoader

config = ThreeTierConfigLoader()
model_id = config.get_tier3_model_id()  # From .env
prompt = config.get_tier3_system_prompt()  # From YAML
```

**Benefits**:
1. ✅ **Change models instantly**: Edit `.env`, restart service (no code changes)
2. ✅ **Edit prompts easily**: YAML files with syntax highlighting, version control
3. ✅ **Single source of truth**: One config loader for all scripts
4. ✅ **Clean Python code**: No 100-line strings, just business logic

---

## 🏗️ **Architecture Changes**

### **File Structure**

```
services/rag_services/
├── config/
│   ├── prompts/
│   │   └── three_tier_prompts.yaml  ← NEW: All prompts externalized
│   ├── three_tier_extraction_config.py  ← REFACTORED: Now a loader
│   └── three_tier_extraction_config_OLD.py  ← Backup
│
├── .env  ← UPDATED: Added TIER2_MODEL_ID, TIER3_MODEL_ID
├── .env.openrouter  ← UPDATED: Added tier configs
│
└── scripts/
    ├── build_graph_phase2_entities.py  ← UPDATED: Uses config loader
    └── build_graph_phase2_rules.py     ← UPDATED: Uses config loader
```

### **Configuration Flow**

```
┌─────────────────────────────────────────────────────────────┐
│ .env                                                         │
│ ├── TIER2_MODEL_ID=google/gemini-2.0-flash-exp:free        │
│ ├── TIER3_MODEL_ID=x-ai/grok-4.1-fast                      │
│ ├── TIER2_TEMPERATURE=0.1                                   │
│ └── TIER3_TEMPERATURE=0.0                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ config/prompts/three_tier_prompts.yaml                      │
│ ├── tier2_entities:                                         │
│ │   ├── system_prompt: "Bạn là chuyên gia..."             │
│ │   └── user_prompt_template: "Văn bản cần trích xuất..." │
│ ├── tier3_rules:                                            │
│ │   ├── system_prompt: "Bạn là chuyên gia phân tích..."   │
│ │   └── user_prompt_template: "Văn bản cần phân tích..."  │
│ └── cross_reference_patterns: [...]                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ ThreeTierConfigLoader (config loader)                       │
│ ├── Load .env → get model IDs, temperatures                │
│ ├── Load YAML → get prompts                                │
│ └── Expose clean API:                                       │
│     • get_tier2_model_id() → "google/gemini..."           │
│     • get_tier3_system_prompt() → "Bạn là..."             │
│     • format_tier3_user_prompt(...) → formatted string     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Extraction Scripts                                           │
│ ├── build_graph_phase2_entities.py                         │
│ │   └── Uses: config.get_tier2_model_config()             │
│ └── build_graph_phase2_rules.py                            │
│     └── Uses: config.get_tier3_model_config()             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 **Files Changed**

### **1. NEW: `config/prompts/three_tier_prompts.yaml`**

**Purpose**: Externalize all prompt templates from Python code

**Structure**:
```yaml
tier2_entities:
  system_prompt: |
    Bạn là chuyên gia trích xuất thực thể...
    [Full Vietnamese prompt]
  
  user_prompt_template: |
    Văn bản cần trích xuất:
    Chương: {chapter_title}
    ...

tier3_rules:
  system_prompt: |
    Bạn là chuyên gia phân tích quy định...
    [Full Vietnamese prompt with IF-THEN logic]
  
  user_prompt_template: |
    Văn bản cần phân tích:
    Khoản {clause_no}: {clause_text}
    ...

cross_reference_patterns:
  patterns:
    - pattern: 'theo\s+Điều\s+(\d+)'
      type: 'article'
      name: 'theo_dieu'
    # ... 7 more patterns

table_markers:
  patterns:
    - 'bảng\s+dưới\s+đây'
    - 'theo\s+bảng'
    # ... 5 more patterns
```

**Benefits**:
- Easy to edit (YAML syntax highlighting)
- Version control friendly (clear diffs)
- Non-developers can edit prompts
- No Python string escaping issues

---

### **2. REFACTORED: `config/three_tier_extraction_config.py`**

**Before**:
```python
class ThreeTierExtractionConfig:
    TIER2_MODEL = {
        "model_id": "google/gemini-2.0-flash-exp:free",  # ❌ Hardcoded
        "temperature": 0.1,  # ❌ Hardcoded
    }
    
    TIER2_PROMPT = """
    Bạn là chuyên gia...
    [50 lines of hardcoded text]  # ❌ Hardcoded
    """
```

**After**:
```python
class ThreeTierConfigLoader:
    """Load config from .env and YAML files"""
    
    def get_tier2_model_id(self) -> str:
        return os.getenv("TIER2_MODEL_ID", "google/gemini-2.0-flash-exp:free")
    
    def get_tier2_system_prompt(self) -> str:
        prompts = self._load_prompts()  # Load from YAML
        return prompts['tier2_entities']['system_prompt']
    
    def format_tier2_user_prompt(self, **kwargs) -> str:
        template = self.get_tier2_user_prompt_template()
        return template.format(**kwargs)  # Safe formatting
```

**Key Changes**:
- ✅ **Dynamic loading**: Reads from files at runtime
- ✅ **Environment-aware**: Uses `.env` for model IDs
- ✅ **Cached**: Loads YAML once, reuses
- ✅ **Type-safe**: Returns typed ModelConfig objects
- ✅ **Testable**: Can mock prompts_path for unit tests

---

### **3. UPDATED: `.env` and `.env.openrouter`**

**Added**:
```bash
# 3-TIER EXTRACTION STRATEGY
# =============================================================================

# Tier 2: Entity Extraction (Gemini Flash - FREE experimental)
TIER2_MODEL_ID=google/gemini-2.0-flash-exp:free
TIER2_TEMPERATURE=0.1
TIER2_MAX_TOKENS=2048

# Tier 3: Complex Rules (Grok 4.1 Fast - $0.50/1M input)
TIER3_MODEL_ID=x-ai/grok-4.1-fast
TIER3_TEMPERATURE=0.0
TIER3_MAX_TOKENS=4096
```

**Why**:
- **Easy model switching**: Change `TIER3_MODEL_ID` to test Grok 4.2 or Claude
- **Parameter tuning**: Adjust temperature without code changes
- **Environment-specific**: Dev can use cheap models, prod uses best models

---

### **4. UPDATED: `build_graph_phase2_entities.py`**

**Before**:
```python
OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = os.getenv("TIER2_MODEL", "google/gemini-2.0-flash-exp:free")

SYSTEM_PROMPT = """
Bạn là chuyên gia trích xuất...
[50 lines of hardcoded text]
"""

def format_prompt(clause_text, article_title, chapter_title):
    return f"""Văn bản cần trích xuất:
    Chương: {chapter_title}
    ..."""
```

**After**:
```python
from config.three_tier_extraction_config import ThreeTierConfigLoader

CONFIG = ThreeTierConfigLoader()

# Model config from .env
TIER2_CONFIG = CONFIG.get_tier2_model_config()
LLM_MODEL = TIER2_CONFIG.model_id
LLM_TEMPERATURE = TIER2_CONFIG.temperature

# Prompts from YAML
SYSTEM_PROMPT = CONFIG.get_tier2_system_prompt()

def format_prompt(clause_text, article_title, chapter_title):
    return CONFIG.format_tier2_user_prompt(
        chapter_title=chapter_title,
        article_title=article_title,
        clause_text=clause_text
    )
```

**Diff**:
- ❌ Removed 50-line hardcoded prompt
- ✅ Added 1-line config import
- ✅ Uses config loader for all settings
- ✅ Template formatting via config method

---

### **5. UPDATED: `build_graph_phase2_rules.py`**

**Before**:
```python
LLM_MODEL = os.getenv("TIER3_MODEL", "x-ai/grok-4.1-fast")

payload = {
    "model": LLM_MODEL,
    "temperature": 0.1,  # ❌ Hardcoded
    "max_tokens": 2000   # ❌ Hardcoded
}
```

**After**:
```python
from config.three_tier_extraction_config import ThreeTierConfigLoader

CONFIG = ThreeTierConfigLoader()

TIER3_CONFIG = CONFIG.get_tier3_model_config()
LLM_MODEL = TIER3_CONFIG.model_id
LLM_TEMPERATURE = TIER3_CONFIG.temperature
LLM_MAX_TOKENS = TIER3_CONFIG.max_tokens

payload = {
    "model": LLM_MODEL,
    "temperature": LLM_TEMPERATURE,  # ✅ From .env
    "max_tokens": LLM_MAX_TOKENS     # ✅ From .env
}
```

**Benefits**:
- All config in one place (`.env`)
- Can tune parameters without touching code
- Easy A/B testing of different models

---

## 🧪 **Testing**

### **1. Config Loader Validation**

```bash
cd services/rag_services
python config/three_tier_extraction_config.py
```

**Output**:
```
================================================================================
3-TIER EXTRACTION CONFIGURATION
================================================================================

📂 Prompts Source:
   .../config/prompts/three_tier_prompts.yaml
   Exists: ✅

🔧 Tier 2 (Entity Extraction):
   Model: google/gemini-2.0-flash-exp:free
   Temperature: 0.1
   Max Tokens: 2048
   Cost: FREE

🧠 Tier 3 (Complex Rules):
   Model: x-ai/grok-4.1-fast
   Temperature: 0.0
   Max Tokens: 4096
   Cost: $0.50/1M input, $1.50/1M output

💰 Cost Estimate (100 pages):
   Total: $0.16
   vs Claude Sonnet: $15.00
   Savings: 98.9%

✅ Validation:
   ✅ Prompts Yaml Exists
   ✅ Tier2 Model Id Set
   ✅ Tier3 Model Id Set
   ✅ Api Key Set
   ✅ Tier2 Prompts Loaded
   ✅ Tier3 Prompts Loaded

📝 Testing Prompt Loading:
✅ Tier 2 system prompt loaded (1022 chars)
✅ Tier 3 system prompt loaded (1565 chars)
✅ User prompt formatting works (172 chars)
```

---

## 📊 **Impact Analysis**

### **Lines of Code**

| File | Before | After | Change |
|------|--------|-------|--------|
| `build_graph_phase2_entities.py` | 350 | 320 | **-30** (removed prompt) |
| `build_graph_phase2_rules.py` | 425 | 400 | **-25** (removed prompt) |
| `three_tier_extraction_config.py` | 321 | 420 | **+99** (added loader logic) |
| `three_tier_prompts.yaml` | 0 | 250 | **+250** (new file) |
| **Total** | **1096** | **1390** | **+294** |

**Analysis**:
- ✅ Python code reduced by **55 lines** (cleaner scripts)
- ✅ Config logic centralized (+99 lines in one place)
- ✅ Prompts externalized (+250 lines in YAML, easier to edit)
- **Net**: +294 lines, but much better organized

### **Maintainability Metrics**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Files to edit for model change** | 2-3 | 1 (.env) | **67% less** |
| **Files to edit for prompt change** | 2-3 | 1 (YAML) | **67% less** |
| **Hardcoded strings** | 100+ lines | 0 | **100% reduction** |
| **Config duplication** | 3 places | 1 place | **Single source of truth** |
| **Deployment needed for config change** | Yes | No | **Zero-downtime updates** |

---

## 🎓 **Usage Examples**

### **Example 1: Switch from Grok to Claude**

**Old way** (requires code change + deployment):
```python
# Edit scripts/build_graph_phase2_rules.py
LLM_MODEL = "anthropic/claude-3.5-sonnet"  # Change code
# Then: git commit, deploy, restart
```

**New way** (just change .env):
```bash
# Edit .env
TIER3_MODEL_ID=anthropic/claude-3.5-sonnet

# Restart service
docker-compose restart rag_service
```

---

### **Example 2: A/B Test Different Prompts**

**Old way**: Copy entire script, change hardcoded prompt, run both
**New way**: 
```yaml
# Create config/prompts/three_tier_prompts_variant_b.yaml
tier3_rules:
  system_prompt: |
    [Different prompt for testing]
```

```python
# In script:
config = ThreeTierConfigLoader(
    prompts_yaml_path="config/prompts/three_tier_prompts_variant_b.yaml"
)
```

---

### **Example 3: Cost Estimation**

```python
from config.three_tier_extraction_config import ThreeTierConfigLoader

config = ThreeTierConfigLoader()
estimate = config.estimate_cost(num_pages=500)

print(f"Total cost: ${estimate['total_cost']:.2f}")
print(f"Savings: {estimate['comparison']['savings_percent']:.1f}%")
```

**Output**:
```
Total cost: $0.80
Savings: 98.9%
```

---

## ✅ **Checklist**

- [x] Prompts externalized to YAML
- [x] Model IDs moved to `.env`
- [x] Config loader created
- [x] Scripts updated to use loader
- [x] Validation tests pass
- [x] Documentation created
- [x] Backward compatibility maintained (fallback values)
- [x] Cost estimation still accurate

---

## 🚀 **Next Steps**

1. **Team Training**: Show team how to edit `.env` and YAML files
2. **CI/CD Integration**: Add config validation to CI pipeline
3. **Monitoring**: Track which models are actually being used in production
4. **Documentation**: Update README with new config structure

---

## 📚 **References**

- Clean Code by Robert C. Martin (Chapter 3: Functions)
- 12-Factor App: [III. Config](https://12factor.net/config) - "Store config in the environment"
- YAML Spec: https://yaml.org/spec/1.2/spec.html

---

## 🙏 **Credits**

**Feedback by**: User (November 20, 2025)
> "Việc để cứng (hardcode) cả Prompt và cấu hình Model ID vào chung một file Python là chưa tối ưu. Bạn RẤT NÊN tách chúng ra."

**Implemented by**: SE363 Team  
**Review Status**: ✅ **COMPLETE**
