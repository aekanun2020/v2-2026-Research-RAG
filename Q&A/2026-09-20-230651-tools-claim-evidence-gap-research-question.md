# Q&A: Tools ที่สอดคล้องกับ Claim–Evidence–Gap–Research Question

## คำถาม

[https://chatgpt.com/share/6ab003ec-1a40-83ec-ba61-c5cbf3f5e2e7](https://chatgpt.com/share/6ab003ec-1a40-83ec-ba61-c5cbf3f5e2e7)

มี tool อะไรที่สอดคล้องกับสาระสำคัญจาก link นี้

## คำตอบ

มีครับ **`map_research_gaps` และ `formulate_question` ตรงกับสาระสำคัญมากที่สุด** โดยมี tools ค้นหลักฐานและบันทึกที่มาช่วยประกอบ

จาก[บทสนทนาที่แชร์](https://chatgpt.com/share/6ab003ec-1a40-83ec-ba61-c5cbf3f5e2e7) ประเด็นหลักคือ **คำถามวิจัยต้องอธิบายที่มาจาก Claim–Evidence–Gap และแสดงว่าจะรู้อะไรเพิ่มจากงานที่ใกล้ที่สุด** ผมเทียบกับ implementation รุ่น 0.2.4 แล้วได้ดังนี้:

| สาระจากลิงก์ | Tools ที่สอดคล้อง | รองรับจริงแค่ไหน |
|---|---|---|
| ตรวจว่า Claim มี Evidence รองรับอย่างไร | `retrieve_evidence`, `read_source_page`, `get_chunk_context` | ค้นข้อความและอ่านบริบทต้นฉบับได้ ผู้วิเคราะห์ยังต้องตัดสินว่าหลักฐานสนับสนุนข้อกล่าวอ้างจริงหรือไม่ |
| เปรียบเทียบว่างานเดิมศึกษาและพบอะไร | `save_artifact(stage="literature_note")` | บันทึกคำถาม ประชากร วิธีวิจัย ผล และข้อจำกัด แยกตาม paper พร้อม citation |
| **การกล่าวว่ามี Gap ต้องมีหลักฐาน** | **`map_research_gaps`** | จัดตารางจาก literature notes พร้อมหลักฐานและประวัติการค้น เพื่อเสนอช่องว่างและระบุขอบเขตการค้น |
| **สร้าง Research Question จากสิ่งที่ยังไม่รู้** | **`formulate_question`** | เตรียมหลักฐานและบันทึกหัวข้อ/gap เดิม ให้พัฒนาคำถาม วัตถุประสงค์ contribution และ feasibility |
| ตอบ “So what?”—คำถามนี้สำคัญอย่างไร | `formulate_question`, `design_study` | มีส่วน contribution และ feasibility ให้เขียนเหตุผลและตรวจความเป็นไปได้ ยังไม่ประเมินความสำคัญอัตโนมัติ |
| เปรียบเทียบ “งานที่ใกล้ที่สุดตอบแล้วอะไร—เราจะตอบเพิ่มอะไร” | `search_literature`, `retrieve_evidence`, `map_research_gaps` | ช่วยค้นและเตรียมข้อมูลเปรียบเทียบ แต่ยังไม่มี tool ประเมิน novelty โดยเฉพาะ; Crossref ค้นเพียง metadata |
| เก็บ Reason, Warrant และข้อทักท้วง/คำตอบ | `save_artifact`, `read_artifact` | เพิ่มเป็น section ในบันทึกได้ แต่ยังไม่มีโครงสร้างเฉพาะที่แยกองค์ประกอบเหล่านี้และตรวจความสัมพันธ์ |
| ย้อนกลับว่าคำถามหรือข้อสรุปใช้หลักฐานใด | `save_artifact` พร้อม `dependency_ids`, `read_artifact`, `find_evidence_usage` | ผูกบันทึกกับรุ่นของบันทึกก่อนหน้าและ citation ได้ รวมถึงหาว่า chunk ถูกอ้างที่ไหน |

รายละเอียดนี้ตรวจจาก [สัญญา tools](https://github.com/aekanun2020/2026-Research-RAG/blob/main/docs/tools.md) และ [โค้ดจัดเตรียมบริบทแต่ละขั้น](https://github.com/aekanun2020/2026-Research-RAG/blob/main/src/research_rag_mcp/workflow.py)

**ข้อจำกัดสำคัญ:** stage tools จัดเตรียมบริบทให้ MCP client วิเคราะห์ ผู้วิเคราะห์ต้องเขียนผลแล้วบันทึกผ่าน `save_artifact` ส่วน server ตรวจข้อความอ้างอิงและความสัมพันธ์ของรุ่นเอกสาร ไม่ได้รับรองเหตุผลหรือความใหม่ของงาน

ส่วนที่ยังขาดเพื่อรองรับแนวคิดในลิงก์ให้ครบ ได้แก่:

- **โครงสร้าง Claim–Reason–Evidence–Warrant–Gap–Question** ที่มีรหัสและความสัมพันธ์ชัดเจน ปัจจุบันเชื่อมระดับ artifact และ citation ยังไม่เป็น KG ตามกรอบนี้
- **ตารางเปรียบเทียบกับงานที่ใกล้ที่สุดโดยเฉพาะ** พร้อมสถานะว่าแต่ละคำถามถูกตอบแล้ว บางส่วน หรือยังไม่ชัด
- **บันทึกการประเมิน novelty อย่างมีหลักฐาน** ระบุเหตุผล ขอบเขตการค้น และผู้ประเมิน โดยไม่ถือว่า “ค้นไม่พบ” เท่ากับ “ใหม่”
