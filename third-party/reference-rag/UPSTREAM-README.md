# RAG MCP Server with Streamable HTTP Transport

MCP server สำหรับค้นหาเอกสาร (RAG) แบบ **Hybrid Search** (BM25 + Semantic + RRF) รองรับภาษาไทย ผ่าน **Streamable HTTP transport** (มาตรฐาน MCP ปัจจุบัน ใช้ endpoint เดียว แทน HTTP+SSE แบบเก่า) รันเป็น container ด้วย Docker

ใช้ **Qdrant** เป็น vector database และ **Ollama** (หรือ OpenAI) สำหรับสร้าง embedding — ทั้งสองตัวรวมอยู่ใน `docker-compose.yml` แล้ว — รันครั้งเดียวขึ้นมาครบทุกตัว ไม่ต้องติดตั้งแยกเอง

Repository นี้คงโปรเจกต์เดิมจาก [`2026-2025-Best-MCP/rag-mcp-server-streamablehttp`](https://github.com/aekanun2020/2026-2025-Best-MCP/tree/main/rag-mcp-server-streamablehttp) และแก้เฉพาะ MCP SDK compatibility จาก `mcp>=1.2.0` เป็น `mcp>=1.28,<2` เพื่อให้โค้ดที่ใช้ FastMCP API ของ SDK v1 ทำงานได้หลัง MCP SDK 2.x ออก

## Features

- **Streamable HTTP Transport** — ใช้ endpoint เดียว (`/mcp`) รับ POST/GET/DELETE ตามมาตรฐาน MCP ปัจจุบัน
- **Stateless** — ไม่บังคับ `Mcp-Session-Id` (คล้าย FastMCP `stateless_http=True`) ต่อ client ได้หลากหลาย
- **Hybrid Search** — รวม BM25 (keyword) + Semantic (vector) เข้าด้วยกันด้วย RRF (Reciprocal Rank Fusion)
- **Thai Language Support** — ตัดคำ/normalize ภาษาไทย (รองรับเลขไทย ๑๒๓) ด้วย PyThaiNLP
- **FastAPI + Uvicorn backend** — web framework ที่เร็วและทันสมัย
- **Docker Support** — รันเป็น container ได้ทั้งหมด

### MCP Tools (4)

| Tool | หน้าที่ |
|------|--------|
| `search_documentation` | ค้นหาเอกสารที่เก็บไว้ (รับ `query`, `limit` default 5, `search_mode` default `hybrid`) — เลือกได้ `semantic` / `bm25` / `hybrid` |
| `list_sources` | ลิสต์ source ของเอกสารทั้งหมดที่เก็บอยู่ |
| `add_directory` | เพิ่มไฟล์เอกสารทั้งโฟลเดอร์เข้าระบบ (รับ `path`) |
| `add_context` | เพิ่ม text content ตรงๆ เข้า RAG store เช่น context จาก agent (รับ `content`, `title`, `source`, `metadata`) |

## Installation

> **Prerequisites:**
> 1. ติดตั้งและเปิด **Docker Desktop** ก่อน ([Mac](https://docs.docker.com/desktop/install/mac-install/) / [Windows](https://docs.docker.com/desktop/install/windows-install/))
> 2. port **8000** (MCP server), **6333** (Qdrant) และ **11434** (Ollama) บนเครื่องว่าง
>
> **ไม่ต้องติดตั้ง Qdrant/Ollama เอง** — `docker-compose.yml` รันให้ครบทั้ง Qdrant + Ollama + MCP server และ pull `nomic-embed-text` ให้อัตโนมัติตอนรันครั้งแรก

ขั้นตอน Windows กับ Mac ต่างกันเล็กน้อย ทำตามหัวข้อของ OS ตัวเอง

---

### Windows (double-click)

**1. ดาวน์โหลดโปรเจกต์จาก GitHub**

เปิด `Command Prompt` (CMD) แล้วรัน:

```cmd
git clone https://github.com/aekanun2020/fixed-2026-rag-mcp-server-streamablehttp.git
cd fixed-2026-rag-mcp-server-streamablehttp
```

(ไม่มี Git? กดปุ่มสีเขียว **Code ▾** ที่ [หน้า repo](https://github.com/aekanun2020/fixed-2026-rag-mcp-server-streamablehttp) → **Download ZIP** → แตกไฟล์แล้วเปิดโฟลเดอร์โปรเจกต์)

**2. เริ่มรัน server**

เปิดโฟลเดอร์โปรเจกต์ใน File Explorer แล้ว **double-click ไฟล์ `start_docker.bat`**

หน้าต่าง CMD จะเปิดขึ้นมาและทำให้ทั้งหมดให้อัตโนมัติ:
- สร้าง `.env` จาก `.env.example` (ถ้ายังไม่มี)
- build Docker image
- รัน container และแสดง log สด

**3. เสร็จ**

เมื่อเห็น log ขึ้น health แล้ว server จะรันที่ **http://localhost:8000/mcp**
เปิดหน้าต่าง CMD ค้างไว้ — **ปิดหน้าต่าง = server หยุด** ถ้าจะหยุดให้ปิดหน้าต่างหรือกด `Ctrl + C`

---

### Mac (Terminal)

**1. ดาวน์โหลดโปรเจกต์จาก GitHub**

เปิด `Terminal` แล้วรัน:

```bash
git clone https://github.com/aekanun2020/fixed-2026-rag-mcp-server-streamablehttp.git
cd fixed-2026-rag-mcp-server-streamablehttp
```

**2. เริ่มรัน server**

```bash
chmod +x start_docker.sh   # ทำแค่ครั้งแรกครั้งเดียว
./start_docker.sh
```

script จะสร้าง `.env` จาก `.env.example` (ถ้ายังไม่มี), build image, รัน container และแสดง log สด

**3. เสร็จ**

เมื่อเห็น log ขึ้น health แล้ว server จะรันที่ **http://localhost:8000/mcp**
เปิด Terminal ค้างไว้ — ปิดหน้าต่าง (หรือกด `Ctrl + C`) = server หยุด

---

### Configuration

ตัวติดตั้งจะ copy [`.env.example`](.env.example) ไปเป็น `.env` ให้อัตโนมัติ โดยชี้ไปที่ service `qdrant` และ `ollama` ภายใน `docker-compose.yml` เดียวกัน:

```env
QDRANT_URL=http://qdrant:6333
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
OLLAMA_URL=http://ollama:11434
OPENAI_API_KEY=
```

`qdrant` / `ollama` คือชื่อ service ใน compose — container คุยกันผ่าน network ภายในได้เลย ไม่ต้องตั้ง Qdrant/Ollama แยกเอง

ถ้าจะใช้ OpenAI แทน Ollama ให้ตั้ง `EMBEDDING_PROVIDER=openai` และใส่ `OPENAI_API_KEY`

## Managing the container

ชื่อ container คือ **`rag-mcp-streamable-http`** — รันคำสั่งเหล่านี้จาก root ของ repository

```bash
# เช็คสถานะ / health
docker ps

# ดู log สด
docker logs -f rag-mcp-streamable-http

# หยุด server (เก็บ container ไว้ start ใหม่ได้)
docker compose stop

# เปิดใช้งานใหม่ภายหลัง
docker compose start
```

## Re-running with a new configuration

ถ้าแก้ `.env` (เช่น เปลี่ยน `QDRANT_URL` หรือ `EMBEDDING_MODEL`) ให้ apply config ใหม่ด้วยการ **rebuild + recreate** container ในที่เดิม:

```bash
docker compose up -d --build --force-recreate
```

> **ห้ามรัน `docker compose down`** — `down` จะลบ container พร้อม network (และอาจกระทบ resource อื่น) ซึ่งไม่จำเป็น
> คำสั่ง `up -d --build --force-recreate` จะ recreate container ในที่พร้อม `.env`/config ใหม่ให้อยู่แล้ว — ใช้แค่คำสั่งนี้คำสั่งเดียว

## ดูและล้างข้อมูลใน Qdrant

ข้อมูลเอกสาร (vector) เก็บอยู่ใน collection ชื่อ **`documentation`** บน Qdrant (port 6333) — สั่งคำสั่งได้ตรงด้วย curl

### ดูจำนวนข้อมูล

```bash
# จำนวน points และโครงสร้าง collection
curl -s http://localhost:6333/collections/documentation | python3 -m json.tool
# ดู points_count — ถ้ามากกว่า 0 คือมีข้อมูลเก็บอยู่

# ดูรายการ collection ทั้งหมด
curl -s http://localhost:6333/collections | python3 -m json.tool
```

### ล้างข้อมูล — วิธีที่แนะนำ (ไม่ทำลายโครงสร้าง)

ลบเฉพาะ **points** ข้างใน — collection (vector size 768, Cosine, HNSW config) **ยังอยู่ครบ** ไม่ต้อง recreate container:

```bash
curl -X POST "http://localhost:6333/collections/documentation/points/delete?wait=true" \
  -H "Content-Type: application/json" \
  -d '{"filter": {}}'
```

✅ หลังลบ server ใช้งานต่อได้ทันที (add/search) — ไม่ต้องรีสตาร์ตอะไร นี่คือวิธีที่แนะนำสำหรับ reset ข้อมูล

> **หมายเหตุ (BM25 index):** Qdrant (vector) จะว่างทันที แต่ BM25 index ในหน่วยความจำของ server จะยังจำของเก่าจนกว่าจะ `add` ข้อมูลชุดใหม่ หรือ restart container — ถ้าอยากล้าง BM25 ให้หมดจริงๆ ให้ `docker compose restart mcp-server` หลังลบ points

### ลบทั้ง collection — รีเซ็ตสุด (ต้อง recreate container)

ถ้าอยากล้างแบบหมดจดรวมโครงสร้าง collection:

```bash
# 1. ลบทั้ง collection
curl -X DELETE http://localhost:6333/collections/documentation

# 2. ต้อง recreate container เพราะ server สร้าง collection แค่ตอน startup
docker compose up -d --force-recreate mcp-server
```

> **ระวัง:** ถ้า `DELETE` ทั้ง collection แล้ว**ไม่** recreate container — การเรียก add/search ครั้งถัดไปจะได้ error `404 Collection doesn't exist` เพราะ server สร้าง collection เฉพาะตอน startup เท่านั้น
> ถ้าแค่ reset ข้อมูลธรรมดา — ใช้วิธี“ล้าง points”ด้านบนจะสะดวกกว่า (ไม่ต้อง recreate)

## API Endpoints

`/mcp` เป็น endpoint เดียวของ Streamable HTTP รองรับ 3 method:

| Method / Path | หน้าที่ |
|---------------|--------|
| `POST /mcp` | รับ JSON-RPC message ของ MCP (ตัวหลักที่ใช้สื่อสาร) |
| `GET /mcp` | เปิด SSE stream — ต้องส่ง `Accept: text/event-stream` ไม่งั้นคืน **405** ตาม spec |
| `DELETE /mcp` | ปิด session — คืน **204** ถ้ามี session, **404** ถ้าไม่มี |
| `GET /health` | Health check (ใช้โดย Docker healthcheck) |
| `GET /` | ข้อมูล service และรายการ endpoint |

### Session handling (stateless)

Server ทำงานแบบ **stateless** (คล้าย FastMCP `stateless_http=True`):
ตอน `initialize` จะ mint `Mcp-Session-Id` ส่งกลับมาใน response header ไว้ให้ client ที่ต้องการใช้ (optional)
แต่ request ถัดไป (`tools/list`, `tools/call`) จะคืน JSON response ตรงๆ **โดยไม่บังคับ** header นี้
ทำให้ client ที่ไม่ได้ส่ง session id กลับมา (เช่น Streamable HTTP path ของ PyClaw) ต่อได้โดยไม่ต้องแก้อะไร

> **Note:** server รันที่ port **8000** ทั้งภายใน container และ expose ออกมาภายนอก (ตรงกับ rag-mcp-server-v3) — Qdrant อยู่ที่ 6333, Ollama อยู่ที่ 11434 (รันจาก compose เดียวกัน)

## MCP Client Configuration

สำหรับ Claude Desktop หรือ MCP client อื่นๆ ให้ต่อผ่าน `mcp-remote` (มันทำหน้าที่ bridge จาก Streamable HTTP server ไปเป็น stdio ที่ client เหล่านี้ต้องการ):

```json
{
  "mcpServers": {
    "rag-streamable-http": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--allow-http"
      ]
    }
  }
}
```

ถ้า client อยู่คนละเครื่องกับ server ให้เปลี่ยน `localhost` เป็น IP ของ server (เช่น LAN หรือ Tailscale address) ส่วน `--allow-http` จำเป็นเพราะ server เสิร์ฟผ่าน HTTP ธรรมดา ไม่ใช่ HTTPS

## วิธีใช้งาน (Usage)

> 📘 **อยากทดสอบทีละขั้นแบบ copy คำสั่งได้เลย?** ดู [TESTING_GUIDE.md](TESTING_GUIDE.md) — คู่มือทดสอบ 5 ขั้น (health → initialize → tools/list → add_directory → search ทั้ง 3 mode) พร้อม output จริงและคำอธิบาย score/log

หลัง server รันแล้ว ใช้งานได้ 2 ทาง: ผ่าน **MCP client** (เช่น Claude Desktop, PyClaw) หรือ **เรียกตรงด้วย curl** เพื่อทดสอบ

### ขั้นตอนใช้งานพื้นฐาน

1. **ใส่เอกสารเข้าระบบก่อน** — ใช้ `add_directory` (ทั้งโฟลเดอร์) หรือ `add_context` (text ตรงๆ) เอกสารจะถูกแปลงเป็น vector เก็บใน Qdrant และ index ลง BM25 ไปพร้อมกัน
2. **ค้นหาด้วย `search_documentation`** — ใส่ `query` แล้วระบบจะค้นแบบ **Hybrid** (BM25 + Semantic + RRF) ให้อัตโนมัติ
3. ถ้าต้องการบังคับโหมด ให้ใส่ `search_mode` เป็น `semantic`, `bm25` หรือ `hybrid`

> **ผ่าน MCP client:** แค่พิมพ์สั่ง AI ว่า "ค้นหาเอกสารเรื่อง..." client จะเรียก `search_documentation` ให้เอง — ได้ Hybrid โดยอัตโนมัติ ไม่ต้องตั้งค่าอะไรเพิ่ม

### ค้นหา (default = Hybrid)

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
    "params": {
      "name": "search_documentation",
      "arguments": { "query": "Hybrid Search ภาษาไทย", "limit": 5 }
    }
  }'
```

### เลือกโหมดค้นหา (semantic / bm25 / hybrid)

เพิ่ม `search_mode` ใน `arguments`:

```bash
# BM25 อย่างเดียว (keyword/exact match — เหมาะกับเลขข้อ เลขไทย ๒๑)
# เปลี่ยนเป็น "semantic" สำหรับ vector search ล้วน หรือ "hybrid" สำหรับรวมทั้งสอง (ค่าเริ่มต้น)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
    "params": {
      "name": "search_documentation",
      "arguments": { "query": "ข้อ ๘๖", "limit": 3, "search_mode": "bm25" }
    }
  }'
```

| `search_mode` | ค้นแบบ | score ที่ได้ |
|---------------|--------|-------------|
| `hybrid` (default) | BM25 + Semantic รวมด้วย RRF | RRF score (เลขน้อย เช่น 0.0x — ปกติของ RRF) |
| `semantic` | Dense vector อย่างเดียว | cosine similarity (0–1) |
| `bm25` | Sparse keyword อย่างเดียว | BM25 score (keyword match) |

### เพิ่มเอกสาร

```bash
# add_directory — ทั้งโฟลเดอร์ (path ต้องเป็น path ภายใน container เช่น /home/mcpuser/documents)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"add_directory","arguments":{"path":"/home/mcpuser/documents"}}}'

# add_context — ใส่ text ตรงๆ
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"add_context","arguments":{"content":"เนื้อหา...","title":"หัวข้อ","source":"agent"}}}'
```

### ดู log ยืนยันว่า Hybrid ทำงานจริง

```bash
docker logs -f rag-mcp-streamable-http
```

ตอน startup จะเห็น BM25 index ถูกสร้าง และตอนค้นหาจะเห็นทั้ง BM25 และ Semantic ทำงาน:

```
SearchOrchestrator initialized with default_mode=hybrid
✅ BM25 index built successfully with N documents
Search request: query='...', mode=hybrid
BM25 search returned X results (max_score=...)
Hybrid search returned Y results (BM25: X, Semantic: X)
```

## License

MIT
