# Update: Debug Mode Mặc Định BẬT

## Thay đổi

Debug logging giờ đây được **BẬT MẶC ĐỊNH** thay vì phải dùng flag `--debug`.

### Trước đây:
```bash
# Phải dùng --debug để bật
python start_backend.py --debug

# Mặc định là INFO level (ít log)
python start_backend.py
```

### Bây giờ:
```bash
# Debug BẬT mặc định (xem chi tiết agents)
python start_backend.py

# Dùng --no-debug để TẮT
python start_backend.py --no-debug
```

## Lý do thay đổi

1. **Dễ sử dụng hơn**: Không cần nhớ thêm flag `--debug`
2. **Phù hợp cho development**: Khi đang phát triển, bạn luôn muốn thấy logs chi tiết
3. **Học hỏi dễ dàng**: Người mới có thể thấy ngay cách hệ thống hoạt động

## Các file đã cập nhật

1. ✅ `start_backend.py` - Đổi từ `--debug` sang `--no-debug`, debug mặc định ON
2. ✅ `DEBUG_LOGGING_GUIDE.md` - Cập nhật hướng dẫn
3. ✅ `README.md` - Cập nhật quick start guide
4. ✅ `DEFAULT_DEBUG_MODE.md` - File này (NEW)

## Cách sử dụng

### Development (mặc định - có debug logs)
```bash
conda activate chatbot-UIT
python start_backend.py
```

Bạn sẽ thấy:
```
🐛 Debug mode: ENABLED (use --no-debug to disable)
```

### Production (tắt debug logs)
```bash
python start_backend.py --no-debug
```

## Tóm tắt Options

| Command | Debug Mode | Use Case |
|---------|------------|----------|
| `python start_backend.py` | ✅ ON | Development, debugging, learning |
| `python start_backend.py --no-debug` | ❌ OFF | Production, performance testing |
| `python start_backend.py --skip-docker` | ✅ ON | Dev with existing Docker |
| `python start_backend.py --skip-docker --no-debug` | ❌ OFF | Production restart |

## Lợi ích

✅ Không cần nhớ thêm flag  
✅ Luôn thấy được flow của agents  
✅ Dễ debug khi có lỗi  
✅ Học được cách agents hoạt động  
✅ Vẫn có thể tắt khi cần (--no-debug)  

## Migration

Nếu bạn đang có script tự động:

**Trước:**
```bash
python start_backend.py --debug
```

**Sau (tương đương):**
```bash
python start_backend.py
```

**Nếu muốn tắt debug:**
```bash
python start_backend.py --no-debug
```

---

**Date**: October 31, 2025  
**Status**: ✅ Complete
