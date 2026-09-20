# Real integration evidence

- [brms article](https://doi.org/10.18637/jss.v080.i01): Paul-Christian Bürkner (2017), *brms: An R Package for Bayesian Multilevel Models Using Stan*, Journal of Statistical Software, 80(1). [Original publisher](https://www.jstatsoft.org/article/view/v080i01), [DOI](https://doi.org/10.18637/jss.v080.i01), [original PDF](https://www.jstatsoft.org/index.php/jss/article/download/v080i01/1143). SHA-256 `35757e85ffb002fcb6c5dc34fec0daa6a84302d552e7555f2551838c4599fffb`. The historical test runs used the unchanged, previously verified project lab copy; the PDF itself is intentionally excluded from this repository. [publisher license](https://www.jstatsoft.org/about): CC-BY-3.0. Used as evidence, not application code.
- [Short policy excerpt](elsevier-policy-excerpt.txt): short quotation from [Elsevier's journal AI policy](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals), checked on 2026-09-20. This limited excerpt tests source attribution, not complete journal compliance.

Tests compute CSV data from the actual PDF's extracted page lengths. They do not fabricate study outcomes, replace Crossref, simulate an MCP server or call an external model. Test review identities explicitly represent protocol exercises, not researcher endorsement. Thai retrieval uses the actual project README. Live Crossref tests call the public production API when `RESEARCH_RAG_LIVE_TESTS=1`.

## Prepare the real PDF locally

Place the original publisher PDF at `tests/evidence/brms.pdf` before running tests. A verified copy remains in the original local project. The PDF is ignored by Git and is not included in this repository, including its first commit. Do not substitute generated or mock document content.

The original download URL is linked above. After saving the PDF, verify the exact bytes from the repository root:

```sh
python3 -c "from pathlib import Path; import hashlib; p=Path('tests/evidence/brms.pdf'); actual=hashlib.sha256(p.read_bytes()).hexdigest(); expected='35757e85ffb002fcb6c5dc34fec0daa6a84302d552e7555f2551838c4599fffb'; assert actual == expected, f'Unexpected PDF SHA-256: {actual}'; print('Verified original brms PDF')"
```

If the file is absent or differs, obtain the verified original before testing; do not relax the expected hash. Preparing a file is separate from ingestion, which must be performed through MCP for the authorized workflow.
