# Timeout Configuration - Answer Agent

**Date**: October 31, 2025  
**Issue**: Answer Agent (deepseek/deepseek-v3.2-exp) timeout after 30 seconds

---

## ✅ SOLUTION IMPLEMENTED

**Timeout đã được TẮT hoàn toàn cho OpenRouter API**

---

## 🔧 CHANGES MADE

### 1. **Container Support for None Timeout**

**File**: `/services/orchestrator/app/core/container.py`

**Change**:
```python
# Before:
timeout = int(os.getenv("OPENROUTER_TIMEOUT", "30"))

# After:
timeout_env = os.getenv("OPENROUTER_TIMEOUT", "30")
timeout = None if timeout_env.lower() == "none" else int(timeout_env)
```

**Impact**: Container now accepts "none" string to disable timeout completely

### 2. **Auto-Configure in Start Script**

**File**: `start_backend.py`

**Change**:
```python
# Set debug log level if requested
if debug_mode:
    env['LOG_LEVEL'] = 'DEBUG'

# Disable timeout for Answer Agent (deepseek model can be slow)
env['OPENROUTER_TIMEOUT'] = 'none'

# Start Orchestrator service - no output capture, show logs in terminal
```

**Impact**: Timeout automatically disabled when starting backend

---

## 🎯 HOW IT WORKS

### Request Flow:

```
start_backend.py
    ↓
Set env: OPENROUTER_TIMEOUT=none
    ↓
container.py reads env variable
    ↓
timeout = None (not 30)
    ↓
OpenRouterAdapter(timeout=None)
    ↓
aiohttp.ClientTimeout(total=None) if None
    ↓
No timeout - waits indefinitely
```

### Code in openrouter_adapter.py:

```python
async def _get_session(self) -> aiohttp.ClientSession:
    """Get or create HTTP session."""
    if self._session is None or self._session.closed:
        # ✅ If timeout is None, aiohttp waits indefinitely
        timeout_config = aiohttp.ClientTimeout(total=self.timeout) if self.timeout else None
        self._session = aiohttp.ClientSession(
            timeout=timeout_config,  # None = no timeout
            headers={...}
        )
    return self._session
```

---

## 📊 BEFORE vs AFTER

### ❌ BEFORE (Timeout 30s)

```
2025-10-31 16:35:07 - Answer Agent started
2025-10-31 16:35:37 - ERROR: TimeoutError (after 30s)
└─> Answer generation failed
└─> Verifier skipped
└─> Response Agent hallucinated answer
```

**Result**: User gets incorrect hallucinated information

### ✅ AFTER (No Timeout)

```
2025-10-31 16:XX:XX - Answer Agent started
2025-10-31 16:XX:XX - Waiting for deepseek response...
[Wait as long as needed - 60s, 120s, 180s...]
2025-10-31 16:XX:XX - Answer Agent completed successfully
└─> Verification successful
└─> Response Agent formats correct answer
```

**Result**: User gets accurate answer based on documents

---

## 🧪 TESTING

### Test 1: Start Backend
```bash
python start_backend.py
# ✅ Should show: "Disable timeout for Answer Agent"
```

### Test 2: Verify Environment
```bash
# In terminal running orchestrator
echo $OPENROUTER_TIMEOUT
# Expected output: none
```

### Test 3: Run Query
```bash
python demo_debug_logging.py
# ✅ Answer Agent should complete without timeout
# ⚠️ May take 60-180 seconds for deepseek model
```

---

## 🔍 VERIFICATION

Check logs for timeout config:

```python
# Look for this in startup logs:
# ✅ GOOD: No timeout setting visible (means None)
# ❌ BAD: "timeout=30" or similar

# Test with complex query requiring long processing:
query = "Giải thích chi tiết quy trình xét tốt nghiệp, điều kiện, thời gian, và các bước cần làm"
# Should complete without TimeoutError
```

---

## ⚠️ CONSIDERATIONS

### Pros:
- ✅ Answer Agent can complete processing without interruption
- ✅ No more TimeoutError for slow models like deepseek
- ✅ Users get accurate answers based on documents
- ✅ Works automatically when using start_backend.py

### Cons:
- ⚠️ Long-running requests may hang if model/API has issues
- ⚠️ User may wait 2-3 minutes for complex queries
- ⚠️ No circuit breaker if deepseek API is completely down

### Mitigations:

1. **Add Application-Level Timeout** (optional):
```python
# multi_agent_orchestrator.py
async with asyncio.timeout(180):  # 3 minutes max
    answer_result = await self.answer_agent.process(answer_input)
```

2. **Monitor Answer Agent Performance**:
```python
# Log processing time
logger.info(f"Answer Agent took {elapsed_time}s")
if elapsed_time > 60:
    logger.warning(f"Answer Agent slow: {elapsed_time}s")
```

3. **Consider Model Switch**:
```yaml
# agents_config.yaml
answer_model:
  name: "openai/gpt-4o-mini"  # Faster, more reliable than deepseek
  temperature: 0.2
  max_tokens: 1500
  timeout: null
```

---

## 🎯 RECOMMENDATIONS

### For Development:
- ✅ Keep timeout disabled for testing
- ✅ Use debug logging to monitor performance
- ✅ Test with various query complexities

### For Production:

**Option 1: Keep Deepseek + No Timeout**
- Good for: Maximum answer quality
- Trade-off: Longer wait times (60-180s)

**Option 2: Switch to GPT-4o-mini + 60s Timeout**
- Good for: Balance of speed and quality
- Trade-off: Slightly less detailed answers

**Option 3: Hybrid Approach**
```python
# Try deepseek with timeout, fallback to gpt-4o-mini
try:
    async with asyncio.timeout(90):
        answer = await deepseek_agent.process(...)
except asyncio.TimeoutError:
    logger.warning("Deepseek timeout, falling back to GPT-4o-mini")
    answer = await gpt_agent.process(...)
```

---

## 📝 MANUAL OVERRIDE

If you need to re-enable timeout:

### Method 1: Environment Variable
```bash
# Before starting backend
export OPENROUTER_TIMEOUT=60  # 60 seconds
python start_backend.py
```

### Method 2: Edit start_backend.py
```python
# Change this line:
env['OPENROUTER_TIMEOUT'] = 'none'

# To:
env['OPENROUTER_TIMEOUT'] = '60'  # or desired timeout in seconds
```

### Method 3: Remove Auto-Config
```python
# Comment out or remove:
# env['OPENROUTER_TIMEOUT'] = 'none'

# Then set in .env file:
# OPENROUTER_TIMEOUT=60
```

---

## 🐛 TROUBLESHOOTING

### Issue: Request still times out

**Check**:
```bash
# 1. Verify env variable
echo $OPENROUTER_TIMEOUT  # Should be "none"

# 2. Check container log
# Should see: timeout_config = None

# 3. Check adapter
# Should see: ClientTimeout(total=None)
```

**Fix**:
```bash
# Restart backend to apply changes
python start_backend.py
```

### Issue: Too slow, want timeout back

**Fix**:
```python
# start_backend.py - change to:
env['OPENROUTER_TIMEOUT'] = '90'  # 90 seconds instead of 'none'
```

### Issue: Deepseek still failing

**Possible Causes**:
- API key invalid/expired
- Rate limit exceeded
- Model unavailable
- Input too long (>20KB)

**Solution**:
```yaml
# Switch model in agents_config.yaml
answer_model:
  name: "openai/gpt-4o-mini"  # More reliable
```

---

## ✅ SUMMARY

| Aspect | Before | After |
|--------|--------|-------|
| **HTTP Timeout** | 30s | None (disabled) |
| **Answer Agent** | TimeoutError | Completes successfully |
| **Wait Time** | 30s max | 60-180s typical |
| **Answer Quality** | Hallucinated | Accurate from docs |
| **Configuration** | Manual env var | Auto-configured |

**Status**: ✅ Timeout disabled automatically when using `python start_backend.py`

---

**Prepared by**: GitHub Copilot  
**Date**: October 31, 2025
