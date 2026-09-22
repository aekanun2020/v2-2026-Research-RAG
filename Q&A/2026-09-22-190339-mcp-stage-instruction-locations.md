# Q&A — ตำแหน่งคำแนะนำเฉพาะ stage ใน MCP server

## คำถาม

"Compare populations, methods, findings and limitations, including contradictory evidence. **A missing hit is not proof that a study does not exist.** State coverage limits."

> "Reconcile actual project records with the protocol. Record what actually happened and explicit deviations. **Plans are not completed experiments.**"

ประโยค 2 อันนี้ อยู่ที่ใน mcp server

## คำตอบ

ทั้งสองอยู่ในไฟล์ **`src/research_rag_mcp/models.py`** ภายในตัวแปร **`STAGES`** ครับ

| ประโยค | ตำแหน่งในโค้ด | ใช้กับ tool |
|---|---|---|
| **“A missing hit is not proof that a study does not exist.”** | `STAGES['gaps']['instruction']` — [บรรทัด 45](https://github.com/aekanun2020/v2-2026-Research-RAG/blob/3b321f9b0f19420074a58c2158e835f4eac7c8bd/src/research_rag_mcp/models.py#L45) | `map_research_gaps` |
| **“Plans are not completed experiments.”** | `STAGES['execution']['instruction']` — [บรรทัด 60](https://github.com/aekanun2020/v2-2026-Research-RAG/blob/3b321f9b0f19420074a58c2158e835f4eac7c8bd/src/research_rag_mcp/models.py#L60) | `track_execution` |

**เป็นคำแนะนำเฉพาะ stage ซึ่งส่งกลับมาในผลของ tool** ผ่านฟังก์ชัน [`stage_context`](https://github.com/aekanun2020/v2-2026-Research-RAG/blob/3b321f9b0f19420074a58c2158e835f4eac7c8bd/src/research_rag_mcp/workflow.py#L45-L51) ในฟิลด์ `instruction` และยังดูได้จาก `workspace_status.stages`

ข้อความสองชุดนี้ **ไม่ได้อยู่ใน MCP Prompt ชื่อ `research_workflow` โดยตรง** ครับ
