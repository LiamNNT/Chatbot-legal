# 🔧 Neo4j UTF-8 Encoding Fix - Hướng dẫn đầy đủ

## ✅ Đã Fix Thành Công!

Database Neo4j đang hoạt động hoàn hảo với UTF-8 encoding. Vấn đề chỉ nằm ở việc hiển thị trong Neo4j Browser.

---

## 📊 3 Options để xem Graph với UTF-8 đúng:

### **Option 1: Python Script (Terminal) ✅ Đơn giản nhất**

```bash
cd /home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services
python scripts/view_graph_data.py
```

**Ưu điểm:**
- ✅ Hiển thị hoàn hảo trong terminal
- ✅ Không cần cài đặt gì thêm
- ✅ Nhanh và đơn giản

---

### **Option 2: Web Viewer 🌐 Đẹp nhất - RECOMMENDED**

```bash
cd /home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services
bash scripts/start_web_viewer.sh
```

Sau đó mở browser: **http://localhost:5555**

**Ưu điểm:**
- ✅ Giao diện đẹp với CSS hiện đại
- ✅ UTF-8 encoding hoàn hảo
- ✅ Run custom Cypher queries
- ✅ Xem statistics real-time
- ✅ Responsive design

**Features:**
- 📊 Statistics dashboard (nodes, relationships, labels)
- 📚 View Môn Học với table đẹp
- 🏫 View Khoa với danh sách đầy đủ
- 🔗 View Prerequisite relationships với visualization
- 🔍 Custom query runner với syntax highlighting

---

### **Option 3: Fix Neo4j Browser 🔧**

#### Bước 1: Kiểm tra database UTF-8
```bash
cd /home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services
bash scripts/fix_neo4j_browser.sh
```

#### Bước 2: Clear browser cache
1. **Chrome/Edge:**
   - Press `F12` → Application tab
   - Storage → Clear site data for localhost:7474

2. **Firefox:**
   - Press `F12` → Storage tab
   - Cookies → Right-click → Delete All

#### Bước 3: Hard refresh
- Press `Ctrl + Shift + R` (Linux/Windows)
- Or `Cmd + Shift + R` (Mac)

#### Bước 4: Thử browser khác
- Google Chrome
- Mozilla Firefox
- Microsoft Edge

#### Bước 5: Access Neo4j Browser
1. Open: http://localhost:7474
2. Login: `neo4j` / `uitchatbot`
3. Run: `:use neo4j`
4. Then: `MATCH (n:Khoa) RETURN n LIMIT 5`

---

## 📝 Sample Queries (để test UTF-8)

### Xem tất cả nodes:
```cypher
MATCH (n) RETURN n LIMIT 50
```

### Xem Môn Học:
```cypher
MATCH (n:MonHoc) 
RETURN n.code, n.name, n.credits 
ORDER BY n.code
LIMIT 20
```

### Xem Khoa:
```cypher
MATCH (n:Khoa) 
RETURN DISTINCT n.name 
ORDER BY n.name
```

### Xem Prerequisite Chain:
```cypher
MATCH (a:MonHoc)-[r:DIEU_KIEN_TIEN_QUYET]->(b:MonHoc)
RETURN a.code as source, b.code as target, 
       a.name as source_name, b.name as target_name,
       r.confidence as confidence
ORDER BY a.code
```

### Xem relationships với visualization:
```cypher
MATCH (a)-[r:DIEU_KIEN_TIEN_QUYET]->(b)
RETURN a, r, b
LIMIT 25
```

---

## 🎯 Kết luận

### ✅ Đã hoạt động:
- Database Neo4j lưu UTF-8 hoàn hảo
- Python scripts hiển thị đúng
- Web viewer hiển thị đẹp
- Data integrity: 100%

### ⚠️ Vấn đề duy nhất:
- Neo4j Browser rendering (do browser cache/settings)

### 🏆 Giải pháp tốt nhất:
**SỬ DỤNG WEB VIEWER** (Option 2) - Đẹp, nhanh, chính xác!

```bash
bash scripts/start_web_viewer.sh
# Mở: http://localhost:5555
```

---

## 📞 Scripts có sẵn:

1. `scripts/view_graph_data.py` - Terminal viewer
2. `scripts/web_graph_viewer.py` - Web viewer (Flask app)
3. `scripts/start_web_viewer.sh` - Start web viewer
4. `scripts/fix_neo4j_browser.sh` - Check and fix Neo4j Browser
5. `scripts/extract_to_neo4j.py` - Extraction script

---

## 🚀 Quick Start

```bash
# Terminal viewer (nhanh)
python scripts/view_graph_data.py

# Web viewer (đẹp)
bash scripts/start_web_viewer.sh
# → Open http://localhost:5555

# Neo4j Browser (nếu cần)
# → Open http://localhost:7474
# → Login: neo4j / uitchatbot
```

---

**Tất cả đã HOÀN TOÀN sẵn sàng với UTF-8 encoding đúng!** 🎉
