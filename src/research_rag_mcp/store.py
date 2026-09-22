"""Transactional evidence, versioned artifacts and separate human decisions."""
import csv
import hashlib
import io
import json
import math
import shutil
import os
import copy
import threading
import uuid
from importlib.metadata import version
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .models import STAGES, Bibliography, Block, Citation
from .retrieval import chunks, rank, deduplicate
from .persistence import Journal
from .backend import RetrievalIndex
from .documents import DocumentManagement
from .cleanup import WorkspaceCleanup
from .downloads import DownloadManagement


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def require_text(value, name, maximum=30000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'{name} requires nonempty text of at most {maximum} characters')


class Store(DocumentManagement, WorkspaceCleanup, DownloadManagement):
    def __init__(self, root, *, collection=None):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        for name in ('inbox', 'sources', 'exports', 'backups'):
            (self.root / name).mkdir(exist_ok=True)
        self.journal = Journal(self.root)
        self.index = RetrievalIndex(collection=collection)
        self._job_owner = threading.local()

    def raw_state(self):
        return self.journal.read()

    @staticmethod
    def state(raw):
        result = {k: raw[k] for k in ('revision','project','sources','artifacts','searches','pending_cleanup','pending_job')}
        result['disabled_spans'] = [row for row in raw['chunks'].values()
            if row['status'] != 'active' and raw['chunk_sets'][row['chunk_set_id']]['active']]
        return result

    def read(self):
        return self.state(self.raw_state())

    @contextmanager
    def snapshot(self):
        with self.journal.lock():
            raw = self.raw_state()
            self.require_no_pending_cleanup(raw)
            yield self.state(raw)

    @staticmethod
    def require_no_pending_cleanup(raw):
        if raw['pending_cleanup']:
            raise ValueError('Pending cleanup must be resumed with its exact original arguments')

    def mutate(self, operation, payload, expected_revision, key, action, actor='mcp-client'):
        require_text(key, 'idempotency_key', 200)
        fingerprint = sha(dump([operation, payload, actor]).encode())
        with self.journal.lock():
            raw = self.raw_state()
            self.require_no_pending_cleanup(raw)
            previous = raw['requests'].get(key)
            if previous:
                if previous['response'] is None:
                    raise ValueError('Idempotency key retired by cleanup; use a new key')
                if previous['fingerprint'] != fingerprint:
                    raise ValueError('Idempotency key already used with different input')
                return previous['response']
            if raw['pending_job'] and raw['pending_job']['idempotency_key'] not in (key,getattr(self._job_owner,'key',None)):
                raise ValueError('A durable ingestion job is in progress; read job_status before writing')
            state = self.state(raw)
            if expected_revision != state['revision']:
                raise ValueError('Stale revision; read workspace_status and reconsider')
            result = action(raw, state)
            revision = raw['revision'] = state['revision'] + 1
            response = {'revision': revision, 'result': result}
            raw['events'].append(dict(time=now(),operation=operation,actor=actor,revision=revision,data=payload))
            raw['requests'][key] = {'fingerprint':fingerprint,'response':response}
            self.journal.commit(raw)
            return response

    def start_project(self, topic, goal, unknowns, expected_revision, key):
        require_text(topic, 'topic', 2000)
        require_text(goal, 'goal', 5000)
        for value in unknowns:
            require_text(value, 'unknown')
        project = dict(topic=topic, goal=goal, unknowns=unknowns)
        def action(db, state):
            if state['project']:
                raise ValueError('Project already exists; use create_workspace for a separate project, or refine this project in a versioned question artifact')
            db['project'] = project
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
                import pymupdf
                with pymupdf.open(stream=raw,filetype='pdf') as reader:
                    if reader.is_encrypted or len(reader)>1000:
                        raise ValueError('Encrypted PDFs and PDFs over 1000 pages are unsupported')
                    pages=[{'page_index':i,'page_label':str(i+1),'text':page.get_text() or ''} for i,page in enumerate(reader)]
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
                          extraction={'engine':'pymupdf' if suffix=='.pdf' else 'utf-8-sig',
                                      'version':version('PyMuPDF') if suffix=='.pdf' else '1'})
            receipt = next((r['response']['result'] for r in reversed(list(db['requests'].values()))
                if r.get('response') and isinstance(r['response'].get('result'), dict)
                and r['response']['result'].get('status') == 'downloaded_to_inbox'
                and r['response']['result'].get('sha256') == sid), None)
            if receipt:
                source['download_provenance'] = receipt
            chunk_set = self._create_chunk_set(db, source, active=True)
            source['active_chunk_set_id'] = chunk_set['chunk_set_id']
            db['sources'][sid] = source
            return self.source_summary(source)
        return self.mutate('import_document', payload, expected_revision, key, action)

    def import_context(self,content,title,origin,role,expected_revision,key,format="md"):
        require_text(content,'content',1000000)
        if format not in ('md','txt','csv','json'): raise ValueError('Unsupported text format')
        filename='context-'+sha(content.encode())+'.'+format
        target=self.root/'inbox'/filename
        if target.exists() and target.read_bytes()!=content.encode('utf-8'):
            raise ValueError('Existing context file integrity mismatch')
        if not target.exists(): target.write_text(content,encoding='utf-8')
        return self.import_document(filename,origin,role,{'title':title},expected_revision,key)

    def import_directory(self,path,bibliography_by_filename,role,expected_revision,key):
        directory=(self.root/'inbox'/path).resolve()
        if not directory.is_dir() or not directory.is_relative_to((self.root/'inbox').resolve()):
            raise ValueError('Supply a relative directory inside inbox')
        files=sorted(p for p in directory.rglob('*') if p.is_file() and p.suffix.lower() in ('.pdf','.txt','.md','.csv','.json'))
        names=[p.relative_to(self.root/'inbox').as_posix() for p in files]
        if set(names)!=set(bibliography_by_filename):
            raise ValueError('Supply verified bibliography for exactly these inbox files: '+dump(names))
        results=[]
        for i,name in enumerate(names):
            child_key=sha((key+':'+name).encode())
            existing=self.raw_state()['requests'].get(child_key)
            if existing and existing['response']:
                result=existing['response']
            else:
                result=self.import_document(name,'inbox:'+name,role,bibliography_by_filename[name],self.read()['revision'],child_key)
            results.append(result)
        return {'revision':self.read()['revision'],'result':{'imported_documents':len(results),'documents':results}}

    @staticmethod
    def source_summary(source):
        return {k: v for k, v in source.items() if k != 'pages'} | {
            'page_count': len(source['pages']), **Store.evidence_kind(source)}

    @staticmethod
    def evidence_kind(source):
        source_format = Path(source['file']).suffix.lower().lstrip('.')
        return {'source_format': source_format,
                'evidence_kind': 'project_note' if source['role'] == 'project_note'
                    else 'pdf_source' if source_format == 'pdf' else 'text_source'}

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
        return {**page, **self.evidence_kind(source), **{k:source[k] for k in ('document_id','source_version','text_revision_id')}, 'source_id': source_id, 'origin': source['origin'], 'role': source['role'],
                'title': source['bibliography']['title'], 'offset_unit': 'Python Unicode characters; start inclusive, end exclusive'}

    def citation(self, citation, state):
        citation = Citation.model_validate(citation).model_dump()
        require_text(citation['quote'], 'citation quote', 100000)
        page = self.page(citation['source_id'], citation['page_index'], state)
        start, end = citation['start'], citation['end']
        if end <= start or end > len(page['text']) or page['text'][start:end] != citation['quote']:
            raise ValueError('Citation quote does not match the exact source page span')
        return citation

    def search(self, query, roles=None, source_ids=None, limit=8, mode="hybrid"):
        require_text(query, 'query', 2000)
        if type(limit) != int or not 1 <= limit <= 30:
            raise ValueError('limit must be 1..30')
        if mode not in ('lexical','semantic','hybrid'):
            raise ValueError('mode must be lexical, semantic or hybrid')
        raw = self.raw_state()
        self.require_no_pending_cleanup(raw)
        if source_ids and set(source_ids)-set(raw['sources']):
            raise ValueError('Unknown source_id in filter')
        latest = {}
        for src in raw['sources'].values():
            latest[src['document_id']] = max(latest.get(src['document_id'],0),src['source_version'])
        selected = {sid:src for sid,src in raw['sources'].items()
                    if (not roles or src['role'] in roles) and
                    (sid in source_ids if source_ids else src['source_version']==latest[src['document_id']])}
        sets = {src['active_chunk_set_id'] for src in selected.values()}
        rows = [row for row in raw['chunks'].values() if row['chunk_set_id'] in sets and row['status']=='active']
        if mode!='lexical' and rows and (raw['index_generation']!=self.index.fingerprint or any(r.get('embedding_fingerprint')!=self.index.fingerprint for r in rows)):
            raise ValueError('Embedding index is not ready for the configured model; rebuild_search_index')
        result = self.index.search(query,rows,selected,mode,limit)
        hits = []
        verified_sources = set()
        for row in result['hits']:
            source=selected[row['source_id']]
            if row['source_id'] not in verified_sources:
                self.verify_source(source); verified_sources.add(row['source_id'])
            page=source['pages'][row['page_index']]
            if page['text'][row['start']:row['end']]!=row['text']:
                raise ValueError('Chunk integrity mismatch')
            hit={**row,**self.evidence_kind(source),**{k:source[k] for k in ('document_id','source_version','text_revision_id','origin','role')},
                 'title':source['bibliography']['title'],'page_label':page['page_label']}
            hit['citation']={k:hit[k] for k in ('source_id','page_index','start','end')}
            hit['citation'].update(quote=hit['text'],relation='context')
            hits.append(hit)
        return dict(query=query,mode=mode,method=result['method'],timings=result['timings'],
                    embedding_model=self.index.model_status() if mode!='lexical' else None,
                    reranking={'enabled':False,'reason':'Selected upstream architecture uses BM25 + semantic RRF; no BGE'},
                    corpus_sources=len(selected),corpus_chunks=len(rows),hits=hits,
                    revision=raw['revision'],status='evidence_retrieved' if hits else 'insufficient_retrieved_evidence',
                    limitation='Retrieved candidates are not verified scientific support. Inspect source pages; scores are not confidence.')

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
                db['versions'].setdefault(identifier, {})[str(previous['version'])] = copy.deepcopy(previous)
            artifact = dict(id=identifier, version=previous['version']+1 if previous else 1,
                            stage=stage, title=title, blocks=blocks, limitations=limitations,
                            dependencies=references, context=self.context(state),
                            status='draft', review=None, created_at=previous['created_at'] if previous else now(), updated_at=now())
            db['artifacts'][identifier] = artifact
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
            db['artifacts'][artifact_id] = artifact
            return artifact
        return self.mutate('human_review', payload, expected_revision, key, action, actor='human-review-ui')

    def get_artifact(self, artifact_id, version=None):
        state = self.read()
        artifact = state['artifacts'].get(artifact_id)
        if not artifact:
            raise ValueError('Unknown artifact')
        if version is not None and version != artifact['version']:
            row = self.raw_state()['versions'].get(artifact_id, {}).get(str(version))
            if not row:
                raise ValueError('Unknown artifact version')
            return {**row, 'historical': True}
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
        with self.journal.lock():
            state = self.raw_state()
            self.require_no_pending_cleanup(state)
            if state['pending_job']:
                raise ValueError('Wait for the ingestion job before taking a backup')
            return self._backup_state(state)

    def _backup_state(self, state):
        from .persistence import atomic_json
        dest=self.root/'backups'/uuid.uuid4().hex
        dest.mkdir()
        # Include actual vectors so restore requires no re-embedding or model drift.
        points=self.index.export_points(list(state['chunks']))
        atomic_json(dest/'qdrant-points.json',points)
        atomic_json(dest/'workspace.json',{'state':state,'sha256':sha(__import__('research_rag_mcp.persistence',fromlist=['encode']).encode(state).encode())})
        for source in state['sources'].values():
            original=self.verify_source(source)
            target=dest/source['file']; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(original,target)
        self.manifest(dest)
        return {'directory':str(dest),'sources':len(state['sources']),'vectors':len(points),
                'excludes':['inbox','exports'],'format':'revisioned-json-and-qdrant-vectors-v1'}

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
        if not {'workspace.json','qdrant-points.json'} <= set(records):
            raise ValueError('Backup must include workspace.json and qdrant-points.json')
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
        restored.index.restore_points(json.loads((dest/'qdrant-points.json').read_text()))
        for src in restored.read()['sources'].values():
            restored.verify_source(src)
        return {'directory': str(dest), 'revision': restored.read()['revision']}
