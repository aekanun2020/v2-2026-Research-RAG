# 2026-Research-RAG — งานวิจัย 8 ช่วงผ่าน MCP

กำลังพัฒนารุ่น **0.4.0 บน branch `codex/academic-paper-chunking`** ตามฐาน [fixed-2026-rag-mcp-server-streamablehttp](https://github.com/aekanun2020/fixed-2026-rag-mcp-server-streamablehttp/tree/5e5373a7a0919201b44f5aa78edad069a09974db) ที่ผู้ใช้เลือก: **Qdrant + Ollama + PyThaiNLP/BM25 + RRF** รันบน CPU ใน Docker และเชื่อมผ่าน Streamable HTTP

รุ่นใหม่ **ไม่ใช้ SQLite เก็บข้อมูลหรือค้นหา** เวกเตอร์อยู่ใน Qdrant ส่วนเอกสาร รหัส chunks ประวัติ manuscript และผลตรวจอยู่ใน JSON journal ที่ล็อกข้าม process และบันทึกแต่ละ revision แบบ atomic ขั้นย้ายครั้งเดียวอ่าน SQLite เดิมแบบ read-only ผ่าน MCP เพื่อรักษารหัสและหลักฐาน ไม่มี SQLite เป็น backend สำรอง

**ผลทดสอบ 0.4.0:** chunking ผ่านกรณีเดิมและกรณีข้างเคียง โดย workflow ผ่าน 61 checks ผ่าน MCP จริง ชุดใหม่ว่าง ณ จบการล้างข้อมูลทดสอบ (เป็นสถานะย้อนหลัง) ต่อมาที่ revision 51 มี 12 papers / 907 chunks; [Codex สุ่มอ่าน 10 chunks](docs/chunk-readability-codex-2026-09-21.md) พบข้อจำกัดเรื่องบริบทข้ามหน้า ตาราง และบรรณานุกรม จึงไม่ถือว่า workflow checks รับรองความได้ใจความของทุก chunk ส่วนผล hybrid พร้อมกัน 12 คำขอและ semantic ไทย→อังกฤษเป็นผลย้อนหลังของ 0.3.0: คำขอสำเร็จครบ แต่คุณภาพ semantic ของโมเดล nomic-embed-text เดิม **ไม่ผ่าน** งาน chunking นี้ยังไม่ได้เปลี่ยนโมเดล

ระบบค้นนี้ไม่มี BGE reranker ตามฐานที่เลือก ผลคุณภาพรุ่น 0.2.4 จึงเป็นหลักฐานย้อนหลัง ไม่ใช่คะแนนของรุ่นใหม่ ดู [สถานะการย้าย ผลก่อนแก้ และการตรวจรับ](docs/qdrant-migration.md) ขณะเอกสารนี้ระบุว่า “กำลังพัฒนา” ยังไม่ถือว่าผ่านการตรวจคุณภาพ semantic ภาษาไทย

**บริการรุ่นเดิม 0.3.0:** ผู้ใช้สั่งลบ container รุ่นเดิมทั้งสองตัวเมื่อ 21 กันยายน 2026 แล้ว ชุดใหม่ `codex-research-rag-next` ยังทำงานที่ `http://127.0.0.1:8876/mcp` โดยไม่มี token ดู [บันทึกการนำบริการเดิมออก](docs/qdrant-migration.md#old-container-removal-2026-09-21)

**ประวัติการล้างรุ่นเดิม 0.3.0:** การล้างเมื่อ 21 กันยายน 2026 ทำให้ revision 38 ว่าง โดยเก็บ PDF ต้นฉบับ 22 ไฟล์และ backup ไว้ ต่อมาในการตรวจแบบอ่านอย่างเดียวระหว่างงาน chunking พบ revision 50 มี 12 เอกสาร/1,490 chunks แล้ว งาน branch นี้ไม่ได้เป็นผู้นำเข้าเหล่านั้น ดู [ผลการล้างและการตรวจผ่าน MCP](docs/qdrant-cleared-2026-09-21.json)

**ชุด chunking แยก:** `codex-rag-chunking` เปิด MCP ที่ `http://127.0.0.1:8976/mcp` และหน้าตรวจที่ port 8977 มี MCP, review, Qdrant และ Ollama ของตัวเอง พร้อม network/volumes และ `.chunking-data` แยกจากรุ่นเดิมทั้งหมด [รายละเอียด chunking และผลตรวจ](docs/academic-chunking.md) · [หลักฐานการแยก containers](docs/chunking-container-isolation-2026-09-21.json)

MCP server จัดเตรียมหลักฐาน โมเดลใน client เป็นผู้สังเคราะห์ ไม่มีการเรียก OpenRouter หรือโมเดลภายนอกเพื่อเขียน/ตัดสินคำตอบ นักวิจัยตรวจต้นฉบับและตัดสินใจผ่านหน้าตรวจแยก การแก้ manuscript สร้าง revision ใหม่และต้องตรวจรับใหม่

## เอกสารและซอร์ส

- [Academic chunking 0.4.0](docs/academic-chunking.md) · [LlamaIndex/tokenizer provenance](third-party/chunking/README.md) · [Compose ชุดแยก](compose.chunking.yaml) · [chunking implementation](src/research_rag_mcp/chunking.py)
- [Codex ประเมินความได้ใจความของ 10 chunks ที่สุ่มจริง](docs/chunk-readability-codex-2026-09-21.md) · [ตัวอย่างเต็ม ตำแหน่งอ้างอิง และ seed](docs/chunk-readability-sample-2026-09-21.json)

- [การย้าย Qdrant และผลทดสอบจริง](docs/qdrant-migration.md) · [endpoint ไม่มี token ที่ตรวจแล้ว](docs/qdrant-final-endpoint-2026-09-21.json) · [MCP migration verifier](scripts/verify_qdrant_migration_mcp.py) · [ทดสอบค้นพร้อมกัน](scripts/verify_qdrant_retrieval_mcp.py) · [ทดสอบ workflow](scripts/verify_qdrant_workflow_mcp.py)
- [สัญญา tools และ workflow ทั้ง 8 ช่วง](docs/tools.md)
- [การนำเข้าและผู้รับผิดชอบ](docs/ingestion.md) · [อ่าน inbox ก่อนนำเข้า](docs/inbox-preview.md)
- [รหัส manuscript และ revision](docs/manuscript-identity.md) · [แนวคิดและขอบเขต](docs/design.md)
- [การติดตั้ง container](docs/container-deployment.md) · [Compose](compose.yaml) · [Dockerfile](Dockerfile) · [ค่าตั้งต้น](.env.example)
- [ต้นทางที่ผู้ใช้เลือกและ SHA-256](third-party/reference-rag/README.md) · [dependencies/ใบอนุญาต](third-party/README.md) · [lockfile](uv.lock)
- [MCP server](src/research_rag_mcp/server.py) · [Qdrant retrieval](src/research_rag_mcp/backend.py) · [JSON journal](src/research_rag_mcp/persistence.py) · [durable jobs](src/research_rag_mcp/jobs.py)
- [เอกสารและ manuscript](src/research_rag_mcp/store.py) · [จัดการ chunks](src/research_rag_mcp/documents.py) · [หน้าตรวจ](src/research_rag_mcp/review.py)
- [สำรอง/ล้างข้อมูล](src/research_rag_mcp/cleanup.py) · [ย้ายและกู้คืนข้อมูล](src/research_rag_mcp/migration.py)
- [ชุดทดสอบ MCP จริง](tests/README.md) · [หลักฐาน PDF จริง](tests/evidence/README.md) · [MCP HTTP smoke](scripts/smoke_http.py)

## ติดตั้งใหม่

ต้องมี Docker Engine/Compose และพื้นที่สำหรับโมเดล/ข้อมูล ค่าเริ่มต้นเปิดเฉพาะ loopback ไม่มี GPU ไม่มี public tunnel และไม่ใช้บัญชี API ที่มีค่าใช้จ่าย

```sh
git clone https://github.com/aekanun2020/2026-Research-RAG.git
cd 2026-Research-RAG
git switch codex/academic-paper-chunking
mkdir -p .chunking-data
cp .env.example .env.chunking
```

หากมี `.env.chunking` อยู่แล้วห้ามคัดลอกทับ บน macOS/Linux ตั้ง `CHUNKING_UID`/`CHUNKING_GID` ตาม `id -u`/`id -g` และกำหนด `CHUNKING_DATA_DIR` เป็นพื้นที่ข้อมูลใหม่ ค่า `RAG_*` เดิมไม่ใช้กับ branch นี้ จากนั้น:

```sh
docker compose --env-file .env.chunking up -d qdrant ollama
docker compose --env-file .env.chunking exec ollama ollama pull nomic-embed-text
docker compose --env-file .env.chunking up -d --build --wait mcp review
```

Model digest ถูก pin ใน Compose หาก tag ใน registry เปลี่ยน ระบบปฏิเสธการใช้โมเดลที่ต่างจากรุ่นที่ตรวจ ไม่เปลี่ยน embedding หรือสร้าง collection ทับอัตโนมัติ

Compose ของ branch นี้ใช้ project `codex-rag-chunking` และ image แอป `codex-research-rag-chunking:0.4.0` เท่านั้น Qdrant/Ollama อยู่ใน network ของชุดนี้ ไม่เปิดพอร์ตฐานข้อมูลสู่ภายนอก MCP เปิด `http://127.0.0.1:8976/mcp` หน้าตรวจที่ `127.0.0.1:8977` ไม่มี container/network/volume หรือข้อมูลร่วมกับรุ่นเดิม

MCP ไม่มี access token และไม่ต้องส่ง Authorization header ตามคำสั่งผู้ใช้วันที่ 21 กันยายน 2026 หน้าตรวจของนักวิจัยแยกจาก MCP และใช้สิทธิ์ตรวจรับเฉพาะหน้า อ่าน URL จาก `docker compose --env-file .env.chunking logs --tail 5 review` นักวิจัยเป็นผู้เปิดและตรวจเอง

## นำเข้าและค้น

1. วางไฟล์ที่มีสิทธิ์ใช้ใน inbox ของการติดตั้งนั้น
2. เรียก `workspace_status` และ `preview_inbox_document` เพื่อตรวจต้นฉบับ/ชื่อเรื่อง
3. เรียก `import_document` พร้อม metadata จริง, revision และ idempotency key จะได้ `job_id` ทันที
4. เรียก `job_status` จนเป็น `completed` จึงถือว่านำเข้าสำเร็จ `failed` เป็นความผิดพลาดจริง; `interrupted` ต้อง `resume_job` ด้วย ID เดิม
5. ค้นด้วย `retrieve_evidence` (`hybrid`, `semantic`, `lexical`) หรือ `search_documentation` (`hybrid`, `semantic`, `bm25`) ค่าเริ่มต้น hybrid ใช้ BM25+semantic+RRF ไม่มี BGE และไม่ลดเหลือหนึ่ง retriever เมื่ออีกตัวล้ม
6. ผลมี document/source/chunk IDs และ source/page/start/end/quote ตรวจต่อด้วย `read_source_page` หรือ `get_chunk_context`

PyThaiNLP ตัดคำไทยด้วย newmm และ normalize ตัวพิมพ์/เลขไทยสำหรับ matching เท่านั้น ข้อความต้นฉบับและตำแหน่งอ้างอิงไม่ถูก normalize การแยกคำช่วย lexical matching; ไม่ได้ทำให้คำค้นไทยเทียบกับข้อความอังกฤษได้เอง คุณภาพข้ามภาษาต้องตรวจ embedding แยก

Chunking ใช้ LlamaIndex SentenceSplitter ขนาดเริ่มต้น 512 tokens รวม special tokens และ overlap ไม่เกิน 64 content tokens; Markdown แบ่งหัวข้อด้วย MarkdownNodeParser ก่อน PDF ใหม่ใช้ PyMuPDF ตามฐานที่เลือก เก็บ spans แบบหน้า/ตัวอักษรและ overlap เพื่อรักษาการอ้างอิง PDF เดิมที่ย้ายมาคงข้อความที่สกัดและ offsets เดิม ไม่มี OCR และยังไม่รับรองลำดับอ่านของทุก two-column PDF

## งานวิจัย 8 ช่วง

| ช่วง | Tool |
|---|---|
| สำรวจหัวข้อ | `explore_topics` |
| วิเคราะห์ช่องว่าง | `map_research_gaps` |
| ตั้งคำถามวิจัย | `formulate_question` |
| ออกแบบการศึกษา | `design_study` |
| ติดตามการดำเนินงาน | `track_execution` |
| วิเคราะห์และอภิปราย | `interpret_results` |
| ร่าง manuscript | `draft_manuscript` |
| เตรียมส่ง | `prepare_submission` |

เริ่มจากหัวข้อ/เป้าหมายที่นักวิจัยระบุด้วย `start_project` stage tools คืนหลักฐานและโครงร่าง client เขียนและบันทึกด้วย `save_artifact` ทุกข้อกล่าวอ้างต้องมีหลักฐานจริง ผลตรวจของนักวิจัยอยู่บนหน้าตรวจแยก เมื่อผ่านเงื่อนไขจึงส่งออกด้วย `export_manuscript` การส่งวารสารเป็นการกระทำของนักวิจัย

## สำรองและย้ายข้อมูล

`backup_workspace` เก็บ JSON journal ต้นฉบับ และเวกเตอร์จริง พร้อม SHA-256 manifest ไม่รวม inbox, exports หรือ token `restore_workspace` กู้คืนเฉพาะ workspace/collection ที่ว่างจาก snapshot ใน backups และคืน job_id ไม่มีการสังเคราะห์ข้อมูลทดแทน

`migrate_legacy_workspace` อ่านเฉพาะ path เดิมที่ operator กำหนดผ่าน read-only mount ใน `RAG_LEGACY_ROOT` เอกสารใหม่และ vectors อยู่ที่ปลายทางใหม่ คงรหัส source/document/chunk/manuscript ประวัติ และ quote offsets เดิม แต่สร้าง embeddings ใหม่ด้วย Ollama การย้ายไม่อ่านหรือคัดลอก inbox

## บันทึก Q&A และผลย้อนหลัง

- [Tools กับ Claim–Evidence–Gap–Research Question — 20 กันยายน 2026](Q&A/2026-09-20-230651-tools-claim-evidence-gap-research-question.md)
- [แยก repository เดิมและที่มาของ snapshot](docs/repository-export.md) · [manifest](docs/repository-export-manifest.json)
- [คุณภาพ semantic ภาษาไทยรุ่น 0.2.4](docs/retrieval-quality-2026-09-20.md) · [คำถามจริง](docs/quality-cases-2026-09-20.json)
- [สถานะก่อนย้ายรุ่น 0.2.4](docs/quality-state-preservation-2026-09-20.json) · [ข้อจำกัดการตรวจเดิม](docs/validation.md)
- [การล้างข้อมูลรุ่นเดิม](docs/workspace-cleanup.md) · [semantic/chunk รุ่นเดิม](docs/semantic-and-chunks.md)
- [จุดพักเดิม](docs/paused-2026-09-20.md)
