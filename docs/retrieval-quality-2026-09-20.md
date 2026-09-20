# Thai retrieval quality — 20 September 2026

Status: version 0.2.4 deployed to the local Docker Compose services. [Runtime and data preservation](quality-state-preservation-2026-09-20.json), [container state](quality-containers-after-2026-09-20.json).

Assessor: **Codex**, inspecting retrieved passages and original evidence directly. No external LLM judge is used. Scripts only call the actual MCP tools, verify exact spans, and aggregate Codex-recorded judgments. The BGE cross-encoder is part of retrieval, not the evaluator.

## Reproduced problem and controlled changes

The same 10 original papers were reimported through MCP after the authorized cleanup. Their source hashes match the previous corpus. [Fresh before results](quality-before-2026-09-20.json) reproduced all 36 previous source/page/span/text outputs. Codex's original topical assessment was 6/10 direct at rank 1 and 7/10 with any direct passage in the first three; both negative controls returned irrelevant passages.

The T04 question asks how a word vector can depend on sentence context. A direct ELMo passage was already indexed at E5 rank 6, but the original search returned the first three cosine-ranked chunks immediately. The [failing MCP regression](quality-failing-before-2026-09-20.json) preserves this result. Coverage and hashes were intact; cleanup/reimport alone did not improve ranking.

An earlier longer-chunk experiment failed and was reverted to the original active chunk set. There are 547 active chunks and 71 inactive experimental chunks retained for audit (618 total indexed), 10 sources, 221 inbox originals, and revision 24. No additional production paper is imported for this change.

The [experiment ledger](quality-experiments-2026-09-20.json) records separate changes and rejected hypotheses:

1. GTE reranking did not recover the original failing case and was rejected. [Actual output](quality-rerank-focused-2026-09-20.json).
2. Replacing only that model with BGE recovered the direct ELMo explanation at rank 1. [Original case](quality-bge-focused-2026-09-20.json), [related cases](quality-bge-related-2026-09-20.json), [all original queries without filtering](quality-bge-regression-2026-09-20.json).
3. A title prefix increased a negative query's false-positive score and reduced T04's ranking quality. It was reverted. [Rejected result](quality-title-focused-2026-09-20.json).
4. Scoring the original first page independently separated topical papers from the two controls in the observed calibration results. [Calibration](quality-document-calibration-2026-09-20.json). A document threshold of 0.002 passed the original controls but failed held-out H02: it removed Adam, whose score was 0.001467, below the negative N02 maximum of 0.001566 on Linux. The automatic gate was rejected, not retuned on that question. [Gated evaluation and failure](quality-container-evaluation-2026-09-20.json), [immediate H02 rerun with gate disabled](quality-h02-without-gate-2026-09-20.json). No score threshold is enabled in the final defaults.

## Runtime behavior

`semantic` uses multilingual-e5-base to select 50 candidates by exact cosine. `hybrid` selects candidates using the existing BM25/E5 reciprocal-rank fusion. Both rerank query–passage pairs with pinned BGE int8 on CPU and expose original first-page relevance scores for inspection. Neither document nor passage scores filter results by default. Original chunks, quotations, page offsets, source IDs and embeddings are unchanged. There is no translation, generated summary, query-specific paper rule or model API call.

The runtime verifies pinned asset SHA-256 values before inference, uses only CPUExecutionProvider and does not silently switch to another implementation. [BGE provenance](../third-party/bge-reranker-model/README.md), [runtime](../src/research_rag_mcp/reranking.py), [MCP contract](tools.md), [Final Docker build](quality-final-build-2026-09-20.txt), [18 final packaged source hashes](quality-final-image-source-hashes-2026-09-20.json).

`min_document_score=0` is the default. Positive values explicitly enable a caller-selected first-page filter; no safe general cutoff was established. `rerank=false` explicitly selects the original first-stage ranking; lexical mode retains BM25 behavior. These are user-selected modes, not automatic fallbacks. Missing/corrupt assets or indexes raise tool errors. Scores are ranking signals, not calibrated confidence.

## Evaluation records

- [All exact Thai questions and fixed split](quality-cases-2026-09-20.json): 10 original topical questions + 2 controls; 6 initially unused paraphrases + 2 controls. H01/H02 were subsequently seen while rejecting the gate; only H03–H06 and HN01–HN02 were untouched before the final no-filter policy. This set concerns the same 10-paper corpus, not unseen papers.
- [Final no-filter container MCP responses, every returned passage and original-span check](quality-final-candidates-2026-09-20.json). This container runs with external networking disabled and uses the installed image, not a source substitute.
- [Codex's per-passage judgments](quality-codex-assessment-2026-09-20.json). Matching a filename alone is not a relevance pass.
- [MCP verifier](../scripts/verify_retrieval_mcp.py) and [contract verifier](../scripts/verify_retrieval_contract_mcp.py).

## Codex assessment of the final retrieval policy

| Measurement | Before | Final |
|---|---:|---:|
| Original topical questions: direct rank 1 | 6/10 | 9/10 |
| Original topical questions: any direct passage in top 3 | 7/10 | 10/10 |
| Untouched final topical questions (H03–H06): direct rank 1 / any in top 3 | Not measured | 3/4 / 3/4 |
| All six additional paraphrases (H01/H02 already seen during gate rejection): rank 1 / top 3 | Not measured | 4/6 / 5/6 |
| Negative controls returning irrelevant candidates | 2/2 original controls | 4/4 original + additional controls |
| Exact spans against MCP read_source_page | 36/36 | 60/60 |

**H06 still fails:** the right summarization paper is retrieved, but none of the first three passages explains copying unseen words with a pointer. **T01 rank 1 regresses:** it is a cut-off statement; a useful explanation remains in later hits. No claim of perfect retrieval or reliable rejection of unrelated questions is made. Exact-span checks validate the extracted page text and offsets, not scientific entailment or visual PDF extraction quality.

The full no-filter run explicitly sent `min_document_score=0` to the installed candidate image, preserving its warm cache and unchanged inference implementation. The final build changes that default to 0 and makes the limitation explicit. [Final-image default H02 test](quality-final-default-2026-09-20.json) uses no override and recovers the same direct passage. This distinction is retained in the raw schemas and arguments, not hidden.

### Actual Thai questions and top-three judgments

`ตรง` means directly addresses a substantive part of the question, not a complete answer. Order in each cell is rank 1 → 2 → 3. Page numbers below are one-based physical PDF pages; raw citations use zero-based indices.

| ID | Exact question | Before | Final | First result: paper / page |
|---|---|---|---|---|
| T01 | ถ่ายทอดความรู้จากโมเดลหลายตัวไปยังโมเดลขนาดเล็กตัวเดียวได้อย่างไร | ตรง / ตรง / ตรง | บางส่วน / ตรง / ตรง | Distilling the Knowledge in a Neural Network / 1 |
| T02 | ปรับอัตราการเรียนรู้แยกสำหรับแต่ละพารามิเตอร์โดยใช้ค่าเฉลี่ยของความชันและความชันกำลังสองได้อย่างไร | บางส่วน / บางส่วน / ไม่ตรง | ตรง / ไม่ตรง / บางส่วน | Adam: A Method for Stochastic Optimization / 1 |
| T03 | แปลงคำถามภาษาคนให้เป็นคำสั่งค้นข้อมูลในตารางโดยใช้ผลการรันคำสั่งเป็นรางวัลได้อย่างไร | ตรง / ตรง / ตรง | ตรง / ตรง / ตรง | Seq2SQL: Generating Structured Queries from Natural Language using Reinforcement Learning / 1 |
| T04 | ทำให้เวกเตอร์ของคำเดียวกันเปลี่ยนไปตามบริบทของประโยคได้อย่างไร | ไม่ตรง / ไม่ตรง / ไม่ตรง | ตรง / บางส่วน / ไม่ตรง | Deep contextualized word representations / 1 |
| T05 | ใช้ระยะห่างระหว่างคำแทนการระบุตำแหน่งแบบตายตัวในกลไกความสนใจได้อย่างไร | ตรง / ไม่ตรง / ไม่ตรง | ตรง / บางส่วน / ตรง | Self-Attention with Relative Position Representations / 1 |
| T06 | เพิ่มความจุของโครงข่ายโดยเลือกใช้ผู้เชี่ยวชาญเพียงบางตัวสำหรับข้อมูลแต่ละตัวอย่างได้อย่างไร | บางส่วน / ตรง / ตรง | ตรง / ตรง / บางส่วน | Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer / 4 |
| T07 | สร้างลายมือเขียนจากข้อความโดยให้โครงข่ายเรียนรู้การทำนายจุดถัดไปได้อย่างไร | ตรง / ไม่ตรง / ตรง | ตรง / ตรง / ตรง | Generating Sequences With Recurrent Neural Networks / 26 |
| T08 | เหตุใดคุณภาพการแปลด้วยตัวเข้ารหัสและตัวถอดรหัสจึงลดลงเมื่อประโยคยาวหรือมีคำที่ไม่รู้จัก | ตรง / ตรง / ตรง | ตรง / บางส่วน / บางส่วน | On the Properties of Neural Machine Translation: Encoder–Decoder Approaches / 5 |
| T09 | สรุปข้อความแบบเขียนใหม่จะจัดการคำหายากและโครงสร้างระดับคำกับประโยคได้อย่างไร | บางส่วน / ไม่ตรง / ไม่ตรง | ตรง / บางส่วน / บางส่วน | Abstractive Text Summarization using Sequence-to-sequence RNNs and Beyond / 4 |
| T10 | จำแนกวิดีโอให้เร็วขึ้นโดยแยกการเรียนรู้ข้อมูลเชิงพื้นที่กับเชิงเวลาได้อย่างไร | ตรง / บางส่วน / ตรง | ตรง / บางส่วน / ตรง | Rethinking Spatiotemporal Feature Learning: Speed-Accuracy Trade-offs in Video Classification / 1 |
| N01 | อะไรเป็นสาเหตุให้แผ่นเปลือกโลกเคลื่อนที่และเกิดภูเขาไฟ | ไม่ตรง / ไม่ตรง / ไม่ตรง | ไม่ตรง / ไม่ตรง / ไม่ตรง | Generating Sequences With Recurrent Neural Networks / 13 |
| N02 | คำนวณวงโคจรของดาวหางรอบดวงอาทิตย์ได้อย่างไร | ไม่ตรง / ไม่ตรง / ไม่ตรง | ไม่ตรง / ไม่ตรง / ไม่ตรง | Adam: A Method for Stochastic Optimization / 14 |
| H01 | จะบีบอัดความรู้ของระบบทำนายหลายตัวให้ใช้โมเดลเล็กเพียงตัวเดียวตอนใช้งานได้อย่างไร | — | บางส่วน / ตรง / บางส่วน | Distilling the Knowledge in a Neural Network / 1 |
| H02 | การใช้โมเมนต์อันดับหนึ่งและอันดับสองของเกรเดียนต์ช่วยปรับขนาดก้าวในการเรียนรู้ได้อย่างไร | — | ตรง / บางส่วน / ตรง | Adam: A Method for Stochastic Optimization / 1 |
| H03 | ถ้าคำหนึ่งมีหลายความหมาย จะสร้างตัวแทนของคำนั้นให้สะท้อนคำที่อยู่รอบข้างได้อย่างไร | — | ตรง / ตรง / ตรง | Deep contextualized word representations / 7 |
| H04 | การเลือกเปิดใช้ผู้เชี่ยวชาญแค่บางส่วนช่วยขยายจำนวนพารามิเตอร์โดยไม่เพิ่มงานคำนวณตามสัดส่วนได้อย่างไร | — | ตรง / ตรง / ตรง | Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer / 2 |
| H05 | โมเดลสร้างลายมือสามารถใช้ข้อความที่ต้องการเขียนเป็นเงื่อนไขของการทำนายตำแหน่งปากกาได้อย่างไร | — | ตรง / บางส่วน / บางส่วน | Generating Sequences With Recurrent Neural Networks / 24 |
| H06 | ระบบสรุปบทความจะดึงคำที่ไม่เคยพบตอนฝึกจากต้นฉบับมาใส่ในบทสรุปได้อย่างไร | — | บางส่วน / ไม่ตรง / ไม่ตรง | Abstractive Text Summarization using Sequence-to-sequence RNNs and Beyond / 4 |
| HN01 | เหตุใดน้ำทะเลจึงขึ้นลงตามตำแหน่งของดวงจันทร์ | — | ไม่ตรง / ไม่ตรง / ไม่ตรง | Generating Sequences With Recurrent Neural Networks / 12 |
| HN02 | หินอัคนีและหินตะกอนเกิดจากกระบวนการที่แตกต่างกันอย่างไร | — | ไม่ตรง / ไม่ตรง / ไม่ตรง | Distilling the Knowledge in a Neural Network / 2 |

Full quotations, stable IDs and character spans are in the [raw responses](quality-final-candidates-2026-09-20.json); reasons and per-hit judgments are in the [Codex assessment](quality-codex-assessment-2026-09-20.json). The [earlier gated judgments](quality-gated-codex-assessment-2026-09-20.json) are historical and excluded from final metrics.

[Hybrid run](quality-final-hybrid-2026-09-20.json) returned the same ordered source/span/text evidence for all 20 queries; [exact comparison](quality-mode-comparison-2026-09-20.json). [Final MCP contract](quality-final-contract-2026-09-20.json) verifies filters, error paths, original-ranking reproduction and chunk/context lookups. [Production retrieval check](quality-production-retrieval-2026-09-20.json) uses the final defaults without a threshold override.

[Production/default comparison](quality-production-comparison-2026-09-20.json) confirms T04, H02 and N02 retain identical candidate evidence after deployment. [Native connected MCP verification](quality-native-runtime-2026-09-20.json) independently confirms the BGE default and an exact T04 source-page span through the task’s connected tools.

## Client timeout regression

The [initial workflow check](quality-container-workflow-before-2026-09-20.txt) passed the semantic/chunk MCP lifecycle test but timed out during `import_document` in the eight-stage case. The traceback identifies `ClientSession(read_timeout_seconds=30)` even though its HTTP client already allowed 300 seconds. Only that test client's request timeout was aligned to 300 seconds; server, real imports, model and assertions remained unchanged. The exact failing case is rerun separately in [this record](quality-container-workflow-after-2026-09-20.txt). A longer timeout accommodates CPU work; it is not a latency improvement.

## Limits

The corpus is only 10 papers. Top-three recovery does not mean each result is relevant or that an answer is complete. Some rank-1 results can regress, which must be reported rather than hidden by the aggregate. A first page can omit relevant material from later sections or contain front matter; the filter can produce false negatives. The attempted cutoff failed a held-out paraphrase and was withdrawn from defaults. Out-of-corpus questions still return irrelevant candidates; reliable automatic abstention remains unresolved. Quantized scores and order can vary across CPU/runtime platforms; production claims use the installed Linux image results.

New queries take tens of seconds on the observed CPU container; repeated queries may hit the in-process score cache. Use sufficient MCP read timeout. Claude Desktop/Windows UI behavior, all 221 papers, journal compliance and full manuscript faithfulness are not validated by these retrieval checks.
