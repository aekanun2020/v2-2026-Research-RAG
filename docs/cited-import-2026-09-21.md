# นำเข้า papers จาก cited ผ่าน MCP — 21 กันยายน 2026

ต้นทาง: `/Users/grizzlymacbookpro/Desktop/test/2026-TTS-AI Master/labs/papers/cited`

ปลายทาง inbox: `/Users/grizzlymacbookpro/Documents/ChatGPT/2026-TTS-AI/codex-research-rag-qdrant/.chunking-data/inbox/cited-20260921-165304`

Endpoint: `http://127.0.0.1:8976/mcp` · branch `codex/academic-paper-chunking`

ผู้ใช้อนุญาตข้อยกเว้นเฉพาะครั้งนี้ให้คัดลอกไฟล์ด้วย filesystem จากนั้นการอ่าน PDF, นำเข้า, ตรวจ chunks และทดสอบค้นหาทั้งหมดใช้ MCP จริง ไม่มีการเขียน JSON journal หรือ Qdrant โดยตรง

คัดลอก 221 PDF รวม 806,172,536 bytes / 6,588 หน้า ตรวจ SHA-256 ต้นทางกับไฟล์ที่คัดลอกตรงทุกไฟล์และไม่มีเนื้อหาไฟล์ซ้ำกันในชุดนี้ เก็บต้นฉบับ Desktop ไว้ครบ

ผลประมวลผล: สำเร็จ 221/221 ไฟล์ ไม่มีไฟล์นำเข้าล้มเหลว; เพิ่ม 15,902 chunks. ก่อนเริ่มมี 12 sources / 907 chunks; หลังตรวจมี 233 documents / 16,809 chunks / 16,809 indexed chunks ที่ revision 282 ตรวจเมื่อ 2026-09-21T18:49:47.483133+07:00

พบ MCP error 1 ครั้งตอน inspect_document_chunks ของไฟล์ที่ 203: /data/workspace.json ไม่พบ การตรวจ workspace_status ต่อมาพบ revision 264 / 215 sources และดัชนีครบ งานนำเข้าระบุ completed จากนั้นเรียก inspection เดิมซ้ำสำเร็จ จึงทำต่อจากไฟล์ที่ 204 โดยไม่ reimport หรือเปลี่ยน server สาเหตุของ error ครั้งนี้ยังไม่ทราบ เก็บหลักฐานและผล retry ไว้ใน JSON

ชื่อเรื่องทั้ง 221 ไฟล์ตรวจโดย Codex จากหน้าแรกผ่าน preview_inbox_document พร้อมตรวจว่าชื่อที่บันทึกปรากฏในข้อความจริง ไม่สร้างชื่อเรื่องจากชื่อไฟล์ ผู้แต่ง ปี และ DOI ยังไม่ได้ตรวจครบ จึงไม่ได้เติมฟิลด์เหล่านั้น

นำเข้าทีละไฟล์ด้วย import_document, poll job_status และตรวจ inspect_document_chunks หลังสำเร็จ ตรวจจำนวนหน้าเทียบ preview, source SHA-256, สถานะ ready, รายการเอกสารแบบแบ่งหน้า, index completeness และคง source IDs เดิมครบ ไม่มีการเปลี่ยน chunker/embedding model ในงานนี้

ทดสอบ hybrid แบบจำกัด source 3 กรณีหลังนำเข้า พร้อมเทียบ hit กับ read_source_page เป็นการตรวจว่าค้นเอกสารและย้อนถึงข้อความได้ ไม่ใช่คะแนน relevance หรือการรับรอง semantic ภาษาไทย รายละเอียดคำค้น/ตำแหน่งอยู่ใน JSON

ข้อจำกัดเดิมเรื่องประโยคข้ามหน้า ตาราง และบรรณานุกรมยังอยู่ การตรวจ spans ครอบคลุมข้อความที่สกัดได้ ไม่ได้ยืนยัน OCR, ลำดับอ่าน PDF จากภาพ หรือความถูกต้องของข้อกล่าวอ้างใน papers

- [ผลตรวจและบัญชี SHA-256/source/job IDs ทุกไฟล์](cited-import-2026-09-21.json)
- [ผลสุ่มอ่านคุณภาพ chunks ก่อนนำเข้ารอบนี้](chunk-readability-codex-2026-09-21.md)

## ผลทดสอบค้นคืนหลังนำเข้า

คำค้นทั้ง 3 ใช้ `mode=hybrid`, `limit=2` และจำกัด `source_ids` ให้ตรงเล่ม เปรียบเทียบข้อความที่คืนกับ `read_source_page` โดยใช้ page/start/end ทุกผลตรงครบ 6/6 ผล ไม่ได้ประเมิน relevance ของผลเหล่านี้

| คำค้น | ไฟล์ | หน้า PDF ที่คืน | ตรงกับต้นฉบับ |
|---|---|---|---|
| Generating sequences with recurrent neural networks | arxiv-1308.0850.pdf | 1, 43 | 2/2 |
| retrieval augmented generation knowledge intensive NLP | arxiv-2005.11401.pdf | 1, 2 | 2/2 |
| SkySim ROS2 natural language control drone swarms | arxiv-2602.01226.pdf | 1, 1 | 2/2 |

## บัญชีไฟล์

| # | ไฟล์ | ชื่อเรื่องจากต้นฉบับ | หน้า | Chunks | ผล |
|---|---|---|---:|---:|---|
| 1 | arxiv-1308.0850.pdf | Generating Sequences With Recurrent Neural Networks | 43 | 69 | completed |
| 2 | arxiv-1409.1259.pdf | On the Properties of Neural Machine Translation: Encoder–Decoder Approaches | 9 | 24 | completed |
| 3 | arxiv-1412.6980.pdf | Adam: A Method for Stochastic Optimization | 15 | 35 | completed |
| 4 | arxiv-1503.02531.pdf | Distilling the Knowledge in a Neural Network | 9 | 20 | completed |
| 5 | arxiv-1602.06023.pdf | Abstractive Text Summarization using Sequence-to-sequence RNNs and Beyond | 12 | 34 | completed |
| 6 | arxiv-1701.06538.pdf | Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer | 19 | 45 | completed |
| 7 | arxiv-1709.00103.pdf | Seq2SQL: Generating Structured Queries from Natural Language Using Reinforcement Learning | 12 | 27 | completed |
| 8 | arxiv-1712.04851.pdf | Rethinking Spatiotemporal Feature Learning: Speed-Accuracy Trade-offs in Video Classification | 17 | 35 | completed |
| 9 | arxiv-1802.05365.pdf | Deep contextualized word representations | 15 | 37 | completed |
| 10 | arxiv-1803.02155.pdf | Self-Attention with Relative Position Representations | 5 | 14 | completed |
| 11 | arxiv-1803.05457.pdf | Think you have Solved Question Answering? Try ARC, the AI2 Reasoning Challenge | 10 | 28 | completed |
| 12 | arxiv-1809.02789.pdf | Can a Suit of Armor Conduct Electricity? A New Dataset for Open Book Question Answering | 14 | 40 | completed |
| 13 | arxiv-1809.09600.pdf | HotpotQA: A Dataset for Diverse, Explainable Multi-hop Question Answering | 12 | 32 | completed |
| 14 | arxiv-1810.04805.pdf | BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding | 16 | 45 | completed |
| 15 | arxiv-1810.06683.pdf | FlowQA: Grasping Flow in History for Conversational Machine Comprehension | 15 | 38 | completed |
| 16 | arxiv-1901.07291.pdf | Cross-lingual Language Model Pretraining | 10 | 28 | completed |
| 17 | arxiv-1904.09728.pdf | Social IQA: Commonsense Reasoning about Social Interactions | 11 | 27 | completed |
| 18 | arxiv-1905.02450.pdf | MASS: Masked Sequence to Sequence Pre-training for Language Generation | 11 | 35 | completed |
| 19 | arxiv-1905.07830.pdf | HellaSwag: Can a Machine Really Finish Your Sentence? | 14 | 37 | completed |
| 20 | arxiv-1905.10044.pdf | BoolQ: Exploring the Surprising Difficulty of Natural Yes/No Questions | 13 | 35 | completed |
| 21 | arxiv-1907.11692.pdf | RoBERTa: A Robustly Optimized BERT Pretraining Approach | 13 | 34 | completed |
| 22 | arxiv-1909.11942.pdf | ALBERT: A Lite BERT for Self-supervised Learning of Language Representations | 17 | 46 | completed |
| 23 | arxiv-1910.01108.pdf | DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter | 5 | 11 | completed |
| 24 | arxiv-1910.10683.pdf | Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer | 67 | 146 | completed |
| 25 | arxiv-1910.10687.pdf | Context-Aware Sentence/Passage Term Importance Estimation For First Stage Retrieval | 9 | 35 | completed |
| 26 | arxiv-1910.13461.pdf | BART: Denoising Sequence-to-Sequence Pre-training for Natural Language Generation, Translation, and Comprehension | 10 | 29 | completed |
| 27 | arxiv-1911.11641.pdf | PIQA: Reasoning about Physical Commonsense in Natural Language | 9 | 26 | completed |
| 28 | arxiv-2001.08361.pdf | Scaling Laws for Neural Language Models | 30 | 62 | completed |
| 29 | arxiv-2002.08909.pdf | REALM: Retrieval-Augmented Language Model Pre-Training | 12 | 34 | completed |
| 30 | arxiv-2003.10555.pdf | ELECTRA: Pre-training Text Encoders as Discriminators Rather Than Generators | 18 | 45 | completed |
| 31 | arxiv-2004.04906.pdf | Dense Passage Retrieval for Open-Domain Question Answering | 13 | 38 | completed |
| 32 | arxiv-2004.05150.pdf | Longformer: The Long-Document Transformer | 17 | 47 | completed |
| 33 | arxiv-2004.13637.pdf | Recipes for building an open-domain chatbot | 25 | 63 | completed |
| 34 | arxiv-2005.03954.pdf | Towards Conversational Recommendation over Multi-Type Dialogs | 14 | 40 | completed |
| 35 | arxiv-2005.11401.pdf | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | 19 | 47 | completed |
| 36 | arxiv-2005.14165.pdf | Language Models are Few-Shot Learners | 75 | 167 | completed |
| 37 | arxiv-2006.03654.pdf | DeBERTa: Decoding-enhanced BERT with Disentangled Attention | 23 | 51 | completed |
| 38 | arxiv-2006.11477.pdf | wav2vec 2.0: A Framework for Self-Supervised Learning of Speech Representations | 19 | 45 | completed |
| 39 | arxiv-2006.15595.pdf | Rethinking Positional Encoding in Language Pre-training | 14 | 33 | completed |
| 40 | arxiv-2007.00808.pdf | Approximate Nearest Neighbor Negative Contrastive Learning for Dense Text Retrieval | 16 | 40 | completed |
| 41 | arxiv-2009.03300.pdf | Measuring Massive Multitask Language Understanding | 27 | 55 | completed |
| 42 | arxiv-2010.11934.pdf | mT5: A Massively Multilingual Pre-trained Text-to-Text Transformer | 17 | 54 | completed |
| 43 | arxiv-2102.05095.pdf | Is Space-Time Attention All You Need for Video Understanding? | 13 | 44 | completed |
| 44 | arxiv-2103.03874.pdf | Measuring Mathematical Problem Solving With the MATH Dataset | 22 | 55 | completed |
| 45 | arxiv-2104.08663.pdf | BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models | 24 | 64 | completed |
| 46 | arxiv-2104.08773.pdf | Cross-Task Generalization via Natural Language Crowdsourcing Instructions | 18 | 49 | completed |
| 47 | arxiv-2104.09864.pdf | RoFormer: Enhanced Transformer with Rotary Position Embedding | 14 | 32 | completed |
| 48 | arxiv-2106.09685.pdf | LoRA: Low-Rank Adaptation of Large Language Models | 26 | 64 | completed |
| 49 | arxiv-2107.02137.pdf | ERNIE 3.0: Large-Scale Knowledge Enhanced Pre-training for Language Understanding and Generation | 22 | 61 | completed |
| 50 | arxiv-2107.03374.pdf | Evaluating Large Language Models Trained on Code | 35 | 102 | completed |
| 51 | arxiv-2108.07258.pdf | On the Opportunities and Risks of Foundation Models | 214 | 512 | completed |
| 52 | arxiv-2108.07732.pdf | Program Synthesis with Large Language Models | 34 | 80 | completed |
| 53 | arxiv-2108.12409.pdf | Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation | 25 | 62 | completed |
| 54 | arxiv-2109.01652.pdf | Finetuned Language Models Are Zero-Shot Learners | 46 | 107 | completed |
| 55 | arxiv-2109.07958.pdf | TruthfulQA: Measuring How Models Mimic Human Falsehoods | 39 | 69 | completed |
| 56 | arxiv-2109.12264.pdf | More Than Reading Comprehension: A Survey on Datasets and Metrics of Textual Question Answering | 18 | 55 | completed |
| 57 | arxiv-2110.05456.pdf | Rome was built in 1776: A Case Study on Factual Correctness in Knowledge-Grounded Response Generation | 16 | 41 | completed |
| 58 | arxiv-2110.08207.pdf | Multitask Prompted Training Enables Zero-Shot Task Generalization | 216 | 265 | completed |
| 59 | arxiv-2110.14168.pdf | Training Verifiers to Solve Math Word Problems | 22 | 32 | completed |
| 60 | arxiv-2110.15943.pdf | MetaICL: Learning to Learn In Context | 19 | 65 | completed |
| 61 | arxiv-2112.04426.pdf | Improving language models by retrieving from trillions of tokens | 43 | 100 | completed |
| 62 | arxiv-2112.09332.pdf | WebGPT: Browser-assisted question-answering with human feedback | 32 | 61 | completed |
| 63 | arxiv-2112.11446.pdf | Scaling Language Models: Methods, Analysis & Insights from Training Gopher | 120 | 242 | completed |
| 64 | arxiv-2201.08239.pdf | LaMDA: Language Models for Dialog Applications | 47 | 101 | completed |
| 65 | arxiv-2201.11990.pdf | Using DeepSpeed and Megatron to Train Megatron-Turing NLG 530B, A Large-Scale Generative Language Model | 44 | 78 | completed |
| 66 | arxiv-2202.04824.pdf | AdaPrompt: Adaptive Model Training for Prompt-based NLP | 12 | 33 | completed |
| 67 | arxiv-2203.13474.pdf | CodeGen: An Open Large Language Model for Code with Multi-Turn Program Synthesis | 25 | 57 | completed |
| 68 | arxiv-2203.15556.pdf | Training Compute-Optimal Large Language Models | 36 | 78 | completed |
| 69 | arxiv-2204.02311.pdf | PaLM: Scaling Language Modeling with Pathways | 87 | 213 | completed |
| 70 | arxiv-2204.14198.pdf | Flamingo: a Visual Language Model for Few-Shot Learning | 54 | 131 | completed |
| 71 | arxiv-2205.01068.pdf | OPT: Open Pre-trained Transformer Language Models | 30 | 70 | completed |
| 72 | arxiv-2205.05131.pdf | UL2: Unifying Language Learning Paradigms | 39 | 95 | completed |
| 73 | arxiv-2205.10487.pdf | Scaling Laws and Interpretability of Learning from Repeated Data | 23 | 51 | completed |
| 74 | arxiv-2206.06336.pdf | Language Models are General-Purpose Interfaces | 32 | 75 | completed |
| 75 | arxiv-2207.05608.pdf | Inner Monologue: Embodied Reasoning through Planning with Language Models | 25 | 61 | completed |
| 76 | arxiv-2208.01448.pdf | AlexaTM 20B: Few-Shot Learning Using a Large-Scale Multilingual Seq2seq Model | 32 | 80 | completed |
| 77 | arxiv-2209.14375.pdf | Improving alignment of dialogue agents via targeted human judgements | 77 | 154 | completed |
| 78 | arxiv-2210.02414.pdf | GLM-130B: An Open Bilingual Pre-trained Model | 56 | 139 | completed |
| 79 | arxiv-2210.02928.pdf | MuRAG: Multimodal Retrieval-Augmented Generator for Open Question Answering over Images and Text | 13 | 33 | completed |
| 80 | arxiv-2210.03629.pdf | ReAct: Synergizing Reasoning and Acting in Language Models | 33 | 80 | completed |
| 81 | arxiv-2210.05549.pdf | Continual Training of Language Models for Few-Shot Learning | 13 | 41 | completed |
| 82 | arxiv-2210.11399.pdf | Transcending Scaling Laws with 0.1% Extra Compute | 21 | 48 | completed |
| 83 | arxiv-2210.11416.pdf | Scaling Instruction-Finetuned Language Models | 54 | 143 | completed |
| 84 | arxiv-2211.01786.pdf | Crosslingual Generalization through Multitask Finetuning | 119 | 221 | completed |
| 85 | arxiv-2211.05100.pdf | BLOOM: A 176B-Parameter Open-Access Multilingual Language Model | 73 | 148 | completed |
| 86 | arxiv-2211.09085.pdf | Galactica: A Large Language Model for Science | 58 | 133 | completed |
| 87 | arxiv-2211.12561.pdf | Retrieval-Augmented Multimodal Language Modeling | 15 | 45 | completed |
| 88 | arxiv-2211.12701.pdf | Continual Learning of Natural Language Processing Tasks: A Survey | 16 | 55 | completed |
| 89 | arxiv-2212.10403.pdf | Towards Reasoning in Large Language Models: A Survey | 15 | 45 | completed |
| 90 | arxiv-2212.10511.pdf | When Not to Trust Language Models: Investigating Effectiveness of Parametric and Non-Parametric Memories | 19 | 46 | completed |
| 91 | arxiv-2212.10560.pdf | Self-Instruct: Aligning Language Models with Self-Generated Instructions | 23 | 54 | completed |
| 92 | arxiv-2212.12017.pdf | OPT-IML: Scaling Language Model Instruction Meta Learning through the Lens of Generalization | 56 | 137 | completed |
| 93 | arxiv-2212.13138.pdf | Large Language Models Encode Clinical Knowledge | 44 | 110 | completed |
| 94 | arxiv-2301.00234.pdf | A Survey on In-context Learning | 22 | 74 | completed |
| 95 | arxiv-2301.12652.pdf | REPLUG: Retrieval-Augmented Black-Box Language Models | 12 | 38 | completed |
| 96 | arxiv-2302.05128.pdf | Translating Natural Language to Planning Goals with Large-Language Models | 15 | 42 | completed |
| 97 | arxiv-2302.07842.pdf | Augmented Language Models: a Survey | 33 | 91 | completed |
| 98 | arxiv-2302.09419.pdf | A Comprehensive Survey on Pretrained Foundation Models: A History from BERT to ChatGPT | 99 | 230 | completed |
| 99 | arxiv-2302.12813.pdf | Check Your Facts and Try Again: Improving Large Language Models with External Knowledge and Automated Feedback | 15 | 41 | completed |
| 100 | arxiv-2302.13971.pdf | LLaMA: Open and Efficient Foundation Language Models | 27 | 70 | completed |
| 101 | arxiv-2302.14045.pdf | Language Is Not All You Need: Aligning Perception with Language Models | 26 | 52 | completed |
| 102 | arxiv-2303.00855.pdf | Grounded Decoding: Guiding Text Generation with Grounded Models for Embodied Agents | 26 | 62 | completed |
| 103 | arxiv-2303.12712.pdf | Sparks of Artificial General Intelligence: Early experiments with GPT-4 | 155 | 342 | completed |
| 104 | arxiv-2303.17580.pdf | HuggingGPT: Solving AI Tasks with ChatGPT and its Friends in Hugging Face | 27 | 64 | completed |
| 105 | arxiv-2303.18223.pdf | A Survey of Large Language Models | 144 | 581 | completed |
| 106 | arxiv-2304.08485.pdf | Visual Instruction Tuning | 25 | 59 | completed |
| 107 | arxiv-2304.11477.pdf | LLM+P: Empowering Large Language Models with Optimal Planning Proficiency | 8 | 29 | completed |
| 108 | arxiv-2305.02309.pdf | CodeGen2: Lessons for Training LLMs on Programming and Natural Languages | 12 | 30 | completed |
| 109 | arxiv-2305.03047.pdf | Principle-Driven Self-Alignment of Language Models from Scratch with Minimal Human Supervision | 55 | 109 | completed |
| 110 | arxiv-2305.05968.pdf | Investigating Forgetting in Pre-Trained Representations Through Continual Learning | 11 | 29 | completed |
| 111 | arxiv-2305.06161.pdf | StarCoder: may the source be with you! | 55 | 130 | completed |
| 112 | arxiv-2305.09617.pdf | Towards Expert-Level Medical Question Answering with Large Language Models | 30 | 73 | completed |
| 113 | arxiv-2305.10403.pdf | PaLM 2 Technical Report | 93 | 187 | completed |
| 114 | arxiv-2305.12270.pdf | Mitigating Catastrophic Forgetting in Task-Incremental Continual Learning with Adaptive Classification Criterion | 11 | 29 | completed |
| 115 | arxiv-2305.13048.pdf | RWKV: Reinventing RNNs for the Transformer Era | 30 | 67 | completed |
| 116 | arxiv-2305.14314.pdf | QLoRA: Efficient Finetuning of Quantized LLMs | 26 | 63 | completed |
| 117 | arxiv-2305.16291.pdf | VOYAGER: An Open-Ended Embodied Agent with Large Language Models | 42 | 88 | completed |
| 118 | arxiv-2305.18290.pdf | Direct Preference Optimization: Your Language Model is Secretly a Reward Model | 27 | 70 | completed |
| 119 | arxiv-2306.01116.pdf | The RefinedWeb Dataset for Falcon LLM: Outperforming Curated Corpora with Web Data, and Web Data Only | 32 | 85 | completed |
| 120 | arxiv-2306.02707.pdf | Orca: Progressive Learning from Complex Explanation Traces of GPT-4 | 51 | 95 | completed |
| 121 | arxiv-2306.04751.pdf | How Far Can Camels Go? Exploring the State of Instruction Tuning on Open Resources | 23 | 64 | completed |
| 122 | arxiv-2306.08302.pdf | Unifying Large Language Models and Knowledge Graphs: A Roadmap | 28 | 112 | completed |
| 123 | arxiv-2306.08647.pdf | Language to Rewards for Robotic Skill Synthesis | 31 | 65 | completed |
| 124 | arxiv-2306.11644.pdf | Textbooks Are All You Need | 26 | 61 | completed |
| 125 | arxiv-2306.13304.pdf | ToolQA: A Dataset for LLM Question Answering with External Tools | 25 | 55 | completed |
| 126 | arxiv-2307.02485.pdf | Building Cooperative Embodied Agents Modularly with Large Language Models | 29 | 64 | completed |
| 127 | arxiv-2307.03170.pdf | Focused Transformer: Contrastive Training for Context Scaling | 28 | 61 | completed |
| 128 | arxiv-2307.04642.pdf | TRAQ: Trustworthy Retrieval Augmented Question Answering via Conformal Prediction | 23 | 49 | completed |
| 129 | arxiv-2307.05973.pdf | VoxPoser: Composable 3D Value Maps for Robotic Manipulation with Language Models | 23 | 59 | completed |
| 130 | arxiv-2307.09288.pdf | Llama 2: Open Foundation and Fine-Tuned Chat Models | 77 | 180 | completed |
| 131 | arxiv-2307.10169.pdf | Challenges and Applications of Large Language Models | 72 | 250 | completed |
| 132 | arxiv-2308.00352.pdf | MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework | 29 | 56 | completed |
| 133 | arxiv-2308.01285.pdf | Flows: Building Blocks of Reasoning and Collaborating AI | 22 | 57 | completed |
| 134 | arxiv-2308.03028.pdf | Pre-Trained Large Language Models for Industrial Control | 25 | 54 | completed |
| 135 | arxiv-2308.08155.pdf | AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation | 43 | 104 | completed |
| 136 | arxiv-2308.10435.pdf | GPT-in-the-Loop: Adaptive Decision-Making for Multiagent Systems | 8 | 21 | completed |
| 137 | arxiv-2308.10882.pdf | Giraffe: Adventures in Expanding Context Lengths in LLMs | 17 | 33 | completed |
| 138 | arxiv-2308.11432.pdf | A Survey on Large Language Model based Autonomous Agents | 42 | 97 | completed |
| 139 | arxiv-2308.12950.pdf | Code Llama: Open Foundation Models for Code | 48 | 116 | completed |
| 140 | arxiv-2308.12966.pdf | Qwen-VL: A Versatile Vision-Language Model for Understanding, Localization, Text Reading, and Beyond | 24 | 51 | completed |
| 141 | arxiv-2308.14263.pdf | Cross-Modal Retrieval: A Systematic Review of Methods and Future Directions | 35 | 166 | completed |
| 142 | arxiv-2309.00267.pdf | RLAIF vs. RLHF: Scaling Reinforcement Learning from Human Feedback with AI Feedback | 28 | 68 | completed |
| 143 | arxiv-2309.05463.pdf | Textbooks Are All You Need II: phi-1.5 technical report | 16 | 31 | completed |
| 144 | arxiv-2309.05519.pdf | NExT-GPT: Any-to-Any Multimodal LLM | 32 | 79 | completed |
| 145 | arxiv-2309.07864.pdf | The Rise and Potential of Large Language Model Based Agents: A Survey | 86 | 229 | completed |
| 146 | arxiv-2309.11489.pdf | Text2Reward: Reward Shaping with Language Models for Reinforcement Learning | 37 | 82 | completed |
| 147 | arxiv-2309.16292.pdf | DiLu: A Knowledge-Driven Approach to Autonomous Driving with Large Language Models | 20 | 46 | completed |
| 148 | arxiv-2309.16436.pdf | Neuro Symbolic Reasoning for Planning: Counterexample Guided Inductive Synthesis Using Large Language Models and Satisfiability Solving | 25 | 43 | completed |
| 149 | arxiv-2310.01415.pdf | GPT-Driver: Learning to Drive with GPT | 12 | 30 | completed |
| 150 | arxiv-2310.03026.pdf | LanguageMPC: Large Language Models as Decision Makers for Autonomous Driving | 8 | 30 | completed |
| 151 | arxiv-2310.06825.pdf | Mistral 7B | 9 | 19 | completed |
| 152 | arxiv-2310.09690.pdf | Configuration Validation with Large Language Models | 12 | 58 | completed |
| 153 | arxiv-2310.11511.pdf | Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | 30 | 68 | completed |
| 154 | arxiv-2310.12931.pdf | Eureka: Human-Level Reward Design via Coding Large Language Models | 45 | 104 | completed |
| 155 | arxiv-2310.16944.pdf | Zephyr: Direct Distillation of LM Alignment | 14 | 35 | completed |
| 156 | arxiv-2311.01378.pdf | Vision-Language Foundation Models as Effective Robot Imitators | 19 | 46 | completed |
| 157 | arxiv-2311.05437.pdf | LLaVA-Plus: Learning to Use Tools for Creating Multimodal Agents | 25 | 72 | completed |
| 158 | arxiv-2311.08377.pdf | Learning to Filter Context for Retrieval-Augmented Generation | 12 | 35 | completed |
| 159 | arxiv-2311.13884.pdf | Controlling Large Language Model-based Agents for Large-Scale Decision-Making: An Actor-Critic Approach | 13 | 34 | completed |
| 160 | arxiv-2312.00752.pdf | Mamba: Linear-Time Sequence Modeling with Selective State Spaces | 36 | 93 | completed |
| 161 | arxiv-2312.00812.pdf | Empowering Autonomous Driving with Large Language Models: A Safety Perspective | 13 | 29 | completed |
| 162 | arxiv-2312.09397.pdf | Personalized Autonomous Driving with Large Language Models: Field Experiments | 8 | 26 | completed |
| 163 | arxiv-2312.10997.pdf | Retrieval-Augmented Generation for Large Language Models: A Survey | 21 | 70 | completed |
| 164 | arxiv-2312.11361.pdf | “Knowing When You Don’t Know”: A Multilingual Relevance Assessment Dataset for Robust Retrieval-Augmented Generation | 19 | 61 | completed |
| 165 | arxiv-2312.11805.pdf | Gemini: A Family of Highly Capable Multimodal Models | 90 | 157 | completed |
| 166 | arxiv-2312.15503.pdf | Llama2Vec: Unsupervised Adaptation of Large Language Models for Dense Retrieval | 11 | 32 | completed |
| 167 | arxiv-2312.16044.pdf | LLMLight: Large Language Models as Traffic Signal Control Agents | 17 | 58 | completed |
| 168 | arxiv-2401.00396.pdf | RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models | 16 | 37 | completed |
| 169 | arxiv-2401.03568.pdf | Agent AI: Surveying the Horizons of Multimodal Interaction | 80 | 177 | completed |
| 170 | arxiv-2401.05561.pdf | TrustLLM: Trustworthiness in Large Language Models – A Principle and Benchmark | 119 | 318 | completed |
| 171 | arxiv-2401.18059.pdf | RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval | 23 | 49 | completed |
| 172 | arxiv-2402.07016.pdf | REALM: RAG-Driven Enhancement of Multimodal Electronic Health Records Analysis via Large Language Models | 14 | 40 | completed |
| 173 | arxiv-2402.09171.pdf | Automated Unit Test Improvement using Large Language Models at Meta | 12 | 42 | completed |
| 174 | arxiv-2402.12289.pdf | DriveVLM: The Convergence of Autonomous Driving and Large Vision-Language Models | 30 | 61 | completed |
| 175 | arxiv-2403.08295.pdf | Gemma: Open Models Based on Gemini Research and Technology | 17 | 42 | completed |
| 176 | arxiv-2403.10131.pdf | RAFT: Adapting Language Model to Domain Specific RAG | 12 | 27 | completed |
| 177 | arxiv-2403.19964.pdf | FairRAG: Fair Human Generation via Fair Retrieval Augmentation | 13 | 34 | completed |
| 178 | arxiv-2404.03647.pdf | Capabilities of Large Language Models in Control Engineering: A Benchmark Study on GPT-4, Claude 3 Opus, and Gemini 1.0 Ultra | 26 | 53 | completed |
| 179 | arxiv-2404.06345.pdf | AgentsCoDriver: Large Language Model Empowered Collaborative Driving with Lifelong Learning | 12 | 36 | completed |
| 180 | arxiv-2404.06413.pdf | Foundation Models to the Rescue: Deadlock Resolution in Connected Multi-Robot Systems | 15 | 41 | completed |
| 181 | arxiv-2404.14294.pdf | A Survey on Efficient Inference for Large Language Models | 36 | 145 | completed |
| 182 | arxiv-2405.19893.pdf | Similarity is Not All You Need: Endowing Retrieval-Augmented Generation with Multi–layered Thoughts | 12 | 30 | completed |
| 183 | arxiv-2406.01587.pdf | PlanAgent: A Multi-modal Large Language Agent for Closed-loop Vehicle Motion Planning | 11 | 36 | completed |
| 184 | arxiv-2406.09246.pdf | OpenVLA: An Open-Source Vision-Language-Action Model | 37 | 95 | completed |
| 185 | arxiv-2407.01219.pdf | Searching for Best Practices in Retrieval-Augmented Generation | 22 | 51 | completed |
| 186 | arxiv-2407.01463.pdf | Retrieval-augmented generation in multilingual settings | 12 | 36 | completed |
| 187 | arxiv-2407.05131.pdf | RULE: Reliable Multimodal RAG for Factuality in Medical Vision Language Models | 13 | 37 | completed |
| 188 | arxiv-2407.08550.pdf | Incorporating Large Language Models into Production Systems for Enhanced Task Automation and Flexibility — Moving Towards Autonomous Systems | 16 | 23 | completed |
| 189 | arxiv-2407.08735.pdf | Real-Time Anomaly Detection and Reactive Planning with Large Language Models | 24 | 78 | completed |
| 190 | arxiv-2407.12801.pdf | Evaluation of LLMs Biases Towards Elite Universities: A Persona-Based Exploration | 10 | 16 | completed |
| 191 | arxiv-2407.16833.pdf | Retrieval Augmented Generation or Long-Context LLMs? A Comprehensive Study and Hybrid Approach | 13 | 36 | completed |
| 192 | arxiv-2407.20242.pdf | BadRobot: Jailbreaking Embodied LLM Agents in the Physical World | 40 | 86 | completed |
| 193 | arxiv-2408.04821.pdf | VLM-MPC: Model Predictive Controller Augmented Vision Language Model for Autonomous Driving | 23 | 43 | completed |
| 194 | arxiv-2408.08535.pdf | CommunityKG-RAG: Leveraging Community Structures in Knowledge Graphs for Advanced Retrieval-Augmented Generation in Fact-Checking | 12 | 28 | completed |
| 195 | arxiv-2408.09017.pdf | Meta Knowledge for Retrieval Augmented Large Language Models | 8 | 26 | completed |
| 196 | arxiv-2408.14484.pdf | Agentic Retrieval-Augmented Generation for Time Series Analysis | 14 | 69 | completed |
| 197 | arxiv-2409.01652.pdf | ReKep: Spatio-Temporal Reasoning of Relational Keypoint Constraints for Robotic Manipulation | 30 | 71 | completed |
| 198 | arxiv-2409.05401.pdf | Benchmarking and Building Zero-Shot Hindi Retrieval Model with Hindi-BEIR and NLLB-E5 | 21 | 45 | completed |
| 199 | arxiv-2409.05591.pdf | MemoRAG: Boosting Long Context Processing with Global Memory-Enhanced Retrieval Augmentation | 12 | 53 | completed |
| 200 | arxiv-2409.08597.pdf | Enhancing LLM-based ASR Accuracy with Retrieval-Augmented Generation | 5 | 18 | completed |
| 201 | arxiv-2409.09046.pdf | HyPA-RAG: A Hybrid Parameter Adaptive Retrieval-Augmented Generation System for AI Legal and Policy Applications | 19 | 38 | completed |
| 202 | arxiv-2409.09916.pdf | SFR-RAG: Towards Contextually Faithful LLMs | 12 | 28 | completed |
| 203 | arxiv-2409.09989.pdf | Comprehensive Study on Sentiment Analysis: From Rule based to modern LLM based system | 16 | 18 | completed |
| 204 | arxiv-2409.16430.pdf | A Comprehensive Survey of Bias in LLMs: Current Landscape and Future Directions | 15 | 27 | completed |
| 205 | arxiv-2410.19811.pdf | ControlAgent: Automating Control System Design via Novel Integration of LLM Agents and Domain Expertise | 42 | 78 | completed |
| 206 | arxiv-2410.22662.pdf | EMOS: Embodiment-Aware Heterogeneous Multi-Robot Operating System with LLM Agents | 21 | 48 | completed |
| 207 | arxiv-2410.24164.pdf | π0: A Vision-Language-Action Flow Model for General Robot Control | 17 | 53 | completed |
| 208 | arxiv-2411.08561.pdf | LogLLM: Log-based Anomaly Detection Using Large Language Models | 11 | 42 | completed |
| 209 | arxiv-2502.16804.pdf | Multi-Agent Autonomous Driving Systems with Large Language Models: A Survey of Recent Advances, Resources, and Future Directions | 18 | 50 | completed |
| 210 | arxiv-2503.11739.pdf | CoLLMLight: Cooperative Large Language Model Agents for Network-Wide Traffic Signal Control | 14 | 46 | completed |
| 211 | arxiv-2503.18666.pdf | AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents | 12 | 43 | completed |
| 212 | arxiv-2504.04187.pdf | AttackLLM: LLM-based Attack Pattern Generation for an Industrial Control System | 9 | 24 | completed |
| 213 | arxiv-2505.19567.pdf | LLM-Agent-Controller: A Universal Multi-Agent Large Language Model System as a Control Engineer | 41 | 58 | completed |
| 214 | arxiv-2506.19160.pdf | AgenticControl: An Automated Control Design Framework Using Large Language Models | 48 | 89 | completed |
| 215 | arxiv-2508.05702.pdf | Grid-Agent: An LLM-Powered Multi-Agent System for Power Grid Control | 10 | 26 | completed |
| 216 | arxiv-2510.04519.pdf | Spec2Control: Automating PLC/DCS Control-Logic Engineering from Natural Language Requirements with LLMs - A Multi-Plant Evaluation | 12 | 46 | completed |
| 217 | arxiv-2510.05547.pdf | ARRC: Advanced Reasoning Robot Control—Knowledge-Driven Autonomous Manipulation Using Retrieval-Augmented Generation | 8 | 21 | completed |
| 218 | arxiv-2511.00337.pdf | Large Language Models for Control | 8 | 24 | completed |
| 219 | arxiv-2512.13004.pdf | Large Language Models for Power System Applications: A Comprehensive Literature Survey | 17 | 22 | completed |
| 220 | arxiv-2601.15486.pdf | An LLM-Agnostic, MAVLink-Based Drone Command and Control Interface and Agentic Harness Using the Model Context Protocol | 67 | 136 | completed |
| 221 | arxiv-2602.01226.pdf | SkySim: A ROS2-based Simulation Environment for Natural Language Control of Drone Swarms using Large Language Models | 6 | 16 | completed |
