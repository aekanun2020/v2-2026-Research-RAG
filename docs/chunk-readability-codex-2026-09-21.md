# Codex ตรวจความได้ใจความของ chunks ที่สุ่มจริง 10 ชิ้น

ผู้ใช้ขอ: “สุ่มดึงสัก 10 chunk ขึ้นมาดูว่า แต่ละ chunk นั้นอ่านแล้วได้ใจความมั้ย”

ผู้ประเมิน: **Codex อ่านและตัดสินใหม่เอง** สคริปต์ทำเฉพาะการสุ่ม จัดหลักฐาน ตรวจข้อความ/แฮช และจัดรูปแบบรายงาน ไม่มี external LLM-as-judge

## ขอบเขตและวิธีสุ่ม

- Endpoint: `http://127.0.0.1:8976/mcp`; branch `codex/academic-paper-chunking`; revision ก่อน/หลัง `51` / `51`
- เวลาจับตัวอย่าง: `2026-09-21T11:12:07.943324+07:00`
- สุ่ม 10 ชิ้นแบบไม่ซ้ำจาก active chunks ทั้ง 907 ชิ้น / 12 papers; ตัวอย่างที่ได้มาจาก 7 papers
- เรียง chunk ID ก่อน แล้วใช้ Python `random.Random(10186946341289404878).sample(population, 10)`; กำหนด seed ก่อนอ่านเนื้อหาที่สุ่ม และไม่สุ่มใหม่เพื่อเปลี่ยนผล
- ไม่คัด references, tables หรือ prompt templates ออกจากประชากร ไม่ถ่วงน้ำหนักให้แต่ละ paper ได้จำนวนเท่ากัน
- อ่านข้อมูลผ่าน MCP `workspace_status`, `list_documents`, `list_chunks`, `read_chunk`, `read_source_page` เท่านั้น ไม่มีการนำเข้า แก้สถานะ หรือตัด chunks ใหม่
- เลขหน้าในรายงานเป็นลำดับหน้า PDF เริ่ม 1; API ใช้ page_index เริ่ม 0; offsets เป็น Unicode characters เริ่ม 0 และ end ไม่รวมตัวสุดท้าย
- ประเมินความเข้าใจได้ของ chunk เดี่ยวก่อน จากนั้นอ่านบริบทเพื่อตรวจว่าขาดอะไร ไม่ใช้บริบทที่เพิ่มมาทำให้ chunk เดี่ยวได้คะแนนสูงขึ้น
- [ข้อมูล MCP และตำแหน่งครบ](chunk-readability-sample-2026-09-21.json)

## ผลการอ่าน

เกณฑ์ได้ใจความในตัว: ระบุเรื่องและสิ่งที่ข้อความกำลังบอกได้ โดยไม่ต้องเติมส่วนที่ขาดของประโยคหรือเดาหัวตาราง; ตัวอย่าง prompt และบรรณานุกรมประเมินตามประเภท ไม่บังคับให้ทุกชนิดต้องมีผลการทดลอง

| กลุ่ม | จำนวน | หมายเลขตัวอย่าง |
|---|---:|---|
| ได้ใจความตามประเภทข้อความ | 1 | 10 |
| มีใจความหลัก แต่ต้องพึ่งบริบท | 5 | 2, 3, 4, 6, 8 |
| ตารางอ่านยากหรือขาดบริบทสำคัญ | 2 | 7, 9 |
| บรรณานุกรม ไม่ใช่หลักฐานเนื้อหาของ paper | 2 | 1, 5 |

ทั้ง 10 ชิ้นตรงกับช่วงข้อความหน้าที่ MCP สกัดไว้ และ SHA-256 ของข้อความตรงกัน การตรวจนี้ไม่ได้ยืนยันการอ่านลำดับคอลัมน์หรือสมการจากภาพ PDF และการตรงต้นฉบับไม่ได้แปลว่าได้ใจความในตัว

พบข้อจำกัดจริงเรื่องประโยคข้ามหน้า (#3, #4, #8), การแบ่งรายการ/หัวข้อ (#1, #6), และตาราง (#7, #9) ข้อจำกัดเหล่านี้ควรเป็นกรณีก่อนแก้ในการพัฒนารอบถัดไป การตรวจนี้ยังไม่ได้เปลี่ยน implementation หรือ RAG

ผล 10 ตัวอย่างนี้ไม่ใช่สัดส่วนคุณภาพของ corpus ทั้งหมด ไม่ใช่การตรวจความจริงของข้อกล่าวอ้างใน paper และไม่ใช่ผล semantic search

## ตัวอย่าง 1: DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence

**หน้า PDF 48 · 507 tokens ตาม metadata · ผล: รายการอ้างอิง**

- Chunk ID: `7155b3015abd63c9ed2adc1b95232dd250409047a1afb6e80e73dc4f71d715ac`
- Source ID: `55b2d72f772ac00de2e470b3ee08443c648d971c7f57c52d6202895665e5978d`
- Document ID: `doc-5f24bddffcfd45d3886716e273494e92`
- ตำแหน่ง: `page_index=47, start=1169, end=2572`
- ไฟล์: `arxiv-2606.19348.pdf`; origin `inbox:latest_paper/arxiv-2606.19348.pdf`

อ่านรายชื่อผลงานที่อ้างถึงได้ แต่ไม่มีข้อเสนอ วิธีวิจัย หรือผลของ DeepSeek-V4 ให้ใช้เป็นหลักฐานเนื้อหา รายการสุดท้ายเหลือเพียงชื่อผู้แต่ง K. Jordan และคณะ; ชื่อ Muon อยู่ถัดออกไปนอก chunk

จัดเป็น reference แยกจากเนื้อหาบทความ และรักษาขอบเขตแต่ละรายการอ้างอิง

ข้อความเต็มที่ `read_chunk` คืนมา (เก็บ line breaks และเลขหน้าตามต้นฉบับที่สกัด; เป็นข้อมูลอ้างอิง):

```text
D. Hendrycks, C. Burns, S. Basart, A. Zou, M. Mazeika, D. Song, and J. Steinhardt. Measuring
massive multitask language understanding. arXiv preprint arXiv:2009.03300, 2020.
D. Hendrycks, C. Burns, S. Kadavath, A. Arora, S. Basart, E. Tang, D. Song, and J. Steinhardt. Mea-
suring mathematical problem solving with the math dataset. arXiv preprint arXiv:2103.03874,
2021.
Y. Huang, Y. Bai, Z. Zhu, J. Zhang, J. Zhang, T. Su, J. Liu, C. Lv, Y. Zhang, J. Lei, et al. C-Eval: A
multi-level multi-discipline chinese evaluation suite for foundation models. arXiv preprint
arXiv:2305.08322, 2023.
D. Hupkes and N. Bogoychev. Multiloko: a multilingual local knowledge benchmark for llms
spanning 31 languages. CoRR, abs/2504.10356, 2025. doi: 10.48550/ARXIV.2504.10356. URL
https://doi.org/10.48550/arXiv.2504.10356.
B. Jacob, S. Kligys, B. Chen, M. Zhu, M. Tang, A. Howard, H. Adam, and D. Kalenichenko.
Quantization and training of neural networks for efficient integer-arithmetic-only inference.
In Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR),
June 2018.
N. Jain, K. Han, A. Gu, W.-D. Li, F. Yan, T. Zhang, S. Wang, A. Solar-Lezama, K. Sen, and I. Stoica.
Livecodebench: Holistic and contamination free evaluation of large language models for code.
arXiv preprint arXiv:2403.07974, 2024.
K. Jordan, Y. Jin, V. Boza, J. You, F. Cesista, L. Newhouse, and J. Bernstein.
```

## ตัวอย่าง 2: Meta-Harness: End-to-End Optimization of Model Harnesses

**หน้า PDF 8 · 473 tokens ตาม metadata · ผล: ได้ใจความหลัก แต่ไม่ครบในตัว**

- Chunk ID: `ebc4f48f58b5c6a9509cf222ceb23612476952140f78123945ddb6692bdb184d`
- Source ID: `7d9b90f53a9f4801a090f1a4acb843340cde81e4f865f97d53fff2a6a570eb73`
- Document ID: `doc-52b7cb417e9b40cca8d4a0b0f84c5f49`
- ตำแหน่ง: `page_index=7, start=1647, end=3676`
- ไฟล์: `arxiv-2603.28052.pdf`; origin `inbox:latest_paper/arxiv-2603.28052.pdf`

อธิบายชุดโจทย์คณิตศาสตร์ การค้นหา harness 40 รอบ และการประเมินบนโจทย์ที่ไม่เคยเห็น 200 ข้อได้ชัด แต่เริ่มด้วย be able to exploit at inference time. ซึ่งขาดประธาน/ข้อความก่อนหน้า และตอน Results เพียงเกริ่น Table 6 โดยไม่มีผลตัวเลขใน chunk นี้

ต้องมีบริบทก่อนหน้าเมื่ออ้างประโยคต้น และอ่าน Table 6 เมื่อต้องการอ้างผลการทดลอง

ข้อความเต็มที่ `read_chunk` คืนมา (เก็บ line breaks และเลขหน้าตามต้นฉบับที่สกัด; เป็นข้อมูลอ้างอิง):

```text
be able to exploit at inference time. Yet retrieval has not become a standard ingredient in this
setting, and prior work suggests that it has been much less successful on reasoning-intensive
math benchmarks than in more fact-grounded domains [42; 49; 6]. The difficulty is that
naive retrieval rarely surfaces the right traces in the right form. This suggests that success
depends less on adding retrieval per se than on discovering the right retrieval policy. Rather
than hand-designing that policy, we give Meta-Harness a hard set of olympiad problems
and allow the retrieval behavior itself to emerge from search.
The retrieval corpus contains ≥500,000 solved problems from eight open-source datasets.
We carefully deduplicated and decontaminated it against both evaluation benchmarks and
the search set, confirmed that held-out problems have no exact prefix matches under our
string-based filter, and manually inspected top BM25 retrievals for held-out examples (ap-
pendix C.2). We use Meta-Harness to optimize a harness for 40 iterations over a 250-problem
search set of Olympiad-difficulty math problems (OlympiadBench + Omni-MATH hard),
producing 109 candidate retrieval harnesses. We initialize the search population H from
the main baseline harnesses in this setting: zero-shot, few-shot, and ACE. We select a single
harness based on search-set performance using GPT-OSS-20B (Appendix B.2). We evaluate
this harness on 200 previously unseen IMO-level problems drawn from IMO-AnswerBench,
IMO-ProofBench, and ArXivMath [30; 6]. In addition to GPT-OSS-20B, we evaluate the
same retrieval harness on four models not seen during search: GPT-5.4-nano, GPT-5.4-mini,
Gemini-3.1-Flash-Lite, and Gemini-3-Flash. We follow the standard evaluation protocol
of prior work [30] and report accuracy averaged over three samples per problem.
Results. Table 6 compares the discovered harness against no retrieval, dense retrieval using
the separate embedding model text-embedding-3-small, random few-shot prompting, and
BM25 retrieval.
```

## ตัวอย่าง 3: Natural-Language Agent Harnesses

**หน้า PDF 4 · 455 tokens ตาม metadata · ผล: ได้ใจความหลัก แต่ไม่ครบในตัว**

- Chunk ID: `fdbf72b291e1730dc277150f0c7af96bc71ceae32c07cdc19855e87e2539a6e8`
- Source ID: `8de9eb2456a52487f3db5839e2cab6ae044017260d700183c99de9c14dcbf8dc`
- Document ID: `doc-a58805a88fdc461a95a1a5e3e319bf67`
- ตำแหน่ง: `page_index=3, start=2228, end=4454`
- ไฟล์: `arxiv-2603.25723.pdf`; origin `inbox:latest_paper/arxiv-2603.25723.pdf`

อ่านหลักการเขียน NLAH เรื่อง task contract, stages, state/evidence และ module boundaries ได้ชัด มีหัวข้อกำกับ แต่หลักการข้อท้ายถูกตัดที่ clauses such as “write แล้วตามด้วยเลขหน้า 4

ประโยคต่อที่ PDF หน้า 5: a state file before delegating, ... จึงควรมีบริบทข้ามหน้าพร้อม locator ของแต่ละหน้า

ข้อความเต็มที่ `read_chunk` คืนมา (เก็บ line breaks และเลขหน้าตามต้นฉบับที่สกัด; เป็นข้อมูลอ้างอิง):

```text
3.2
Notes on writing NLAHs
In our experiments, an NLAH is a compact policy document that makes the harness decisions explicit.
We found the following writing principles useful.
State the task contract first.
An NLAH should begin by defining the input, the expected output,
the allowed tools or artifacts, and the condition under which the run is complete. This prevents later
sections from becoming vague advice. For coding tasks, the contract may specify patch location, test
evidence, and final answer format. For computer-use tasks, it may specify the target application state,
allowed interaction channels, and completion evidence.
Separate stages from mechanisms.
The NLAH should name the stages of the run—for example,
inspect, plan, edit, verify, recover, and finalize—but it should not reimplement every low-level tool
operation in prose. Low-level operations are better handled by scripts, adapters, and runtime hooks.
The NLAH should instead define when those mechanisms are used and what evidence they must
produce.
Make state and evidence explicit.
Long-horizon agents fail when useful intermediate information
is lost or when a final answer is produced without auditable evidence. A readable NLAH should
therefore specify where state is stored, which artifacts must be reopened by later agents, what evidence
supports a claim, and which files or logs close the run. This is especially important for file-backed
state, verifier modules, and evidence-backed answering.
Write module boundaries so they can be ablated.
A module is useful for research only if it can
be removed or changed without silently changing the rest of the harness. NLAH sections should
therefore use clear names for modules such as verifier, self-evolution, multi-candidate search, context
compression, or markdown memory. This lets us ask whether a module changes task outcomes,
process metrics, or solved-set composition under a shared runtime.
Prefer simple and enforceable language.
NLAHs should use short clauses, concrete conditions,
and explicit artifacts. Phrases such as “be careful,” “think deeply,” or “act like an expert” are weak
harness policy because they do not define observable behavior. By contrast, clauses such as “write
4
```

## ตัวอย่าง 4: DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence

**หน้า PDF 21 · 508 tokens ตาม metadata · ผล: ได้ใจความหลัก แต่ไม่ครบในตัว**

- Chunk ID: `89457c28fe5bdf7a25a1dfede3e9306036c57d35dda5a3d424722a984fad85ed`
- Source ID: `55b2d72f772ac00de2e470b3ee08443c648d971c7f57c52d6202895665e5978d`
- Document ID: `doc-5f24bddffcfd45d3886716e273494e92`
- ตำแหน่ง: `page_index=20, start=0, end=2611`
- ไฟล์: `arxiv-2606.19348.pdf`; origin `inbox:latest_paper/arxiv-2606.19348.pdf`

ส่วน activation checkpointing อธิบายการกำหนด tensor และใช้ TorchFX ได้เป็นเรื่องเป็นราว แต่ต้น chunk เป็นท้ายประโยคเรื่อง compressed KV จากหน้าก่อน มีสมการที่แสดงเป็นหลายบรรทัด และเปลี่ยนหัวข้อกลาง chunk

แยกขอบเขตหัวข้อ และตรวจบริบทข้ามหน้าของย่อหน้า compressed KV; ยังไม่ได้ตรวจการแสดงสมการจากภาพ PDF

ข้อความเต็มที่ `read_chunk` คืนมา (เก็บ line breaks และเลขหน้าตามต้นฉบับที่สกัด; เป็นข้อมูลอ้างอิง):

```text
producing a fixed length of 𝑠
𝑚+ 1 compressed entries, in which exist some padding entries. In
the second stage, an all-gather operation across all CP ranks collects the locally compressed KV
entries. Then, a fused select-and-pad operator reorganizes them into the full set of compressed
KV entries with a total length of cp_size · 𝑠
𝑚. Any padding entries are placed at the tail. For
HCA and the indexer in CSA, the visible range of compressed KV entries for each query token
can be precomputed by rules. For the sparse attention in CSA, the top-𝑘selector explicitly
specifies the indices of visible compressed KV entries for each query.
3.4.4. Extended Automatic Differentiation for Flexible Activation Checkpointing
Conventional activation checkpointing implementations operate at the granularity of an entire
module, deciding whether to retain or recompute its output activations during the backward
pass. This coarse granularity often leads to suboptimal trade-offs between recomputation cost
and activation memory footprint. An alternative approach is to manually implement the forward
and backward logic of an entire layer, explicitly managing tensor checkpointing states. While
enabling fine-grained control, this method loses the convenience of the automatic differentiation
framework, substantially increasing development complexity.
To achieve fine-grained control without sacrificing programming efficiency, we implement a
tensor-level activation checkpointing mechanism with automatic differentiation support. With
this mechanism, developers only need to implement the forward pass and selectively annotate
individual tensors for automatic checkpointing and recomputation. Our framework leverages
TorchFX (Reed et al., 2022) to trace the full computation graph. For each annotated tensor, it
performs a backward traversal to identify the minimal subgraph required for its recomputation.
We define these minimal subgraphs as recomputation graphs and insert them into the backward
logic just before the corresponding gradient computation.
Compared with the manual implementation, this design introduces no additional overhead
during training. Recomputation in this framework is implemented by directly freeing the
GPU memory of the annotated tensor and reusing the storage pointer from the recomputed
tensor, without any GPU memory copy. Furthermore, since graph tracing executes the model
concretely, we can track the underlying storage pointer of each tensor, which enables automatic
deduplication of recomputation for tensors that share storage (e.g., the input and output of a
reshape operation).
```

## ตัวอย่าง 5: Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering

**หน้า PDF 50 · 502 tokens ตาม metadata · ผล: รายการอ้างอิง**

- Chunk ID: `ff828bcab2b1c4a4bb13e7c957befd8c86e030c6eb972a6359801fb4e3f0ea86`
- Source ID: `5f06a75d0819795b077bf41fb61a79db9174aa3e024d5a70b7fde4ccff2088a5`
- Document ID: `doc-93aedcb4c8d94121a4be7f26ad604194`
- ตำแหน่ง: `page_index=49, start=1202, end=2681`
- ไฟล์: `arxiv-2604.08224.pdf`; origin `inbox:latest_paper/arxiv-2604.08224.pdf`

ระบุเอกสารและ URL ได้ เป็นบรรณานุกรมตั้งแต่ ORKG/OpenAI ไปถึง MemGPT และงานสำรวจ latency ข้อมูลนี้ใช้ตามหาแหล่งอ้างอิงได้ แต่ไม่อธิบายผลวิจัยหรือเหตุผลของบทความที่กำลังอ่าน

ไม่ตีตราว่าข้อความไร้ประโยชน์ แต่ควรแยก reference ออกจาก body สำหรับการค้นหลักฐานเนื้อหา

ข้อความเต็มที่ `read_chunk` คืนมา (เก็บ line breaks และเลขหน้าตามต้นฉบับที่สกัด; เป็นข้อมูลอ้างอิง):

```text
A. Oelen, M. Y. Jaradeh, and S. Auer. Introducing orkg ask: An ai-driven scholarly literature search and exploration
system taking a neuro-symbolic approach. In International Conference on Web Engineering, pages 11–25. Springer,
2025.
OpenAI.
Function
calling
and
other
API
updates.
https://openai.com/index/
function-calling-and-other-api-updates/, June 2023a. OpenAI blog post, June 13, 2023.
OpenAI. GPT-4 technical report. arXiv preprint arXiv:2303.08774, 2023b. URL https://arxiv.org/abs/2303.08774.
OpenAI. Introducing codex. https://openai.com/index/introducing-codex/, May 2025a. Accessed: 2026-04-06.
OpenAI. Introducing deep research. https://openai.com/index/introducing-deep-research/, Feb. 2025b. OpenAI
release post, February 2, 2025; accessed 2026-04-02.
OpenAPI Initiative. Openapi specification version 3.1.0, 2021. URL https://spec.openapis.org/oas/v3.1.0.html.
L. Ouyang, J. Wu, X. Jiang, D. Almeida, C. Wainwright, P. Mishkin, C. Zhang, S. Agarwal, K. Slama, A. Ray,
et al. Training language models to follow instructions with human feedback. In Advances in Neural Information
Processing Systems, volume 35, pages 27730–27744, 2022.
C. Packer, S. Wooders, K. Lin, V. Fang, S. G. Patil, I. Stoica, and J. E. Gonzalez. MemGPT: Towards LLMs as
operating systems. arXiv preprint arXiv:2310.08560, 2023. doi: 10.48550/arXiv.2310.08560.
G. Park, S. Lee, and Y. Park. Minimizing response latency in llm-based agent systems: A comprehensive survey.
IEEE Access, 2026.
```

## ตัวอย่าง 6: Natural-Language Agent Harnesses

**หน้า PDF 3 · 110 tokens ตาม metadata · ผล: ได้ใจความหลัก แต่ไม่ครบในตัว**

- Chunk ID: `2607fdd396eaaf8b721d6dd28d5e89bd87902360988f706b6de4bb8c58532ab3`
- Source ID: `8de9eb2456a52487f3db5839e2cab6ae044017260d700183c99de9c14dcbf8dc`
- Document ID: `doc-a58805a88fdc461a95a1a5e3e319bf67`
- ตำแหน่ง: `page_index=2, start=2165, end=2702`
- ไฟล์: `arxiv-2603.25723.pdf`; origin `inbox:latest_paper/arxiv-2603.25723.pdf`

อธิบายหน้าที่ของ runtime policy, NLAH และ scripts/adapters ได้ชัด ประโยคครบ แต่เริ่มที่ The second layer และเล่าชั้นที่ 2–4 โดยไม่มีชั้นแรก/ภาพรวม และไม่ได้ขยาย IHR ใน chunk นี้

หน้าต้นฉบับก่อน offset 2165 อธิบายระบบสี่ชั้นและ base agent จึงควรดึงบริบทส่วนนั้นเมื่อตอบเรื่องสถาปัตยกรรมทั้งหมด

ข้อความเต็มที่ `read_chunk` คืนมา (เก็บ line breaks และเลขหน้าตามต้นฉบับที่สกัด; เป็นข้อมูลอ้างอิง):

```text
The second layer is the runtime policy: a
fixed instruction that turns the base agent into IHR by defining how it should interpret and execute
harness documents. The third layer is the NLAH: the natural-language policy document that describes
the stages, roles, state rules, verification rules, recovery rules, and stopping conditions of a task run.
The fourth layer is the set of scripts and adapters: deterministic code used for exact operations such
as running tests, parsing results, calling benchmark tools, or checking artifacts.
3
```

## ตัวอย่าง 7: LinearRAG: Linear Graph Retrieval Augmented Generation on Large-scale Corpora

**หน้า PDF 7 · 504 tokens ตาม metadata · ผล: ตารางอ่านยาก ต้องระวังการจับคู่ตัวเลข**

- Chunk ID: `dbdce69b82d9ae88442b0ee13a51eeb598962209e4ae1221206e7ac74d637975`
- Source ID: `1df0bd67b590f331d7928c65bbdc0a086ce6c41195428a8f3670683dcd3de533`
- Document ID: `doc-c976e31f2e2e47008e6240ccad899de6`
- ตำแหน่ง: `page_index=6, start=247, end=1515`
- ไฟล์: `arxiv-2510.10114.pdf`; origin `inbox:latest_paper/arxiv-2510.10114.pdf`

หัวชื่อ benchmark และชื่อวิธียังอยู่ จึงพออนุมานโครงสร้างตารางได้ แต่ค่าทุกช่องกลายเป็นบรรทัดแยก หัวตารางแบบหลายระดับหาย และ caption ที่บอกหน่วย/ความหมายอยู่นอก chunk ท้ายชิ้นปนต้นหัวข้อ Experiments

อย่าอ้างผลตัวเลขจากชิ้นนี้โดยไม่ตรวจตารางพร้อมหัวคอลัมน์และ caption; ไม่อ้างว่าทุกค่าอ่านไม่ได้

ข้อความเต็มที่ `read_chunk` คืนมา (เก็บ line breaks และเลขหน้าตามต้นฉบับที่สกัด; เป็นข้อมูลอ้างอิง):

```text
Method
HotpotQA
2Wiki
MuSiQue
Medical
Contain-Acc. GPT-Acc. Contain-Acc. GPT-Acc. Contain-Acc. GPT-Acc. GPT-Acc.
Direct Zero-shot LLM Inference
llama-8B
31.10
27.30
33.60
16.20
7.40
8.10
27.31
llama-13B
24.20
16.80
21.90
10.50
3.30
4.40
28.86
GPT-3.5-turbo
33.40
43.20
28.70
31.00
10.30
21.90
45.60
GPT-4o-mini
38.90
40.20
36.30
31.40
13.60
15.80
42.10
Vanilla Retrieval-Augmented-Generation
Retrieval (Top-1)
46.30
49.10
36.60
31.70
17.80
21.10
48.01
Retrieval (Top-3)
53.00
56.00
44.90
39.70
25.10
27.50
59.07
Retrieval (Top-5)
55.70
58.60
48.60
43.00
26.10
29.60
61.68
Graph-based Retrieval-Augmented-Generation Methods
KGP
61.50
60.90
31.60
30.00
25.60
30.10
54.22
G-retriever
42.20
40.60
46.60
27.10
14.40
15.50
50.36
RAPTOR
55.90
58.30
50.10
42.10
23.30
27.40
55.75
E2GraphRAG
61.00
63.90
54.30
38.10
23.80
26.20
58.00
LightRAG
60.30
59.50
55.20
39.00
27.40
28.60
54.36
HippoRAG
57.00
59.30
66.10
59.90
29.30
24.10
55.04
GFM-RAG
62.70
65.60
66.80
59.60
29.90
34.60
56.07
HippoRAG2
62.90
64.30
62.70
55.00
31.00
35.00
60.77
LinearRAG (Ours)
64.30
66.50
70.20
63.70
33.90
37.00
63.72
4
EXPERIMENTS
In this section, we conduct comprehensive experiments to verify the effectiveness and efficiency of
LinearRAG. Specifically, we aim to answer the following questions.
```

## ตัวอย่าง 8: DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence

**หน้า PDF 17 · 355 tokens ตาม metadata · ผล: ได้ใจความหลัก แต่ไม่ครบในตัว**

- Chunk ID: `c7244b7201528ddc559c0c62be7679b65c63b00b55a79e25cbabfa8825529dbe`
- Source ID: `55b2d72f772ac00de2e470b3ee08443c648d971c7f57c52d6202895665e5978d`
- Document ID: `doc-5f24bddffcfd45d3886716e273494e92`
- ตำแหน่ง: `page_index=16, start=2169, end=3903`
- ไฟล์: `arxiv-2606.19348.pdf`; origin `inbox:latest_paper/arxiv-2606.19348.pdf`

ย่อหน้าเกี่ยวกับ Z3 และ formal integer analysis อ่านเข้าใจได้ แต่ต่อไปเปิดอีกหัวข้อ Numerical Precision and Bitwise Reproducibility แล้วจบกลางประโยค TileLang provides ตามด้วยเลขหน้า 17

PDF หน้า 18 ต่อว่า IEEE-compliant intrinsics ... จึงต้องอ่านต่อก่อนอ้างรายละเอียดที่ TileLang provides

ข้อความเต็มที่ `read_chunk` คืนมา (เก็บ line breaks และเลขหน้าตามต้นฉบับที่สกัด; เป็นข้อมูลอ้างอิง):

```text
During compilation passes such
as layout inference, memory hazard detection, and bound analysis, the compiler must verify
whether integer expressions satisfy specific properties to enable the corresponding optimiza-
tions. Therefore, stronger formal analysis capabilities can unlock more advanced and complex
optimization opportunities.
To this end, we integrate the Z3 SMT solver (De Moura and Bjørner, 2008) into TileLang’s
algebraic system, providing formal analysis capability for most integer expressions in tensor
programs. We strike a balance between computational overhead and formal expressiveness by
translating TileLang’s integer expressions into Z3’s quantifier-free non-linear integer arithmetic
(QF_NIA). Based on Integer Linear Programming (ILP) solvers, QF_NIA seamlessly resolves
standard linear integer expressions common in kernels. Furthermore, its inherent non-linear
reasoning capacity effectively addresses advanced challenges like vectorization over variable
tensor shapes. Under reasonable resource limits, Z3 elevates overall optimization performance
while restricting compilation time overhead to just a few seconds. The impact is substantial
across multiple passes, including vectorization, barrier insertion, and code simplification.
Numerical Precision and Bitwise Reproducibility.
In production settings, numerical correct-
ness and reproducibility are as critical as raw throughput. We therefore prioritize accuracy by
default: fast-math optimizations are disabled at the compiler level, and precision-affecting ap-
proximations are provided only as explicit, opt-in frontend operators (e.g., T.__exp, T.__log,
and T.__sin). Conversely, when strict IEEE-754 semantics are required, TileLang provides
17
```

## ตัวอย่าง 9: Qwen3-Omni Technical Report

**หน้า PDF 17 · 474 tokens ตาม metadata · ผล: บริบทตารางไม่ครบสำหรับอ้างตัวเลข**

- Chunk ID: `ac066f9ae483365e284b8141f52c0668c1d34bc09b2df9d6b4df6c9b5cd1717e`
- Source ID: `4608d7f5d0694dd09a66144dac921797e161331d92b5eef133615bec392ec928`
- Document ID: `doc-041ea792341d4cf898d4e38e6a1499ed`
- ตำแหน่ง: `page_index=16, start=1315, end=2716`
- ไฟล์: `arxiv-2509.17765.pdf`; origin `inbox:latest_paper/arxiv-2509.17765.pdf`

ช่วงแรกเป็นค่าจาก Table 17 แต่ขาดชื่อโมเดลที่เป็นหัวคอลัมน์จากส่วนก่อนหน้า ต่อด้วย footnotes และเริ่ม Table 18 อีกตาราง ปลายชิ้นตัดที่ GTZAN Acc. โดยค่าของแถวนั้นอยู่นอก chunk

ต้องแยกแต่ละตาราง เก็บ caption/ชื่อคอลัมน์กับค่าของแถวเดียวกัน; การเดาชื่อโมเดลจากลำดับตัวเลขใน chunk นี้ไม่เพียงพอ

ข้อความเต็มที่ `read_chunk` คืนมา (เก็บ line breaks และเลขหน้าตามต้นฉบับที่สกัด; เป็นข้อมูลอ้างอิง):

```text
ASR (wer)
Fleurs-avg
(19 lang)a
-
15.67
8.09
4.48
5.55
14.04
8.63
8.88
Lyric ASR (wer)
MIR-1K (vocal-only)b
6.45
23.33
18.73
11.87
9.85
8.15
11.15
10.47
Opencpop-test
2.98
31.01
16.06
7.93
6.49
2.84
6.11
4.52
S2TT (BLEU)
Fleurs-en2xxc
-
30.35
37.85
-
39.25
29.22
36.24
36.04
Fleurs-xx2en
-
27.54
32.81
-
35.41
28.61
30.50
30.22
Fleurs-zh2xx
-
17.03
22.05
-
26.63
17.97
23.74
23.77
Fleurs-xx2zh
-
28.75
34.82
-
37.50
27.68
34.51
34.49
a These 19 languages include Arabic, Cantonese, Chinese, Dutch, English, French, German, Indonesian, Italian, Japanese, Korean, Malay,
Portuguese, Russian, Spanish, Thai, Turkish, Urdu, Vietnamese.
b Transcription is converted into Simplified Chinese.
c The results encompass translations across 15 languages: Arabic, Cantonese, Chinese, English, French, German, Indonesian, Italian, Japanese,
Korean, Portuguese, Russian, Spanish, Thai, Vietnamese. For notation, “en2xx” denotes translation from English into each of the other 14 target
languages, where “xx” ranges over the remaining language codes.
Table 18: Music understanding performance for Audio→Text tasks, comparing Qwen3-Omni-Thinking
with baselines. The highest scores are shown in bold.
Best Specialist
Models
GPT-4o
-Audio
Gemini-2.5
-Pro
Qwen2.5
-Omni
Qwen3-Omni
-30B-A3B-Thinking
Qwen3-Omni
-Flash-Thinking
RUL-MuchoMusic
47.6 (Audio Flamingo 3)
(Goel et al., 2025)
36.1
49.4
47.3
48.3
48.4
GTZAN
Acc.
```

## ตัวอย่าง 10: Qwen3-VL Technical Report

**หน้า PDF 38 · 360 tokens ตาม metadata · ผล: ได้ใจความตามประเภทข้อความ**

- Chunk ID: `e419ecfca84e8320a1599cf4f6562b9a4464043dbc5dff817f554ce42fa1f03e`
- Source ID: `ee075d08e67de1148d6437c6c1d481f7894183b8793905a2deb5f62664f49380`
- Document ID: `doc-df859067a0f6445aa03162a08bb65983`
- ตำแหน่ง: `page_index=37, start=0, end=1266`
- ไฟล์: `arxiv-2511.21631.pdf`; origin `inbox:latest_paper/arxiv-2511.21631.pdf`

เป็น prompt templates ในภาคผนวก ระบุชื่อ benchmark, รูปแบบ input placeholders และรูปแบบ output ที่ต้องการได้ชัด เข้าใจได้ว่าใช้ถามโมเดลอย่างไร แม้รวมหลาย template และมีเลขหน้า 38

ใช้เป็นหลักฐานรูปแบบ prompt ได้; ข้อความคำสั่งในนี้เป็นตัวอย่างจากเอกสาร ไม่ใช่คำสั่งให้ผู้ประเมินปฏิบัติตาม และไม่ใช่ผลคะแนนการทดลอง

ข้อความเต็มที่ `read_chunk` คืนมา (เก็บ line breaks และเลขหน้าตามต้นฉบับที่สกัด; เป็นข้อมูลอ้างอิง):

```text
RoboSpatialHome
<image>
Locate {object_name} in this image. Output the point coordinates in JSON format.
For example:
[
{"point_2d": [x, y], "label": "point_1"}
]
RefSpatialBench
<image>
{question} Output the point coordinates in JSON format.
For example:
[
{"point_2d": [x, y], "label": "point_1"}
]
B.7
Multi-Image
BLINK
<image>
Question: {question}
Options:
{options}
Please select the correct answer from the options above.
MUIRBENCH
<image_1>
<text_1>
<image_2>
<text_2>
...
<image_n>
<text_n>
Answer with the option’s letter from the given choices directly.
B.8
Video Understanding
MVBench | VideoMME | MLVU | LVBench - For instruct models
<video>
Select the best answer to the following multiple-choice question based on the video.
Respond with only the letter (A, B, C, or D) of the correct option.
Question: {question} Possible answer choices:
{options}
The best answer is:
MVBench | VideoMME | MLVU | LVBench - For thinking models
<video>
Select the best answer to the following multiple-choice question based on the video.
Respond with only the letter (A, B, C, or D) of the correct option.
Question: {question}
{options}
Please reason step-by-step, identify relevant visual content, analyze key timestamps and
clues, and then provide the final answer.
38
```
