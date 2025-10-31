# Fix Applied: aiohttp Timeout Issue

**Date**: October 31, 2025  
**Error**: `AttributeError: 'NoneType' object has no attribute 'total'`

---

## ❌ ROOT CAUSE

When setting `timeout=None` to disable timeout, the code was passing:
```python
timeout_config = None
aiohttp.ClientSession(timeout=None)  # ❌ aiohttp doesn't accept None
```

aiohttp internally tries to access `timeout.total`, causing:
```
File "/home/kien/anaconda3/envs/chatbot-UIT/lib/python3.11/site-packages/aiohttp/client.py", line 470
    self._loop, real_timeout.total, ceil_threshold=real_timeout.ceil_threshold
                ^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'total'
```

---

## ✅ SOLUTION

**Don't pass `timeout` parameter at all when we want no timeout**

### Before (BROKEN):
```python
async def _get_session(self) -> aiohttp.ClientSession:
    if self._session is None or self._session.closed:
        timeout_config = aiohttp.ClientTimeout(total=self.timeout) if self.timeout else None
        self._session = aiohttp.ClientSession(
            timeout=timeout_config,  # ❌ None causes error
            headers={...}
        )
    return self._session
```

### After (FIXED):
```python
async def _get_session(self) -> aiohttp.ClientSession:
    if self._session is None or self._session.closed:
        # Prepare session kwargs
        session_kwargs = {
            "headers": {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost:3000",
                "X-Title": "Chatbot-UIT"
            }
        }
        
        # Only add timeout if specified (None = no timeout)
        if self.timeout is not None:
            session_kwargs["timeout"] = aiohttp.ClientTimeout(total=self.timeout)
        
        self._session = aiohttp.ClientSession(**session_kwargs)  # ✅ No timeout param = no limit
    return self._session
```

---

## 🎯 HOW IT WORKS

1. **If timeout is set** (e.g., 30):
   ```python
   session_kwargs["timeout"] = aiohttp.ClientTimeout(total=30)
   ClientSession(**session_kwargs)  # Has 30s timeout
   ```

2. **If timeout is None**:
   ```python
   # timeout key not added to session_kwargs
   ClientSession(**session_kwargs)  # No timeout = waits indefinitely
   ```

---

## 🧪 TESTING

Restart backend and test:

```bash
# Stop current backend (Ctrl+C)
python start_backend.py

# Run test
python demo_debug_logging.py
```

**Expected**: No more `'NoneType' object has no attribute 'total'` error

---

**Status**: ✅ Fixed  
**File Modified**: `/services/orchestrator/app/adapters/openrouter_adapter.py`
