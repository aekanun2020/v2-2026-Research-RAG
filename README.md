# 2026-Research-RAG — MCP สำหรับ 8 ช่วงของงานวิจัย

โครงการ [2026-Research-RAG](https://github.com/aekanun2020/2026-Research-RAG) เป็น MCP server แยกจากระบบ `tts-research` เดิม รันด้วย **Docker Compose** เชื่อมผ่าน **Streamable HTTP** และใช้ workspace ของตนเอง ตั้งแต่สำรวจหัวข้อจนถึงเตรียมส่งบทความ โดยเก็บหลักฐานต้นฉบับ ประวัติ revision และผลตรวจของนักวิจัย

**RAG ทำงานร่วมกับโมเดลของ MCP client:** server ค้นและจัดเตรียมหลักฐาน แล้ว Claude หรือ MCP client ที่เชื่อมอยู่เป็นผู้สังเคราะห์และเรียก `save_artifact` เพื่อบันทึก ไม่มีการเรียก OpenRouter หรือโมเดลภายนอกจาก server ไม่มีการใช้ GPU การคืน context จาก stage tool ไม่ได้หมายความว่าเขียนบทความเสร็จแล้ว

รุ่น **0.2.4** มี **33 tools** ค้นด้วย multilingual-e5-base แล้วเรียงหลักฐาน 50 candidates ใหม่ด้วย BGE reranker บน CPU สำหรับ semantic/hybrid เวกเตอร์ยังอยู่ใน SQLite มีรหัส document/source/chunk/manuscript และระบบจัดการ chunks ดู [สัญญา tools](docs/tools.md) และ [ที่มาโมเดล](third-party/bge-reranker-model/README.md)

[ผลตรวจของ Codex พร้อมคำถามจริง](docs/retrieval-quality-2026-09-20.md): ชุดเดิมได้ข้อความตรงอันดับแรก **9/10** จากเดิม 6/10 และมีข้อความตรงใน top 3 **10/10** จากเดิม 7/10 คำถามใหม่ที่ยังไม่ใช้เลือกนโยบายสุดท้ายผ่าน 3/4 ข้อ อ้างกลับข้อความที่ดึงจากต้นฉบับตรง 60/60 ผล แต่ยังคืนข้อความผิดเรื่องสำหรับคำถามนอกคลัง และยังพลาดคำถามใหม่เรื่องคัดลอกคำที่ไม่เคยพบตอนฝึก จึงไม่เปิดการกรองผลด้วยคะแนนอัตโนมัติ คะแนนไม่ใช่การรับรองคำตอบ

การติดตั้งในเครื่องที่ใช้ทดสอบวันที่ 20 กันยายน 2026 มี **10 papers** ที่นำเข้าผ่าน MCP และ **221 ไฟล์ต้นฉบับใน inbox** ตรวจ hash คงเดิมหลัง deploy ดู [สถานะและการรักษาข้อมูล](docs/quality-state-preservation-2026-09-20.json) มี 547 active chunks และเก็บชุดทดลองที่ไม่ active ไว้เป็นประวัติ การล้างก่อนหน้านี้เป็น [บันทึกย้อนหลัง](docs/purge-execution-2026-09-20.json)

Repository นี้เก็บโค้ด เอกสาร และผลทดสอบย้อนหลัง การ clone ใหม่ไม่มี paper ฐานข้อมูล credentials หรือไฟล์โมเดล ดู [ขอบเขตการแยก repository และที่มาของ snapshot](docs/repository-export.md)

## เอกสารและซอร์ส

- [กำลังย้ายเป็น Qdrant/Ollama และนำ SQLite ออก](docs/qdrant-migration.md) · [ที่มาของฐานที่ผู้ใช้เลือก](third-party/reference-rag/README.md)

- [Repository และขอบเขตไฟล์ที่เผยแพร่](docs/repository-export.md) · [SHA-256 ของไฟล์ต้นทางและไฟล์ที่ส่งขึ้น Git](docs/repository-export-manifest.json)

- [ปรับคุณภาพ semantic search ภาษาไทย: คำถาม ผลจริง และข้อจำกัด](docs/retrieval-quality-2026-09-20.md) · [คำถามทั้งหมด](docs/quality-cases-2026-09-20.json) · [MCP regression client](scripts/verify_retrieval_mcp.py)
- [สัญญา tools และ workflow ทั้ง 8 ช่วง](docs/tools.md)
- [ล้างข้อมูลผ่าน MCP: ขอบเขต สำรองข้อมูล และทดสอบ](docs/workspace-cleanup.md) · [ซอร์ส](src/research_rag_mcp/cleanup.py) · [ล้างทั้งหมดโดยเก็บ inbox](src/research_rag_mcp/purge.py) · [HTTP tests](tests/test_purge.py) · [ตรวจ endpoint แบบอ่านอย่างเดียว](scripts/verify_cleanup_http.py)
- [Baseline คำค้นไทย 12 ข้อจาก 10 papers พร้อมผลตรวจเดิม](docs/thai-retrieval-baseline-10-papers-2026-09-20.json)
- [นำเข้าเอกสาร: ใครทำ ผ่านอะไร และข้อมูลไปที่ไหน](docs/ingestion.md)
- [อ่าน PDF ใน inbox ก่อนนำเข้า: สัญญา tool และ regression](docs/inbox-preview.md) · [ซอร์ส](src/research_rag_mcp/inbox.py) · [HTTP tests](tests/test_inbox.py)
- [Semantic search และระบบจัดการ chunks](docs/semantic-and-chunks.md)
- [รหัส manuscript และการอ้างแต่ละ revision](docs/manuscript-identity.md)
- [การออกแบบ ขอบเขต และข้อจำกัด](docs/design.md)
- [ผลทดสอบและสิ่งที่ยังไม่ยืนยัน](docs/validation.md)
- [การรัน container และหลักฐานตรวจ](docs/container-deployment.md) · [Compose](compose.yaml) · [Dockerfile](Dockerfile) · [ค่าตั้งต้น](.env.example)
- [ต้นทาง dependencies และใบอนุญาต](third-party/README.md) · [lockfile](uv.lock)
- [ซอร์ส MCP](src/research_rag_mcp/server.py) · [การเก็บข้อมูล](src/research_rag_mcp/store.py) · [การค้น](src/research_rag_mcp/retrieval.py) · [หน้าตรวจ](src/research_rag_mcp/review.py)
- [ชุดทดสอบ](tests/) · [หลักฐานจริงที่ใช้ทดสอบ](tests/evidence/README.md)
- [MCP HTTP smoke client](scripts/smoke_http.py) · [ตรวจ migration จากรุ่นจริงเดิม](scripts/verify_migration.py)
- [โมเดล embedding ที่ pin รุ่นไว้](src/research_rag_mcp/model_manifest.json) · [ดาวน์โหลดและตรวจ hash](scripts/download_model.py) · [ระบบจัดการเอกสาร/chunks](src/research_rag_mcp/documents.py) · [semantic encoder](src/research_rag_mcp/semantic.py)

## บันทึก Q&A

- [Tools ที่สอดคล้องกับ Claim–Evidence–Gap–Research Question — 20 กันยายน 2026](Q&A/2026-09-20-230651-tools-claim-evidence-gap-research-question.md)

## รันด้วย container

สำหรับการติดตั้งใหม่ ให้ clone repository นี้ก่อน:

```sh
git clone https://github.com/aekanun2020/2026-Research-RAG.git
cd 2026-Research-RAG
```

เครื่องที่มี Compose project `codex-research-rag` ทำงานอยู่แล้ว ให้ใช้ directory และ `.data` ของการติดตั้งเดิมต่อไป การรัน Compose จาก checkout ใหม่นี้จะใช้ชื่อ project เดียวกันและอาจเปลี่ยน bind mount ไปยัง workspace ใหม่ การแยก repository ครั้งนี้ไม่ได้ย้าย runtime หรือข้อมูล ดู [สถานะการติดตั้งเดิม](docs/repository-export.md#existing-local-installation)

เปิด Docker Engine แล้วเรียกจากโฟลเดอร์นี้ สร้าง `.data` และคัดลอก `.env.example` เป็น `.env` ครั้งแรก บน macOS/Linux ตั้ง `RAG_UID` และ `RAG_GID` ให้ตรงกับ `id -u` และ `id -g` ของเจ้าของโฟลเดอร์:

```sh
mkdir -p .data
cp .env.example .env
docker compose up -d --build --wait
docker compose ps
```

หากมี `.env` อยู่แล้ว ให้ใช้ไฟล์เดิมและไม่คัดลอกทับ

Compose project ชื่อ `codex-research-rag` มีสอง container: `codex-research-rag-mcp-1` และ `codex-research-rag-review-1` ข้อมูลอยู่ที่ `.data/` บนเครื่อง และ mount เป็น `/data` ภายในทั้งสอง container การสร้าง container ใหม่ไม่ลบข้อมูลนี้

MCP endpoint: `http://127.0.0.1:8776/mcp` ใช้ Streamable HTTP จริงของ official MCP Python SDK ไม่ใช่ SSE transport รุ่นเก่า ต้องส่ง `Authorization: Bearer <token>` โดย token อยู่ที่ `.data/.http-token` ซึ่งไม่ถูก commit หรือคืนผ่าน MCP tools ภายใน container รับที่ `0.0.0.0` และ Compose เปิดพอร์ตเฉพาะ `127.0.0.1` ของเครื่อง

นำ endpoint และ header ไปตั้งใน MCP client ที่รองรับ Streamable HTTP พร้อม custom header การรองรับหน้า settings ของแต่ละ client ต้องตรวจตามรุ่นที่ใช้ คู่มือนี้ไม่อ้างว่าตรวจ Claude Desktop HTTP บนทั้งสอง OS แล้ว ทดสอบ protocol เบื้องหลังได้ด้วย:

```sh
docker compose exec mcp python /app/scripts/smoke_http.py --workspace /data
```

ตรวจสถานะและหยุดเฉพาะระบบนี้ได้ด้วย `docker compose ps` และ `docker compose stop` ส่วน `docker compose up -d --wait` ใช้เปิดใหม่ ทั้งสอง service ใช้ `restart: unless-stopped` และต้องมี Docker Engine ทำงาน

## ใช้งานจริง

1. วาง PDF, UTF-8 TXT/MD/CSV/JSON ที่มีสิทธิ์ใช้ใน `.data/inbox/`
2. ให้ client เรียก `workspace_status` → `start_project` ด้วยความสนใจและเป้าหมายที่นักวิจัยระบุจริง
3. ใช้ `search_literature` ค้น Crossref ด้วยคำค้นสาธารณะ เมื่อมีไฟล์ใน inbox ให้เรียก `preview_inbox_document` อ่านชื่อเรื่องจากต้นฉบับ แล้วใช้ `import_document` ผลค้น Crossref เป็น metadata และไม่ได้อ่าน full text แทนแล้ว
4. เรียก stage tool ที่ต้องการ ให้ client อ่านหลักฐาน สังเคราะห์ และบันทึก `save_artifact` โดยแยกข้อเสนอ ผลจริง ข้อมูลจากผู้วิจัย และสิ่งที่ยังไม่ทราบ
5. ดู URL หน้าตรวจที่พอร์ต `8777` จาก log ด้านล่าง นักวิจัยเปิด URL ที่มี token ตรวจข้อความและต้นฉบับ แล้วบันทึกการตัดสินใจ โปรแกรมไม่เปิดแอปหรือแย่งโฟกัสเอง URL เปลี่ยน token ทุกครั้งที่ review service เริ่มใหม่:

```sh
docker compose logs --tail 5 review
```

token หน้าตรวจแยกจาก token MCP และไม่เปิดให้ tools อ่าน ห้ามส่ง URL หน้าตรวจให้โมเดลเพื่อกดตรวจรับแทน การแก้ artifact สร้าง revision ใหม่และต้องตรวจใหม่ ถ้า corpus หรือ dependency เปลี่ยน ระบบแจ้ง `needs_review` และไม่ส่งออกแบบ reviewed จนแก้ครบ

6. เมื่อบันทึก `save_artifact(stage="manuscript")` จะได้ `result.id` เป็นรหัส manuscript ถาวร ใช้รหัสเดียวกันเมื่ออ่าน แก้ไข ตรวจ และส่งออก การแก้ไขต้องส่ง `artifact_id` เดิมแล้วระบบเพิ่ม `version`; manuscript คนละชิ้นได้รหัสต่างกัน รหัสและรุ่นปรากฏในหน้าตรวจและไฟล์ส่งออก ดู [รายละเอียดรหัส](docs/manuscript-identity.md)
7. ก่อนส่ง ใช้ `prepare_submission` กับ manuscript และต้นฉบับข้อกำหนดวารสาร บันทึก submission artifact ที่อ้าง manuscript รุ่นนั้นและ guideline จริง ตรวจรับแล้วจึง `export_manuscript(mode="reviewed")` ได้ manuscript, evidence JSON, cover letter, AI disclosure, checklist และ SHA-256 manifest ใน workspace/exports การส่งเข้าวารสารยังเป็นการตัดสินใจและการกระทำของนักวิจัย

## Tools ตาม 8 ช่วง

| ช่วง | Tool | ผลที่จัดเตรียม |
|---|---|---|
| 1 สำรวจหัวข้อ | `explore_topics` | หลักฐาน รายการอ่าน สถานะการค้น และโครงบันทึกหัวข้อ |
| 2 หาช่องว่าง | `map_research_gaps` | ตารางวรรณกรรมจาก literature notes และขอบเขตการค้น |
| 3 ตั้งคำถาม | `formulate_question` | หลักฐานกับข้อเสนอเดิมสำหรับคำถาม วัตถุประสงค์ ความเป็นไปได้ |
| 4 ออกแบบวิจัย | `design_study` | หลักฐานวิธีวิจัยและโครง protocol |
| 5 ดำเนินงาน | `track_execution` | protocol บันทึกกิจกรรม ข้อสังเกต และการเปลี่ยนแปลงที่บันทึกจริง |
| 6 วิเคราะห์/อภิปราย | `interpret_results` | ผลของเราแยกจากวรรณกรรม; ใช้ `summarize_dataset` คำนวณ CSV จริง |
| 7 เขียนบทความ | `draft_manuscript` | หลักฐานและ artifacts สำหรับร่าง; บันทึกแล้วส่งออก Markdown ได้ |
| 8 เตรียมส่ง | `prepare_submission` | รายการปัญหา citation/revision/review และ guideline ที่ผู้เขียนต้องตรวจ |

## สำรองและกู้คืน

```sh
docker compose exec mcp research-rag --workspace /data backup
docker compose exec mcp research-rag restore /data/backups/<snapshot> /data/restored-workspace
```

กู้คืนได้เฉพาะ directory ใหม่ ตรวจ hashes ก่อนคัดลอก รวมฐานข้อมูลและต้นฉบับที่นำเข้าแล้ว ไม่รวม inbox, exports หรือ token HTTP

## พัฒนาโดยตรงด้วย Python

ต้องมี Python 3.11 ขึ้นไปและ uv ใช้พอร์ตอื่นถ้า container กำลังทำงานอยู่:

```sh
uv sync --locked --no-editable
uv run --no-sync python scripts/download_model.py .models/multilingual-e5-base
uv run --no-sync python scripts/download_reranker.py .models/bge-reranker-v2-m3-ONNX
uv run --no-sync research-rag --workspace .data serve --port 8876
```

การรันโดยตรงรับเฉพาะ `127.0.0.1` ตามค่าเริ่มต้น และยังรองรับ `serve --transport stdio` สำหรับ client ที่ใช้ local stdio

## ทดสอบ

เตรียม PDF จริงตาม [คู่มือหลักฐานทดสอบ](tests/evidence/README.md) ก่อน เพราะ paper ไม่อยู่ใน Git ผลที่บันทึกใน `docs/` เป็นผลย้อนหลังจากการพัฒนา ไม่ใช่การรันทดสอบใหม่บนทุกเครื่องที่ clone

```sh
uv run --no-sync python -m unittest discover -s tests -v
```

Live Crossref แยกเป็น opt-in: ตั้ง environment variable `RESEARCH_RAG_LIVE_TESTS=1` แล้วรัน suite เดิม ต้องมี network และสิทธิ์เปิด local listening ports ผลทุกครั้งแยก deterministic protocol checks ออกจากการประเมินคุณภาพคำตอบของโมเดล

## ประวัติจุดพัก

- [จุดพักและขั้นตอนทำต่อ — 20 กันยายน 2026](docs/paused-2026-09-20.md) — บันทึกก่อนพัก; กลับมาทำต่อและ deploy 0.2.0 แล้ว ดูผลล่าสุดด้านบน
