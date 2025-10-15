# Migration Guide - Container Import Update

## 📢 Thông Báo Quan Trọng

DI Container đã được di chuyển từ `core/container.py` sang `infrastructure/container.py` để tuân thủ đúng kiến trúc Ports & Adapters.

## 🔄 Cần Làm Gì?

### Bước 1: Update Imports

**❌ CŨ (Deprecated):**
```python
from core.container import get_container, get_search_service
```

**✅ MỚI (Recommended):**
```python
from infrastructure.container import get_container, get_search_service
```

### Bước 2: Tìm Tất Cả Imports Cần Update

```bash
# Tìm tất cả files import từ core.container
cd /home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services
grep -r "from core.container import" --include="*.py"
grep -r "import core.container" --include="*.py"
```

### Bước 3: Update Từng File

#### Example 1: API Facade

**File**: `adapters/api_facade.py`

```python
# ❌ Before
from core.container import get_search_service

# ✅ After  
from infrastructure.container import get_search_service
```

#### Example 2: Test Files

**File**: `tests/test_*.py`

```python
# ❌ Before
from core.container import reset_container

# ✅ After
from infrastructure.container import reset_container
```

#### Example 3: Scripts

**File**: `scripts/demo_*.py`

```python
# ❌ Before
from core.container import get_container

# ✅ After
from infrastructure.container import get_container
```

### Bước 4: Verify

```bash
# Run tests to ensure everything works
pytest tests/

# Check for deprecation warnings
python -W default::DeprecationWarning scripts/test_api.py
```

## ⚡ Quick Fix Script

Tạo script tự động update imports:

```bash
#!/bin/bash
# update_imports.sh

# Find and replace in Python files
find . -name "*.py" -type f -exec sed -i \
  's/from core\.container import/from infrastructure.container import/g' {} +

echo "✅ Updated all imports from core.container to infrastructure.container"
```

Chạy script:
```bash
chmod +x update_imports.sh
./update_imports.sh
```

## 📋 Files Commonly Affected

Thường các files sau cần update:

1. **`adapters/api_facade.py`**
2. **`app/api/deps.py`** (nếu có)
3. **`tests/test_*.py`**
4. **`scripts/demo_*.py`**
5. **`scripts/test_*.py`**

## ⏰ Timeline

- **Ngay bây giờ**: Backward compatibility được maintain (old imports vẫn hoạt động)
- **Tuần tới**: Deprecation warnings sẽ xuất hiện
- **Tháng tới**: `core/container.py` sẽ bị xóa

## ❓ FAQ

### Q: Import cũ còn hoạt động không?

**A:** Có! `core/container.py` giờ forward tất cả calls sang `infrastructure/container.py`. Tuy nhiên bạn sẽ nhận deprecation warning.

### Q: Tại sao cần di chuyển?

**A:** DI Container là "composition root" - nó biết về tất cả concrete implementations (adapters). Theo kiến trúc Ports & Adapters, nó thuộc infrastructure layer, không phải core domain layer.

### Q: Có ảnh hưởng gì đến functionality không?

**A:** KHÔNG! Functionality hoàn toàn giống nhau. Chỉ thay đổi vị trí file để kiến trúc rõ ràng hơn.

### Q: Phải update ngay không?

**A:** Không bắt buộc ngay, nhưng nên update sớm để:
- Tránh deprecation warnings
- Code rõ ràng hơn
- Tuân thủ architecture standards

## ✅ Verification Checklist

Sau khi update, verify:

- [ ] No import errors
- [ ] No deprecation warnings  
- [ ] All tests pass
- [ ] Application runs normally
- [ ] No runtime errors

## 📚 Related Documentation

- [Ports & Adapters Violations Report](./PORTS_AND_ADAPTERS_VIOLATIONS_REPORT.md)
- [Architecture Fix Summary](./ARCHITECTURE_FIX_SUMMARY.md)
- [Refactoring Complete Summary](./REFACTORING_COMPLETE_SUMMARY.md)
- [Quick Guide](./PORTS_AND_ADAPTERS_QUICK_GUIDE.md)

## 💡 Need Help?

Nếu gặp vấn đề:
1. Check deprecation warning message
2. Verify import path
3. Run tests to identify issues
4. Review documentation above

---

*Migration guide - Created 15/10/2025*
