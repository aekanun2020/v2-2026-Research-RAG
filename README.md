# 2026-Research-RAG — งานวิจัย 8 ช่วงผ่าน MCP

## ใบอนุญาตและข้อจำกัดการใช้งาน

โค้ดและเอกสารต้นฉบับของโปรเจกต์นี้เผยแพร่ภายใต้ **GNU AGPL version 3 only (`AGPL-3.0-only`)** ดู [LICENSE ฉบับเต็ม](LICENSE) และ [ขอบเขตใบอนุญาต/ประกาศของส่วนประกอบภายนอก](third-party/README.md#application-license) โค้ดที่นำเข้า dependencies โมเดล และเนื้อหาของบุคคลที่สามยังคงอยู่ภายใต้สิทธิ์และเงื่อนไขของต้นทาง ไม่ได้ถูกเปลี่ยนใบอนุญาตด้วยประกาศนี้

ระบบเป็นเครื่องมือช่วยวิจัย ไม่รับรองความถูกต้องของผลค้นคืนหรือข้อความที่ AI สังเคราะห์ นักวิจัยต้องตรวจต้นฉบับก่อนใช้หรือเผยแพร่ อ่าน [ข้อจำกัดและความรับผิดชอบในการใช้งาน](DISCLAIMER.md) ใบอนุญาตซอฟต์แวร์ไม่ให้สิทธิ์เพิ่มเติมในบทความ PDF หรือข้อมูลวิจัยที่นำเข้า

รุ่น **0.5.0 บน branch `codex/claude-workspace-ingestion`** เพิ่ม workspace แยกตามรหัสและดาวน์โหลด PDF ฝั่ง server ตามฐาน [fixed-2026-rag-mcp-server-streamablehttp](https://github.com/aekanun2020/fixed-2026-rag-mcp-server-streamablehttp/tree/5e5373a7a0919201b44f5aa78edad069a09974db) ที่ผู้ใช้เลือก: **Qdrant + Ollama + PyThaiNLP/BM25 + RRF** รันบน CPU ใน Docker และเชื่อมผ่าน Streamable HTTP

**ชุดใหม่ 0.5.0:** `codex-rag-agents` เปิด MCP ที่ `http://127.0.0.1:9076/mcp` ไม่มี access token และหน้าตรวจที่ port 9077 ใช้ container, network, volumes และ `.agent-data` ของตัวเองทั้งหมด ไม่เปลี่ยนบริการ 8976 หรือข้อมูลเดิม ต้องชี้ client มาที่ endpoint รุ่นใหม่จึงจะเห็น tools ใหม่ ดู [ขั้นตอนใช้กับ Claude, ตำแหน่ง inbox และหลักฐานทดสอบ](docs/agent-ingestion/README.md) การทดสอบ MCP ไม่ใช่การยืนยันว่าได้ทดสอบผ่านแอป Claude จริงทั้ง Windows/macOS แล้ว

**Public MCP ที่ผู้ใช้อนุมัติ:** [research-rag ผ่าน ngrok](https://michiko-psychodiagnostic-melvina.ngrok-free.dev/mcp) → พอร์ต 9076 บน MacBook โดยไม่มี token ตรวจ initialize/tools/list/workspace_status แล้วครบ 45 tools ดู [ค่าตั้งค่า ผลทดสอบ และข้อกำหนดการรัน](docs/agent-ingestion/ngrok.md)

รุ่นใหม่ **ไม่ใช้ SQLite เก็บข้อมูลหรือค้นหา** เวกเตอร์อยู่ใน Qdrant ส่วนเอกสาร รหัส chunks ประวัติ manuscript และผลตรวจอยู่ใน JSON journal ที่ล็อกข้าม process และบันทึกแต่ละ revision แบบ atomic ขั้นย้ายครั้งเดียวอ่าน SQLite เดิมแบบ read-only ผ่าน MCP เพื่อรักษารหัสและหลักฐาน ไม่มี SQLite เป็น backend สำรอง

**ผลทดสอบ 0.4.0:** chunking ผ่านกรณีเดิมและกรณีข้างเคียง โดย workflow ผ่าน 61 checks ผ่าน MCP จริง ชุดใหม่ว่าง ณ จบการล้างข้อมูลทดสอบ (เป็นสถานะย้อนหลัง) ต่อมาที่ revision 51 มี 12 papers / 907 chunks; [Codex สุ่มอ่าน 10 chunks](docs/chunk-readability-codex-2026-09-21.md) พบข้อจำกัดเรื่องบริบทข้ามหน้า ตาราง และบรรณานุกรม จึงไม่ถือว่า workflow checks รับรองความได้ใจความของทุก chunk ส่วนผล hybrid พร้อมกัน 12 คำขอและ semantic ไทย→อังกฤษเป็นผลย้อนหลังของ 0.3.0: คำขอสำเร็จครบ แต่คุณภาพ semantic ของโมเดล nomic-embed-text เดิม **ไม่ผ่าน** งาน chunking นี้ยังไม่ได้เปลี่ยนโมเดล

ระบบค้นนี้ไม่มี BGE reranker ตามฐานที่เลือก ผลคุณภาพรุ่น 0.2.4 จึงเป็นหลักฐานย้อนหลัง ไม่ใช่คะแนนของรุ่นใหม่ ดู [สถานะการย้าย ผลก่อนแก้ และการตรวจรับ](docs/qdrant-migration.md) ขณะเอกสารนี้ระบุว่า “กำลังพัฒนา” ยังไม่ถือว่าผ่านการตรวจคุณภาพ semantic ภาษาไทย

**บริการรุ่นเดิม 0.3.0:** ผู้ใช้สั่งลบ container รุ่นเดิมทั้งสองตัวเมื่อ 21 กันยายน 2026 แล้ว ชุดใหม่ `codex-research-rag-next` ยังทำงานที่ `http://127.0.0.1:8876/mcp` โดยไม่มี token ดู [บันทึกการนำบริการเดิมออก](docs/qdrant-migration.md#old-container-removal-2026-09-21)

**ประวัติการล้างรุ่นเดิม 0.3.0:** การล้างเมื่อ 21 กันยายน 2026 ทำให้ revision 38 ว่าง โดยเก็บ PDF ต้นฉบับ 22 ไฟล์และ backup ไว้ ต่อมาในการตรวจแบบอ่านอย่างเดียวระหว่างงาน chunking พบ revision 50 มี 12 เอกสาร/1,490 chunks แล้ว งาน branch นี้ไม่ได้เป็นผู้นำเข้าเหล่านั้น ดู [ผลการล้างและการตรวจผ่าน MCP](docs/qdrant-cleared-2026-09-21.json)

**ชุด chunking แยก:** `codex-rag-chunking` เปิด MCP ที่ `http://127.0.0.1:8976/mcp` และหน้าตรวจที่ port 8977 มี MCP, review, Qdrant และ Ollama ของตัวเอง พร้อม network/volumes และ `.chunking-data` แยกจากรุ่นเดิมทั้งหมด [รายละเอียด chunking และผลตรวจ](docs/academic-chunking.md) · [หลักฐานการแยก containers](docs/chunking-container-isolation-2026-09-21.json)

MCP server จัดเตรียมหลักฐาน โมเดลใน client เป็นผู้สังเคราะห์ ไม่มีการเรียก OpenRouter หรือโมเดลภายนอกเพื่อเขียน/ตัดสินคำตอบ นักวิจัยตรวจต้นฉบับและตัดสินใจผ่านหน้าตรวจแยก การแก้ manuscript สร้าง revision ใหม่และต้องตรวจรับใหม่

ล่าสุดนำเข้า cited ครบ **221/221 PDF** ผ่าน MCP ณ revision 282: รวม **233 เอกสาร / 16,809 chunks** และดัชนีครบทุก chunk ดู [บัญชีไฟล์ ผลตรวจ และข้อผิดพลาดที่พบระหว่างนำเข้า](docs/cited-import-2026-09-21.md) การทดสอบค้นคืนท้ายงานตรวจตำแหน่งข้อความ ไม่ได้ประเมินคุณภาพ semantic ใหม่

## เอกสารและซอร์ส

- [การแก้ Claude agent: ดาวน์โหลด PDF และแยก workspace](docs/agent-ingestion/README.md) · [Compose 0.5.0](compose.agents.yaml) · [ค่าเริ่มต้นชุดใหม่](agents.env.example)
- [Public ngrok endpoint ชื่อ research-rag](docs/agent-ingestion/ngrok.md) · [ทดสอบ public MCP](scripts/verify_public_mcp.py)
- [การเลือก workspace](src/research_rag_mcp/workspaces.py) · [ดาวน์โหลด PDF](src/research_rag_mcp/downloads.py) · [MCP prompt](src/research_rag_mcp/models.py) · [ทดสอบ ingestion จริง](scripts/verify_agent_ingestion_mcp.py) · [ทดสอบ manuscript และกู้คืน workspace](scripts/verify_agent_workspace_followup_mcp.py)
- [ชุดอ่าน AI กับการทำงาน: 23 งาน / 25 PDF เก็บแยก ยังไม่นำเข้า RAG](papers/ai-work-common-2026-09-22/README.md) · [บัญชีแหล่งที่มาและ reference links](papers/ai-work-common-2026-09-22/catalog.json)
- [ผลนำเข้า cited 221 PDF ผ่าน MCP และบัญชีเอกสาร](docs/cited-import-2026-09-21.md) · [หลักฐานตรวจจำนวนและดัชนี](docs/cited-import-2026-09-21.json)
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
git switch codex/claude-workspace-ingestion
mkdir -p .agent-data
cp agents.env.example .env.agents
```

หากมี `.env.agents` อยู่แล้วห้ามคัดลอกทับ บน macOS/Linux ตั้ง `AGENTS_UID`/`AGENTS_GID` ตาม `id -u`/`id -g` และกำหนด `AGENTS_DATA_DIR` เป็นพื้นที่ข้อมูลใหม่ ห้ามชี้ไปที่ข้อมูลของบริการเดิม จากนั้นใช้ `-f compose.agents.yaml` ทุกครั้ง:

```sh
docker compose -f compose.agents.yaml --env-file .env.agents up -d qdrant ollama
docker compose -f compose.agents.yaml --env-file .env.agents exec ollama ollama pull nomic-embed-text
docker compose -f compose.agents.yaml --env-file .env.agents up -d --build --wait mcp review
```

Model digest ถูก pin ใน Compose หาก tag ใน registry เปลี่ยน ระบบปฏิเสธการใช้โมเดลที่ต่างจากรุ่นที่ตรวจ ไม่เปลี่ยน embedding หรือสร้าง collection ทับอัตโนมัติ

Compose 0.5.0 ใช้ project `codex-rag-agents` และ image `codex-research-rag-agents:0.5.0` Qdrant/Ollama อยู่ใน network ของชุดนี้ ไม่เปิดพอร์ตฐานข้อมูลสู่ภายนอก MCP เปิด `http://127.0.0.1:9076/mcp` หน้าตรวจที่ `127.0.0.1:9077` ไม่มี container/network/volume หรือข้อมูลร่วมกับรุ่นเดิม ไฟล์ Compose รุ่นก่อนคงไว้เป็น deployment เดิม อย่าสั่งโดยละ `-f`

MCP ไม่มี access token และไม่ต้องส่ง Authorization header ตามคำสั่งผู้ใช้วันที่ 21 กันยายน 2026 หน้าตรวจของนักวิจัยแยกจาก MCP และใช้สิทธิ์ตรวจรับเฉพาะหน้า อ่าน URL จาก `docker compose -f compose.agents.yaml --env-file .env.agents logs --tail 5 review` นักวิจัยเป็นผู้เปิดและตรวจเอง Workspace ID เป็นการจัดพื้นที่ข้อมูล ไม่ใช่สิทธิ์แยกผู้ใช้

## นำเข้าและค้น

1. เรียก `list_workspaces` เลือกพื้นที่ที่ผู้ใช้ระบุ หรือ `create_workspace` สำหรับโครงการใหม่ ส่ง `workspace_id` ทุกคำขอ; ไม่มีการสลับพื้นที่กลางร่วมกัน
2. เรียก `workspace_status` แล้ว `download_document` ด้วย public HTTPS URL หรือ arXiv ID; poll `job_status` จนเสร็จ หรือวางไฟล์จริงใน inbox ของ workspace นั้น จากนั้น `preview_inbox_document` เพื่อตรวจต้นฉบับ/ชื่อเรื่อง หากสั่งดาวน์โหลดอย่างเดียวให้หยุดก่อนนำเข้า
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

- [Q&A: ตำแหน่งคำแนะนำเฉพาะ stage ใน MCP server — 22 กันยายน 2026](Q&A/2026-09-22-190339-mcp-stage-instruction-locations.md)
- [Q&A: MCP ส่ง prompt และคำแนะนำให้ client เมื่อใด — 22 กันยายน 2026](Q&A/2026-09-22-182242-mcp-prompt-delivery.md)
- [Q&A: ความได้ใจความของ 10 chunks ที่สุ่มจริง — 21 กันยายน 2026](Q&A/2026-09-21-123834-random-ten-chunks-readability.md)
- [Tools กับ Claim–Evidence–Gap–Research Question — 20 กันยายน 2026](Q&A/2026-09-20-230651-tools-claim-evidence-gap-research-question.md)
- [แยก repository เดิมและที่มาของ snapshot](docs/repository-export.md) · [manifest](docs/repository-export-manifest.json)
- [คุณภาพ semantic ภาษาไทยรุ่น 0.2.4](docs/retrieval-quality-2026-09-20.md) · [คำถามจริง](docs/quality-cases-2026-09-20.json)
- [สถานะก่อนย้ายรุ่น 0.2.4](docs/quality-state-preservation-2026-09-20.json) · [ข้อจำกัดการตรวจเดิม](docs/validation.md)
- [การล้างข้อมูลรุ่นเดิม](docs/workspace-cleanup.md) · [semantic/chunk รุ่นเดิม](docs/semantic-and-chunks.md)
- [จุดพักเดิม](docs/paused-2026-09-20.md)
