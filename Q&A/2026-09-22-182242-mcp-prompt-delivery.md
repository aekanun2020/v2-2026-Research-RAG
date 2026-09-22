# Q&A — MCP ส่ง prompt และคำแนะนำให้ client เมื่อใด

## คำถาม

[https://github.com/aekanun2020/v2-2026-Research-RAG/blob/04f698182603938760fd507141da67cd6b0ceca1/src/research\_rag\_mcp/server.py#L377-L379](https://github.com/aekanun2020/v2-2026-Research-RAG/blob/04f698182603938760fd507141da67cd6b0ceca1/src/research_rag_mcp/server.py#L377-L379)

มันถูกส่งเป็น prompt ทุกครั้งที่ ...

## คำตอบ

**โค้ดที่คุณชี้จะส่ง prompt เมื่อ client เรียก `prompts/get` โดยระบุชื่อ `research_workflow` ครับ ไม่ได้ส่งซ้ำอัตโนมัติทุกครั้งที่เรียก tool** ตาม [กลไกของ MCP Prompts](https://py.sdk.modelcontextprotocol.io/servers/prompts/)

ระบบเราส่งคำแนะนำได้หลายจังหวะ:

| จังหวะ | สิ่งที่ส่ง |
|---|---|
| **เริ่มเชื่อมต่อผ่าน `initialize`** ตามเส้นทางที่เราทดสอบ | `INSTRUCTIONS` ทั้งชุดในช่อง server instructions |
| **ขอ `research_workflow` ผ่าน `prompts/get`** | `INSTRUCTIONS` ทั้งชุดในรูปข้อความ prompt |
| **เรียก stage tool เช่น `design_study`** | คำแนะนำเฉพาะขั้น หลักฐาน และ `required_output` ว่าต้องบันทึกอะไร |
| **เรียก tool อื่นทั่วไป** | ผลของ tool นั้น ไม่ได้แนบ workflow prompt ทั้งชุดเสมอ |

อีกจุดสำคัญคือ **server ส่งคำแนะนำให้ client แล้ว ไม่ได้ยืนยันว่า Claude นำข้อความนั้นเข้า context ทุกครั้งที่โมเดลคิดหรือตอบ** วิธีเก็บและส่งต่อคำแนะนำขึ้นกับ client ซึ่งเอกสาร MCP ระบุข้อจำกัดนี้ไว้ด้วยครับ [Server instructions](https://blog.modelcontextprotocol.io/posts/2025-11-03-using-server-instructions/)
