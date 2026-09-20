import csv
import shutil
from pathlib import Path
from pypdf import PdfReader

from research_rag_mcp.models import STAGES
from research_rag_mcp.store import Store

ROOT = Path(__file__).resolve().parents[1]


def prepare_files(root):
    store = Store(root)
    shutil.copyfile(ROOT/'tests/evidence/brms.pdf', store.root/'inbox/brms.pdf')
    shutil.copyfile(ROOT/'tests/evidence/elsevier-policy-excerpt.txt', store.root/'inbox/guidelines.txt')
    shutil.copyfile(ROOT/'README.md', store.root/'inbox/project-readme.md')
    reader = PdfReader(store.root/'inbox/brms.pdf')
    lengths = [len(p.extract_text() or '') for p in reader.pages]
    with (store.root/'inbox/extraction-metrics.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['page_index', 'text_characters'])
        writer.writerows(enumerate(lengths))
    return store, lengths


def populate(root):
    store, lengths = prepare_files(root)
    store.start_project('Inspect extraction from the supplied brms article',
                        'Protocol verification using a real PDF; not a study of model quality', [], 0, 'start')
    sources = {}
    for filename, origin, role, title in [
        ('brms.pdf', 'https://doi.org/10.18637/jss.v080.i01', 'literature', 'brms: An R Package for Bayesian Multilevel Models Using Stan'),
        ('guidelines.txt', 'https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals', 'journal_guidelines', 'Elsevier policy excerpt'),
        ('project-readme.md', 'Local project README', 'project_note', 'Research RAG README'),
        ('extraction-metrics.csv', 'Actual pypdf page extraction measurements of brms.pdf, computed by the integration test', 'results', 'PDF extraction measurements'),
    ]:
        result = store.import_document(filename, origin, role, {'title': title}, store.read()['revision'], filename)
        sources[role] = result['result']['source_id']
    return store, sources, lengths


def cite(store, source_id, text=None):
    page = store.page(source_id, 0)
    quote = text or page['text'][:min(len(page['text']), 300)]
    start = page['text'].index(quote)
    return dict(source_id=source_id, page_index=0, start=start, end=start+len(quote), quote=quote, relation='context')


def blocks(stage, citation=None):
    # These are explicitly unresolved protocol records, not invented research findings.
    return [dict(section=section, text='Scientific content has not been assessed in this protocol test.',
                 basis='unresolved', citations=[citation] if citation else []) for section in STAGES[stage]['sections']]


def save(store, stage, content=None, dependencies=None, artifact_id=None):
    result = store.save_artifact(stage, 'Protocol exercise: '+stage, content or blocks(stage),
                                 ['Integration behavior only; no scientific assessment or journal submission.'],
                                 dependencies or [], store.read()['revision'], __import__('uuid').uuid4().hex, artifact_id)
    return result['result']


def accepted_proposal(store, stage='question', dependencies=None):
    content = [dict(section=s, text='Protocol exercise limited to measuring the supplied PDF extraction.',
                    basis='researcher_input', citations=[]) for s in STAGES[stage]['sections']]
    artifact = save(store, stage, content, dependencies)
    store.review(artifact['id'], 'accepted', 'Protocol state-transition test; not a research reviewer',
                 'Exercise acceptance state only, not semantic correctness.', store.read()['revision'], __import__('uuid').uuid4().hex)
    return artifact
