# Retrieval assessment — Codex, 20 September 2026

Assessor: **Codex**, newly inspecting the actual query results and original extracted passages in this task. No external model judge or automatic semantic grader was used. Assertions in tests record the reviewed source locator; they do not perform semantic judgement.

## Original failure and controlled changes

1. The existing lexical implementation returned no hits for `การประมาณค่าแบบเบย์สำหรับข้อมูลที่มีโครงสร้างหลายระดับ` against the real brms PDF. [Before](semantic-before-2026-09-20.json).
2. Adding the pinned multilingual-e5-small embedding path returned hits, but the top three were predictor syntax on page index 6 and bibliography on page index 24. Codex assessed these as weak evidence for the requested Bayesian multilevel estimation topic, not a passing abstract-retrieval result. [First result](semantic-after-2026-09-20.json).
3. An isolated experiment normalized only passage input with NFKC. The original query and school-grouping query retained the same scores and ordering; the tokenizer already includes normalization. This did not improve the failure and was **not added** as an application patch. [Experiment](semantic-normalization-experiment-2026-09-20.json).
4. An isolated experiment changed the embedding model to original-publisher `intfloat/multilingual-e5-base`, revision `d128750597153bb5987e10b1c3493a34e5a4502a`, keeping the same actual PDF chunks, query wording, prefixes, pooling, cosine and CPU provider. The original query retrieved the actual abstract at rank 2. This motivated adoption of base (768 dimensions); model provenance is [preserved](../third-party/embedding-model/base-experiment/). The standalone experiment itself was not counted as application integration. [Experiment results](semantic-base-experiment-2026-09-20.json).
5. The original import/search case was immediately rerun through the actual updated Store implementation. Lexical still returns zero; semantic and hybrid include page index 0/start 0 in their top 3. [Actual application result](semantic-final-query-2026-09-20.json). The targeted regression checks this exact locator plus unchanged citation integrity.

The abstract directly describes Bayesian multilevel models, supported response families, priors and model comparison. It is relevant reading for the query. The first base-model hit is still a reference list and the third is a software comparison table. Consequently **top-3 recovery improved; rank-1 relevance and general Thai retrieval quality are not certified**. The system returns evidence candidates for original-text inspection, not an answer or probability of correctness.

## Nearby cases and practical limitations

The [small-model cases](semantic-cases-2026-09-20.json) include the real PDF, an original Elsevier policy excerpt, the actual project README and measured PDF-extraction counts. The [base experiment](semantic-base-experiment-2026-09-20.json) uses the same preserved PDF chunks only; do not treat the two records as a same-corpus aggregate benchmark.

| Query | Codex's inspection |
|---|---|
| How can knowledge about parameters be incorporated before analysing observations? | Small retrieves a prior-distributions section; base retrieves discussion of prior choice and sampling. Both contain relevant context, but lower-ranked references/parameter syntax are incomplete support. |
| How are observations grouped within schools represented? | Neither experiment recovers the directly useful school-nesting introduction among the displayed top three. This remains a known retrieval weakness. |
| นักเรียนอยู่ในชั้นเรียนและโรงเรียนเดียวกันวิเคราะห์อย่างไร | Small retrieves unrelated project documentation in the mixed corpus; base's PDF-only results remain indirect package/group-prior material. This case is not accepted as a successful retrieval of the desired explanation. |
| Authors remain responsible for the contents of the manuscript | Small ranks the actual policy excerpt about checking references first. It supports source checking, not every aspect of the broader responsibility statement. Base was not assessed on this policy case in the isolated experiment. |

These are a handful of diagnostic queries, not a benchmark of Thai/English accuracy or large-corpus capacity. Base improves the original case at the cost of a larger image and more CPU work. No translation service, fabricated evidence, hidden lexical fallback or score threshold calibrated to these examples was introduced. Use role/source filters and inspect context; hybrid also retains lexical matching when words are available.
