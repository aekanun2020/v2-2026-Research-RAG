# นำเข้าเอกสารจนถึงใช้เขียน manuscript

| ขั้นตอน | ใครทำ / ผ่านอะไร | ปลายทาง |
|---|---|---|
| จัดหาเอกสาร | นักวิจัยเลือกไฟล์ที่มีสิทธิ์ใช้; `search_literature` ค้น metadata ผ่าน Crossref ได้ แต่ไม่ดาวน์โหลด full paper | ไฟล์ PDF หรือ UTF-8 TXT/MD/CSV/JSON ของนักวิจัย |
| วางไฟล์ | นักวิจัยหรือเครื่องมือจัดไฟล์ที่ได้รับอนุญาต วางใน `.data/inbox/` บนเครื่อง | Docker เห็นไฟล์เดียวกันที่ `/data/inbox/` |
| อ่านก่อนนำเข้า | MCP client เรียก `preview_inbox_document(filename, page_index=0)` อ่านชื่อเรื่องและข้อมูลจากหน้าแรก; ใช้ `next_start` อ่านข้อความส่วนถัดไป | คืนข้อความต้นฉบับและ metadata พร้อม SHA-256 โดยยังไม่บันทึกเอกสารหรือสร้าง embeddings; metadata อาจไม่มีหรือผิด ต้องเทียบกับข้อความจริง |
| สั่งนำเข้า | MCP client เรียก `import_document` พร้อม filename, origin, role, bibliography, expected_revision และ idempotency_key | MCP server ตรวจชนิด/ขนาด/ขอบเขต path และคำนวณ SHA-256 |
| เก็บต้นฉบับ | MCP server คัดลอก bytes เดิม | `.data/sources/<source_id>/original.<ext>`; ไม่แก้ต้นฉบับ |
| ดึงข้อความ | MCP server ใช้ pypdf หรืออ่าน UTF-8 | ข้อความรายหน้าใน SQLite พร้อม text hash; หน้า PDF ว่างถูกแจ้ง `needs_text_review`; ยังไม่มี OCR |
| ให้รหัส | MCP server | `document_id` ของงาน, `source_id` ของไฟล์รุ่นนั้น, `source_version`, `text_revision_id`, `chunk_set_id`, `chunk_id` |
| แบ่งและทำดัชนี | MCP server แบ่งรายหน้าและช่วงอักขระ สร้าง embedding ด้วยโมเดลที่ pin รุ่นไว้บน CPU | chunks และเวกเตอร์อยู่ใน workspace; สำเร็จแล้วจึงคืนผลนำเข้า |
| ตรวจและจัดการ | นักวิจัยใช้ผลจาก `inspect_document_chunks`, `list_chunks`, `read_chunk`, `get_chunk_context`; client ช่วยเรียกเครื่องมือ | รักษา citation ถึงหน้า/ข้อความเดิม; พัก chunk ด้วย `set_chunk_status` พร้อมเหตุผลได้ |
| ค้น | MCP client เรียก `retrieve_evidence(mode="hybrid")` หรือ `semantic` / `lexical` | E5/hybrid candidates → BGE reranking บน CPU → คะแนนความเกี่ยวข้องระดับเอกสารเพื่อช่วยตรวจ (ไม่ตัดผลอัตโนมัติ) → chunks พร้อมคะแนนแยกแต่ละขั้นและ citation; นักวิจัย/client ต้องอ่านบริบทและตรวจว่ารองรับคำกล่าวจริง |
| เขียนและตรวจ | client สังเคราะห์แล้ว `save_artifact`; นักวิจัยตรวจในหน้าตรวจแยก | manuscript ID ถาวรและ version; การตรวจรับไม่ทำอัตโนมัติ |
| ส่งออก | client เรียก `export_manuscript` เมื่อเข้าเงื่อนไข | `.data/exports/` มี Markdown, evidence JSON, bibliography และ hash manifest; นักวิจัยเป็นผู้ส่งเข้าวารสาร |

การนำเข้าเป็นงาน synchronous การสร้าง embedding บน CPU อาจใช้เวลามากกว่าการแยกข้อความ โดยเฉพาะครั้งแรก ให้ client ใช้เวลารอที่เหมาะกับงานนำเข้า สำหรับ Python HTTP client ใช้ `httpx2.Timeout(30, read=300)` ซึ่งตรงค่าที่ official MCP SDK ใช้กับ Streamable HTTP; request timeout ของ MCP client ต้องไม่สั้นกว่างานที่กำลังทำ หากการเชื่อมต่อขาด ให้ตรวจ `workspace_status` และ retry ด้วย key/arguments เดิม ไม่สร้าง key ใหม่โดยยังไม่ตรวจผลเดิม

การใส่ `document_id` เดิมใน `import_document` หมายถึงผู้เรียกยืนยันว่าไฟล์ใหม่เป็นอีก source version ของงานเดียวกัน ระบบไม่เดาจากชื่อหรือ DOI ค้นค่าเริ่มต้นใช้รุ่นล่าสุด; `source_ids` เลือกรุ่นเก่าได้ ต้นฉบับและ citation ของรุ่นเก่ายังอ่านได้

`rechunk_document` สร้าง candidate set พร้อมดัชนี ให้ตรวจด้วย `list_chunks(chunk_set_id=...)` แล้วเลือกด้วย `activate_chunk_set` ชุดเก่ายังคงอยู่ การเปลี่ยนชุดไม่ได้แก้ extracted text หรือหมายความว่านักวิจัยรับรองความถูกต้องของเนื้อหา

ไม่มีช่องอัปโหลดเว็บ, inbox watcher, URL/PDF downloader หรือ OCR ในรุ่นนี้ การมีไฟล์ใน inbox อย่างเดียวยังไม่ทำให้ค้นเจอ ต้องเรียก import ให้สำเร็จก่อน ดู [สัญญาเครื่องมือ](tools.md) และ [semantic/chunk implementation](semantic-and-chunks.md)

การปรับค้นรุ่น 0.2.4 ไม่ต้องนำเข้าเอกสารหรือสร้าง embedding ใหม่: [reranking และผลตรวจ](retrieval-quality-2026-09-20.md) ทำตอนค้น โดยใช้โมเดลและข้อมูลในเครื่องทั้งหมด `lexical` ยังค้นคำตามเดิม
