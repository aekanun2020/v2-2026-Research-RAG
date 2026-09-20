"""Transactional evidence, versioned artifacts and separate human decisions."""
import csv
import hashlib
import io
import json
import math
import secrets
import shutil
import sqlite3
import uuid
from importlib.metadata import version
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from .models import STAGES, Bibliography, Block, Citation
from .retrieval import chunks, rank, deduplicate
from . import semantic, reranking
from .documents import DocumentManagement, migrate
from .cleanup import WorkspaceCleanup


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def require_text(value, name, maximum=30000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'{name} requires nonempty text of at most {maximum} characters')


class Store(DocumentManagement, WorkspaceCleanup):
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        for name in ('inbox', 'sources', 'exports', 'backups'):
            (self.root / name).mkdir(exist_ok=True)
        with self.connect() as db:
            schema = db.execute('PRAGMA user_version').fetchone()[0]
            if schema not in (0, 1, 2, 3, 4):
                raise ValueError('Unsupported workspace schema')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS meta(id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, project TEXT);
                INSERT OR IGNORE INTO meta VALUES(1,0,NULL);
                CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, source_id TEXT NOT NULL, page_index INTEGER, start INTEGER, end INTEGER, text TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS chunks_source ON chunks(source_id);
                CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS versions(artifact_id TEXT, version INTEGER, data TEXT NOT NULL, PRIMARY KEY(artifact_id,version));
                CREATE TABLE IF NOT EXISTS searches(id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, time TEXT, operation TEXT, actor TEXT, revision INTEGER, data TEXT);
                CREATE TABLE IF NOT EXISTS requests(key TEXT PRIMARY KEY, fingerprint TEXT, response TEXT);
                CREATE TABLE IF NOT EXISTS embeddings(chunk_id TEXT PRIMARY KEY, model_fingerprint TEXT NOT NULL,
                    text_sha256 TEXT NOT NULL, vector BLOB NOT NULL, vector_sha256 TEXT NOT NULL, dimensions INTEGER NOT NULL, windows INTEGER NOT NULL);

            ''')
            migrate(db)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.root / 'research.sqlite', timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def state(db):
        meta = db.execute('SELECT * FROM meta WHERE id=1').fetchone()
        pending = db.execute('SELECT data FROM cleanup_jobs WHERE id=1').fetchone()
        job = json.loads(pending['data']) if pending else None
        return {
            'revision': meta['revision'], 'project': json.loads(meta['project']) if meta['project'] else None,
            'sources': {row['id']: json.loads(row['data']) for row in db.execute('SELECT * FROM documents ORDER BY id')},
            'artifacts': {row['id']: json.loads(row['data']) for row in db.execute('SELECT * FROM artifacts ORDER BY rowid')},
            'disabled_spans': [dict(r) for r in db.execute("SELECT c.source_id,c.page_index,c.start,c.end,m.status FROM chunks c JOIN chunk_metadata m ON m.chunk_id=c.id JOIN chunk_sets s ON s.id=m.chunk_set_id WHERE m.status!='active' AND s.active=1")],
            'searches': [json.loads(row['data']) for row in db.execute('SELECT * FROM searches ORDER BY rowid')],
            'pending_cleanup': {k: job[k] for k in ('scope', 'plan_hash', 'expected_revision', 'idempotency_key')} if job else None,
        }

    def read(self):
        with self.connect() as db:
            db.execute('BEGIN')
            return self.state(db)

    def mutate(self, operation, payload, expected_revision, key, action, actor='mcp-client'):
        require_text(key, 'idempotency_key', 200)
        fingerprint = sha(dump([operation, payload, actor]).encode())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.require_no_pending_cleanup(db)
            previous = db.execute('SELECT * FROM requests WHERE key=?', (key,)).fetchone()
            if previous:
                if previous['response'] is None:
                    raise ValueError('Idempotency key retired by cleanup; inspect current state and use a new key for new work')
                if previous['fingerprint'] != fingerprint:
                    raise ValueError('Idempotency key already used with different input')
                return json.loads(previous['response'])
            state = self.state(db)
            if expected_revision != state['revision']:
                raise ValueError('Stale revision; read workspace_status and reconsider')
            result = action(db, state)
            revision = state['revision'] + 1
            response = {'revision': revision, 'result': result}
            db.execute('UPDATE meta SET revision=? WHERE id=1', (revision,))
            db.execute('INSERT INTO events(time,operation,actor,revision,data) VALUES(?,?,?,?,?)',
                       (now(), operation, actor, revision, dump(payload)))
            db.execute('INSERT INTO requests VALUES(?,?,?)', (key, fingerprint, dump(response)))
            return response

    def start_project(self, topic, goal, unknowns, expected_revision, key):
        require_text(topic, 'topic', 2000)
        require_text(goal, 'goal', 5000)
        for value in unknowns:
            require_text(value, 'unknown')
        project = dict(topic=topic, goal=goal, unknowns=unknowns)
        def action(db, state):
            if state['project']:
                raise ValueError('Project already exists; preserve it and refine questions in a versioned question artifact')
            db.execute('UPDATE meta SET project=? WHERE id=1', (dump(project),))
            return project
        return self.mutate('start_project', project, expected_revision, key, action)

    def import_document(self, filename, origin, role, bibliography, expected_revision, key, document_id=None):
        require_text(origin, 'origin', 4000)
        if role not in ('literature', 'protocol', 'data', 'results', 'project_note', 'journal_guidelines'):
            raise ValueError('Unknown source role')
        bibliography = Bibliography.model_validate(bibliography).model_dump()
        path = (self.root / 'inbox' / filename).resolve()
        if not path.is_relative_to((self.root / 'inbox').resolve()) or not path.is_file():
            raise ValueError('Supply an existing file inside this workspace inbox')
        suffix = path.suffix.lower()
        if suffix not in ('.pdf', '.txt', '.md', '.csv', '.json'):
            raise ValueError('Supported formats: PDF, UTF-8 TXT, MD, CSV and JSON')
        maximum = 50*1024*1024 if suffix == '.pdf' else 10*1024*1024
        if path.stat().st_size > maximum:
            raise ValueError('Source exceeds size limit')
        raw = path.read_bytes()
        sid = sha(raw)
        payload = dict(source_id=sid, filename=path.name, origin=origin, role=role, bibliography=bibliography)
        if document_id is not None:
            payload['document_id'] = document_id
        def action(db, state):
            if sid in state['sources']:
                previous = state['sources'][sid]
                if any(previous[k] != payload[k] for k in ('origin', 'role', 'bibliography')):
                    raise ValueError('Identical source already imported with different metadata; inspect existing source')
                if document_id is not None and previous['document_id'] != document_id:
                    raise ValueError('These exact bytes already belong to another document_id')
                self.verify_source(previous)
                return self.source_summary(previous)
            earlier = [src for src in state['sources'].values() if src['document_id'] == document_id]
            if document_id is not None and not earlier:
                raise ValueError('Unknown document_id; omit it to create a new logical document')
            if suffix == '.pdf':
                reader = PdfReader(io.BytesIO(raw))
                if reader.is_encrypted or len(reader.pages) > 1000:
                    raise ValueError('Encrypted PDFs and PDFs over 1000 pages are unsupported')
                pages = [{'page_index': i, 'page_label': reader.page_labels[i], 'text': page.extract_text() or ''}
                         for i, page in enumerate(reader.pages)]
            else:
                try:
                    text = raw.decode('utf-8-sig')
                except UnicodeDecodeError as exc:
                    raise ValueError('Text input must be UTF-8') from exc
                if suffix == '.json':
                    json.loads(text)  # validate, but preserve the original whitespace and offsets
                pages = [{'page_index': 0, 'page_label': 'text', 'text': text}]
            if sum(len(p['text']) for p in pages) > 20_000_000:
                raise ValueError('Extracted text exceeds 20 million character limit')
            dest = self.root / 'sources' / sid
            dest.mkdir(exist_ok=True)
            original = dest / ('original' + suffix)
            original.write_bytes(raw)
            source = {**payload, 'file': str(original.relative_to(self.root)).replace('\\', '/'),
                      'sha256': sid, 'imported_at': now(), 'pages': pages,
                      'text_sha256': sha(dump(pages).encode()),
                      'status': 'ready' if pages and all(p['text'].strip() for p in pages) else 'needs_text_review'}
            source.update(document_id=document_id or 'doc-'+uuid.uuid4().hex,
                          source_version=max((src['source_version'] for src in earlier), default=0)+1,
                          text_revision_id='text-'+sha(dump([sid, source['text_sha256']]).encode()),
                          extraction={'engine':'pypdf' if suffix=='.pdf' else 'utf-8-sig',
                                      'version':version('pypdf') if suffix=='.pdf' else '1'})
            chunk_set = self._create_chunk_set(db, source, active=True)
            source['active_chunk_set_id'] = chunk_set['chunk_set_id']
            db.execute('INSERT INTO documents VALUES(?,?)', (sid, dump(source)))
            return self.source_summary(source)
        return self.mutate('import_document', payload, expected_revision, key, action)

    @staticmethod
    def source_summary(source):
        return {k: v for k, v in source.items() if k != 'pages'} | {'page_count': len(source['pages'])}

    def verify_source(self, source):
        path = (self.root / source['file']).resolve()
        if not path.is_relative_to((self.root / 'sources').resolve()):
            raise ValueError('Invalid stored source path')
        if not path.is_file() or sha(path.read_bytes()) != source['sha256']:
            raise ValueError('Original source hash mismatch: ' + source['filename'])
        if sha(dump(source['pages']).encode()) != source['text_sha256']:
            raise ValueError('Extracted text integrity mismatch')
        return path

    def page(self, source_id, page_index, state=None):
        state = state if state is not None else self.read()
        source = state['sources'].get(source_id)
        if not source:
            raise ValueError('Unknown source_id')
        self.verify_source(source)
        if type(page_index) != int or not 0 <= page_index < len(source['pages']):
            raise ValueError('page_index must identify an existing zero-based page')
        page = source['pages'][page_index]
        return {**page, **{k:source[k] for k in ('document_id','source_version','text_revision_id')}, 'source_id': source_id, 'origin': source['origin'], 'role': source['role'],
                'title': source['bibliography']['title'], 'offset_unit': 'Python Unicode characters; start inclusive, end exclusive'}

    def citation(self, citation, state):
        citation = Citation.model_validate(citation).model_dump()
        require_text(citation['quote'], 'citation quote', 100000)
        page = self.page(citation['source_id'], citation['page_index'], state)
        start, end = citation['start'], citation['end']
        if end <= start or end > len(page['text']) or page['text'][start:end] != citation['quote']:
            raise ValueError('Citation quote does not match the exact source page span')
        return citation

    def search(self, query, roles=None, source_ids=None, limit=8, mode="hybrid", rerank=True,
               candidate_limit=50, min_rerank_score=None, min_document_score=0):
        require_text(query, 'query', 2000)
        if not 1 <= limit <= 30:
            raise ValueError('limit must be 1..30')
        if mode not in ('lexical', 'semantic', 'hybrid'):
            raise ValueError('mode must be lexical, semantic or hybrid')
        if type(rerank) is not bool or type(candidate_limit) is not int or not 30 <= candidate_limit <= 200:
            raise ValueError('rerank must be boolean; candidate_limit must be 30..200')
        if min_rerank_score is not None and (type(min_rerank_score) not in (float, int)
                or not math.isfinite(min_rerank_score) or not 0 <= min_rerank_score <= 1):
            raise ValueError('min_rerank_score must be null or a finite number in 0..1')
        if min_rerank_score is not None and (not rerank or mode == 'lexical'):
            raise ValueError('A rerank score threshold requires semantic/hybrid with rerank=true')
        if (type(min_document_score) not in (float, int) or not math.isfinite(min_document_score)
                or not 0 <= min_document_score <= 1):
            raise ValueError('min_document_score must be a finite number in 0..1')
        state = self.read()
        if source_ids and set(source_ids)-set(state['sources']):
            raise ValueError('Unknown source_id in filter')
        latest = {}
        for src in state['sources'].values():
            latest[src['document_id']] = max(latest.get(src['document_id'], 0), src['source_version'])
        selected = {sid: src for sid, src in state['sources'].items()
                    if (not roles or src['role'] in roles) and (sid in source_ids if source_ids else src['source_version']==latest[src['document_id']])}
        for source in selected.values():
            self.verify_source(source)
        with self.connect() as db:
            rows = [dict(r) for r in db.execute("SELECT c.*, m.chunk_set_id FROM chunks c JOIN chunk_metadata m ON m.chunk_id=c.id JOIN chunk_sets s ON s.id=m.chunk_set_id WHERE s.active=1 AND m.status='active'") if r['source_id'] in selected]
        for row in rows:
            source = selected[row['source_id']]
            page = source['pages'][row['page_index']]
            if page['text'][row['start']:row['end']] != row['text']:
                raise ValueError('Chunk integrity mismatch; reimport from verified source')
            row.update({k:source[k] for k in ('document_id','source_version','text_revision_id')})
            row.update(title=source['bibliography']['title'], origin=source['origin'], role=source['role'], page_label=page['page_label'])
        lexical = rank(rows, query, len(rows) or 1, remove_overlap=False) if mode != 'semantic' else []
        reranked_count = 0
        rejected_count = 0
        document_scores = {}
        if mode == 'lexical':
            hits = deduplicate(lexical, limit)
        else:
            with self.connect() as db:
                scores = semantic.cosine_scores(db, rows, query)
            ordered = sorted(zip(rows, scores), key=lambda item: (-item[1], item[0]['id']))
            lexical_ranks = {r['id']: (i+1, r) for i, r in enumerate(lexical)}
            candidates = []
            for position, (row, score) in enumerate(ordered, 1):
                lr, lexical_hit = lexical_ranks.get(row['id'], (None, {}))
                combined = score if mode == 'semantic' else 1/(60+position) + (1/(60+lr) if lr else 0)
                candidates.append({**row, 'score': round(combined, 8), 'semantic_score': round(score, 6),
                                   'lexical_score': lexical_hit.get('score', 0), 'matched_terms': lexical_hit.get('matched_terms', [])})
            candidates.sort(key=lambda row: (-row['score'], row['id']))
            if rerank:
                candidates = reranking.rerank(candidates[:candidate_limit], query,
                    {sid: src['pages'][0]['text'] for sid, src in selected.items()})
                reranked_count = len(candidates)
                document_scores = {c['source_id']: c['document_score'] for c in candidates}
                kept = [c for c in candidates if c['document_score'] >= min_document_score
                        and (min_rerank_score is None or c['rerank_score'] >= min_rerank_score)]
                rejected_count = len(candidates)-len(kept)
                candidates = kept
            hits = deduplicate(candidates, limit)
        for hit in hits:
            hit['citation'] = {k: hit[k] for k in ('source_id', 'page_index', 'start', 'end')}
            hit['citation'].update(quote=hit['text'], relation='context')
        return dict(query=query, mode=mode,
                    method={'lexical': 'BM25 with Unicode words and Thai 2/3-grams',
                            'semantic': 'Local multilingual E5 embeddings; exact cosine similarity',
                            'hybrid': 'BM25 + multilingual E5 cosine; reciprocal rank fusion k=60'}[mode]
                           + ('; BGE pairwise reranking with first-page relevance diagnostics' if rerank and mode != 'lexical' else ''),
                    embedding_model=semantic.model_status() if mode != 'lexical' else None,
                    reranking={'enabled': rerank and mode != 'lexical',
                               'model': reranking.status() if rerank and mode != 'lexical' else None,
                               'candidate_limit': candidate_limit, 'candidates_scored': reranked_count,
                               'min_score': min_rerank_score, 'rejected_candidates': rejected_count,
                               'document_gate': {'enabled': rerank and mode != 'lexical' and min_document_score > 0,
                                                 'min_score': min_document_score,
                                                 'basis': 'original extracted first page; max score across token windows',
                                                 'scores_by_source': document_scores},
                               'score_meaning': 'Sigmoid of pairwise ranking logit; not calibrated answer confidence'},
                    corpus_sources=len(selected), corpus_chunks=len(rows), hits=hits,
                    status='evidence_retrieved' if hits else 'insufficient_retrieved_evidence',
                    limitation='Candidates are not verified support; unrelated questions can return hits. Scores are not calibrated confidence. No score filter is enabled by default: first-page thresholds produced false negatives in testing. Inspect original evidence. No completeness or novelty claim.')

    @staticmethod
    def context(state):
        return sha(dump([state['project'], sorted(state['sources'])]).encode())

    def artifact_issues(self, artifact, state, visited=None):
        visited = set() if visited is None else set(visited)
        if artifact['id'] in visited:
            return ['Cyclic artifact dependency']
        visited.add(artifact['id'])
        issues = []
        if artifact['context'] != self.context(state):
            issues.append('Evidence corpus changed; revise using the current sources')
        for block in artifact['blocks']:
            for citation in block['citations']:
                try:
                    self.citation(citation, state)
                except (ValueError, OSError) as exc:
                    issues.append(str(exc))
                if any(span['source_id']==citation['source_id'] and span['page_index']==citation['page_index']
                       and span['start']<citation['end'] and span['end']>citation['start'] for span in state.get('disabled_spans', [])):
                    issues.append('Cited evidence overlaps an excluded or needs_review chunk; inspect evidence and revise/review the artifact')
        for ref in artifact['dependencies']:
            current = state['artifacts'].get(ref['id'])
            if not current or current['version'] != ref['version']:
                issues.append('Dependency revised or missing: ' + ref['id'])
            elif current['status'] in ('rejected', 'unresolved') or self.artifact_issues(current, state, visited):
                issues.append('Dependency rejected, unresolved or stale: ' + ref['id'])
        return list(dict.fromkeys(issues))

    def artifact_view(self, artifact, state):
        issues = self.artifact_issues(artifact, state)
        return {**artifact, 'effective_status': 'needs_review' if issues else artifact['status'], 'issues': issues}

    def save_artifact(self, stage, title, blocks, limitations, dependency_ids, expected_revision, key, artifact_id=None):
        if stage not in STAGES:
            raise ValueError('Unknown research stage')
        require_text(title, 'title', 1000)
        blocks = [Block.model_validate(b).model_dump() for b in blocks]
        if not 1 <= len(blocks) <= 100:
            raise ValueError('Use 1..100 evidence blocks')
        required = set(STAGES[stage]['sections'])
        if required - {b['section'] for b in blocks}:
            raise ValueError('Missing sections: ' + ', '.join(sorted(required-{b['section'] for b in blocks})))
        for limitation in limitations:
            require_text(limitation, 'limitation')
        payload = dict(stage=stage, title=title, blocks=blocks, limitations=limitations,
                       dependency_ids=dependency_ids, artifact_id=artifact_id)
        def action(db, state):
            if not state['project']:
                raise ValueError('Start the project with the researcher-supplied topic and goal first')
            previous = state['artifacts'].get(artifact_id) if artifact_id else None
            if artifact_id and not previous:
                raise ValueError('Unknown artifact_id')
            if previous and previous['stage'] != stage:
                raise ValueError('A revision must retain its artifact stage')
            if len(set(dependency_ids)) != len(dependency_ids):
                raise ValueError('Duplicate dependencies')
            references = []
            def reaches_self(dependency, seen):
                if dependency['id'] == artifact_id:
                    return True
                if dependency['id'] in seen:
                    return False
                return any(reaches_self(state['artifacts'][ref['id']], seen | {dependency['id']})
                           for ref in dependency['dependencies'])
            for identifier in dependency_ids:
                dependency = state['artifacts'].get(identifier)
                if not dependency:
                    raise ValueError('Unknown dependency')
                if reaches_self(dependency, set()):
                    raise ValueError('Cyclic artifact dependency')
                if dependency['status'] in ('rejected', 'unresolved') or self.artifact_issues(dependency, state):
                    raise ValueError('Revise rejected, unresolved or stale dependencies before using them')
                references.append({'id': identifier, 'version': dependency['version']})
            for block in blocks:
                require_text(block['text'], 'block text')
                if block['basis'] in ('evidence', 'analysis_result') and not block['citations']:
                    raise ValueError('Evidence and analysis_result blocks require citations')
                for citation in block['citations']:
                    self.citation(citation, state)
                if block['basis'] == 'analysis_result' and not any(
                    state['sources'][c['source_id']]['role'] in ('data', 'results') for c in block['citations']
                ):
                    raise ValueError('analysis_result must cite actual project data or results')
            if stage == 'literature_note':
                cited = {c['source_id'] for block in blocks for c in block['citations']}
                if len(cited) != 1 or state['sources'][next(iter(cited))]['role'] != 'literature':
                    raise ValueError('A literature note must cite exactly one literature source')
            identifier = artifact_id or uuid.uuid4().hex
            if previous:
                db.execute('INSERT INTO versions VALUES(?,?,?)', (identifier, previous['version'], dump(previous)))
            artifact = dict(id=identifier, version=previous['version']+1 if previous else 1,
                            stage=stage, title=title, blocks=blocks, limitations=limitations,
                            dependencies=references, context=self.context(state),
                            status='draft', review=None, created_at=previous['created_at'] if previous else now(), updated_at=now())
            db.execute('INSERT OR REPLACE INTO artifacts VALUES(?,?)', (identifier, dump(artifact)))
            return artifact
        return self.mutate('save_artifact', payload, expected_revision, key, action)

    def review(self, artifact_id, verdict, reviewer, rationale, expected_revision, key):
        """Called exclusively by the separate review UI; never exposed as an MCP tool."""
        if verdict not in ('accepted', 'rejected', 'unresolved'):
            raise ValueError('Invalid review verdict')
        require_text(reviewer, 'reviewer', 300)
        require_text(rationale, 'rationale', 5000)
        payload = dict(artifact_id=artifact_id, verdict=verdict, reviewer=reviewer, rationale=rationale)
        def action(db, state):
            artifact = state['artifacts'].get(artifact_id)
            if not artifact:
                raise ValueError('Unknown artifact')
            issues = self.artifact_issues(artifact, state)
            if verdict == 'accepted':
                if issues:
                    raise ValueError('; '.join(issues))
                if any(state['artifacts'][ref['id']]['status'] != 'accepted' for ref in artifact['dependencies']):
                    raise ValueError('Review dependencies before accepting this artifact')
                if any(block['basis'] == 'unresolved' for block in artifact['blocks']):
                    raise ValueError('Resolve unresolved blocks before acceptance')
            artifact['status'] = verdict
            artifact['review'] = {**payload, 'time': now(), 'version': artifact['version']}
            db.execute('UPDATE artifacts SET data=? WHERE id=?', (dump(artifact), artifact_id))
            return artifact
        return self.mutate('human_review', payload, expected_revision, key, action, actor='human-review-ui')

    def get_artifact(self, artifact_id, version=None):
        state = self.read()
        artifact = state['artifacts'].get(artifact_id)
        if not artifact:
            raise ValueError('Unknown artifact')
        if version is not None and version != artifact['version']:
            with self.connect() as db:
                row = db.execute('SELECT data FROM versions WHERE artifact_id=? AND version=?', (artifact_id, version)).fetchone()
            if not row:
                raise ValueError('Unknown artifact version')
            return {**json.loads(row['data']), 'historical': True}
        return self.artifact_view(artifact, state)

    def profile_csv(self, source_id):
        source = self.read()['sources'].get(source_id)
        if not source or not source['file'].endswith('.csv') or source['role'] not in ('data', 'results'):
            raise ValueError('An imported CSV with role data or results is required')
        raw = self.verify_source(source).read_text(encoding='utf-8-sig')
        reader = csv.reader(io.StringIO(raw), strict=True)
        headers = next(reader, [])
        if not headers or len(set(headers)) != len(headers) or any(not h.strip() for h in headers):
            raise ValueError('CSV requires unique nonempty column names')
        columns = [[] for _ in headers]
        for row in reader:
            if len(row) != len(headers):
                raise ValueError('CSV rows must have the same number of columns as the header')
            for column, cell in zip(columns, row):
                column.append(cell)
        summary = []
        for header, column in zip(headers, columns):
            values = []
            for cell in column:
                try:
                    number = float(cell)
                except ValueError:
                    continue
                if math.isfinite(number):
                    values.append(number)
            summary.append(dict(column=header, count=len(column), blank=sum(not x.strip() for x in column),
                                numeric_count=len(values), min=min(values) if values else None,
                                max=max(values) if values else None,
                                mean=sum(x/len(values) for x in values) if values else None))
        return dict(source_id=source_id, sha256=source['sha256'], rows=len(columns[0]), columns=summary,
                    method='Descriptive summary of finite numeric cells only; blank means empty or whitespace. Non-numeric and non-finite cells are excluded from numeric summaries. No imputation, inference or causal interpretation.')

    def backup(self):
        dest = self.root / 'backups' / uuid.uuid4().hex
        with self.connect() as db:
            db.execute('BEGIN')
            self.require_no_pending_cleanup(db)
            dest.mkdir()
            with sqlite3.connect(dest / 'research.sqlite') as target:
                db.backup(target)
            sources = [json.loads(r['data']) for r in db.execute('SELECT data FROM documents')]
            for source in sources:
                original = self.verify_source(source)
                target = dest / source['file']
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, target)
            self.manifest(dest)
        return {'directory': str(dest), 'sources': len(sources), 'excludes': ['inbox', 'exports', 'HTTP token']}

    @staticmethod
    def manifest(directory):
        records = {str(p.relative_to(directory)).replace('\\', '/'): sha(p.read_bytes())
                   for p in directory.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        (directory / 'manifest.json').write_text(dump(records)+'\n', encoding='utf-8')
        return records

    @classmethod
    def restore(cls, snapshot, destination):
        source = Path(snapshot).resolve()
        dest = Path(destination).expanduser().resolve()
        if dest.exists():
            raise ValueError('Restore destination must not exist')
        records = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
        if 'research.sqlite' not in records:
            raise ValueError('Backup must include research.sqlite')
        for name, digest in records.items():
            if Path(name).is_absolute() or '..' in Path(name).parts or '\\' in name or ':' in name:
                raise ValueError('Backup manifest paths must be portable relative paths')
            original = (source / name).resolve()
            if not original.is_relative_to(source) or sha(original.read_bytes()) != digest:
                raise ValueError('Backup integrity or path check failed')
        dest.mkdir(parents=True)
        for name in records:
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
        restored = cls(dest)
        for src in restored.read()['sources'].values():
            restored.verify_source(src)
        return {'directory': str(dest), 'revision': restored.read()['revision']}

    def http_token(self):
        path = self.root / '.http-token'
        if not path.exists():
            try:
                with path.open('x', encoding='utf-8') as f:
                    f.write(secrets.token_urlsafe(32))
                path.chmod(0o600)
            except FileExistsError:
                pass
        token = path.read_text(encoding='utf-8').strip()
        if len(token) < 32:
            raise ValueError('HTTP token file must contain at least 32 characters')
        return token
