import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import httpx2
from mcp import Client, ClientSession, StdioServerParameters
from mcp.client.streamable_http import streamable_http_client

from research_rag_mcp.models import STAGES
from research_rag_mcp.store import Store, sha
from support import prepare_files, populate, cite, blocks, save, ROOT

BIND_HOST = os.getenv('RESEARCH_RAG_TEST_BIND_HOST', '127.0.0.1')


class HTTPIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store, self.lengths = prepare_files(self.tmp.name)
        self.token = self.store.http_token()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.url = f'http://127.0.0.1:{self.port}/mcp'
        self.log = tempfile.TemporaryFile(mode='w+t')
        self.process = subprocess.Popen([sys.executable, '-m', 'research_rag_mcp', '--workspace', self.tmp.name,
                                         'serve', '--host', BIND_HOST, '--port', str(self.port)], stdout=self.log, stderr=self.log)
        for _ in range(100):
            if self.process.poll() is not None:
                self.log.seek(0)
                self.fail(self.log.read())
            try:
                reader, writer = await asyncio.open_connection('127.0.0.1', self.port)
                writer.close()
                await writer.wait_closed()
                break
            except OSError:
                await asyncio.sleep(0.1)
        else:
            self.fail('Actual MCP server did not become reachable')

    async def asyncTearDown(self):
        self.process.terminate()
        self.process.wait(timeout=10)
        self.log.close()
        self.tmp.cleanup()

    async def test_real_streamable_http_all_eight_stages_and_resume(self):
        async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+self.token}, timeout=httpx2.Timeout(30, read=300)) as http:
            async with streamable_http_client(self.url, http_client=http) as streams:
                async with ClientSession(*streams, read_timeout_seconds=300) as session:
                    await session.initialize()
                    tools = (await session.list_tools()).tools
                    names = {tool.name for tool in tools}
                    self.assertEqual(len(names), 33)
                    self.assertTrue({s['tool'] for s in STAGES.values()} <= names)
                    self.assertNotIn('review', names)
                    for tool in tools:
                        self.assertIsNotNone(tool.output_schema)
                        if tool.name == 'save_artifact':
                            self.assertNotIn('reviewer', json.dumps(tool.input_schema))
                    async def call(name, **arguments):
                        result = await session.call_tool(name, arguments)
                        self.assertFalse(result.is_error, str(result))
                        return result.structured_content or json.loads(result.content[0].text)
                    await call('start_project', topic='PDF extraction from the real brms article',
                               goal='Verify the eight-stage evidence workflow; no research acceptance implied', unknowns=[],
                               expected_revision=0, idempotency_key='start')
                    source_ids = {}
                    for filename, role, origin, title in [
                        ('brms.pdf', 'literature', 'https://doi.org/10.18637/jss.v080.i01', 'brms article'),
                        ('guidelines.txt', 'journal_guidelines', 'https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals', 'Elsevier policy excerpt'),
                        ('extraction-metrics.csv', 'results', 'Computed from the actual imported brms PDF by pypdf', 'Actual PDF extraction metrics'),
                    ]:
                        current = await call('workspace_status')
                        imported = await call('import_document', filename=filename, role=role, origin=origin,
                                              bibliography={'title': title}, expected_revision=current['revision'], idempotency_key=filename)
                        source_ids[role] = imported['result']['source_id']
                    retrieval = await call('retrieve_evidence', query='Bayesian multilevel Stan', roles=['literature'])
                    self.assertTrue(retrieval['hits'])
                    source_page = await call('read_source_page', source_id=source_ids['literature'], page_index=0)
                    self.assertIn('brms', source_page['text'])
                    summary = await call('summarize_dataset', source_id=source_ids['results'])
                    self.assertEqual(summary['rows'], len(self.lengths))
                    quotation = retrieval['hits'][0]['citation']
                    for stage, spec in STAGES.items():
                        if stage in ('submission', 'literature_note'):
                            continue
                        packet = await call(spec['tool'], query='Bayesian multilevel Stan')
                        self.assertTrue(packet['retrieval']['hits'])
                        self.assertEqual(packet['stage'], stage)
                        current = await call('workspace_status')
                        saved = await call('save_artifact', stage=stage, title='Protocol record: '+stage,
                                           blocks=blocks(stage, quotation), limitations=['Scientific content remains unassessed.'],
                                           dependency_ids=[], expected_revision=current['revision'], idempotency_key=stage)
                        if stage == 'manuscript':
                            manuscript_id = saved['result']['id']
                    checks = await call('prepare_submission', manuscript_id=manuscript_id, guideline_source_id=source_ids['journal_guidelines'])
                    self.assertTrue(checks['blockers'])
                    current = await call('workspace_status')
                    submission = await call('save_artifact', stage='submission', title='Unresolved submission protocol record',
                                            blocks=blocks('submission'), limitations=['No submission performed'],
                                            dependency_ids=[manuscript_id], expected_revision=current['revision'], idempotency_key='submission')
                    self.assertEqual(submission['result']['status'], 'draft')
                    bad = await session.call_tool('save_artifact', dict(stage='question', title='Rejected malformed evidence',
                        blocks=[dict(b, basis='evidence', citations=[]) for b in blocks('question')], limitations=[], dependency_ids=[],
                        expected_revision=submission['revision'], idempotency_key='bad'))
                    self.assertTrue(bad.is_error)
                    self.assertEqual((await call('workspace_status'))['revision'], submission['revision'])
                    exported = await call('export_manuscript', manuscript_id=manuscript_id, expected_revision=submission['revision'])
                    self.assertTrue((Path(exported['directory'])/'manuscript.md').exists())
                    backup = await call('backup_workspace')
                    self.assertTrue((Path(backup['directory'])/'manifest.json').exists())
            # Reconnect across a fresh actual HTTP session and explicitly initialize again.
            async with streamable_http_client(self.url, http_client=http) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    resumed = await session.call_tool('read_artifact', {'artifact_id': manuscript_id})
                    self.assertFalse(resumed.is_error)
                    self.assertEqual(resumed.structured_content['id'], manuscript_id)

    async def test_semantic_and_chunk_tools_over_actual_http(self):
        async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+self.token}, timeout=60) as http:
            async with streamable_http_client(self.url, http_client=http) as streams:
                async with ClientSession(*streams, read_timeout_seconds=60) as session:
                    await session.initialize()
                    async def call(name, **arguments):
                        result=await session.call_tool(name,arguments)
                        self.assertFalse(result.is_error,str(result))
                        return result.structured_content
                    async def mutate(name, **arguments):
                        state=await call('workspace_status')
                        return await call(name,expected_revision=state['revision'],idempotency_key=__import__('uuid').uuid4().hex,**arguments)
                    imported=await mutate('import_document',filename='brms.pdf',role='literature',
                        origin='https://doi.org/10.18637/jss.v080.i01',bibliography={'title':'brms: An R Package for Bayesian Multilevel Models Using Stan'})
                    sid=imported['result']['source_id']
                    docs=await call('list_documents')
                    self.assertEqual(docs['documents'][0]['document_id'],imported['result']['document_id'])
                    index=await call('search_index_status')
                    self.assertTrue(index['ready'])
                    self.assertEqual(index['model']['provider'],'CPUExecutionProvider')
                    for mode in ('semantic','hybrid','lexical'):
                        result=await call('retrieve_evidence',query='Bayesian multilevel',mode=mode)
                        self.assertTrue(result['hits'])
                        self.assertEqual(result['mode'],mode)
                    listed=await call('list_chunks',source_id=sid,limit=2)
                    self.assertEqual(len(listed['chunks']),2)
                    cid=listed['chunks'][0]['id']
                    chunk=await call('read_chunk',chunk_id=cid)
                    context=await call('get_chunk_context',chunk_id=cid,before=0,after=1)
                    self.assertEqual(context['chunks'][0]['text'],chunk['text'])
                    qc=await call('inspect_document_chunks',source_id=sid)
                    self.assertFalse(any(p['uncovered_nonblank_spans'] for p in qc['pages']))
                    self.assertEqual((await call('find_evidence_usage',chunk_id=cid))['usages'],[])
                    await mutate('set_chunk_status',chunk_id=cid,status='excluded',reason='HTTP lifecycle exercise')
                    self.assertEqual((await call('read_chunk',chunk_id=cid))['status'],'excluded')
                    await mutate('set_chunk_status',chunk_id=cid,status='active',reason='HTTP lifecycle exercise complete')
                    candidate=await mutate('rechunk_document',source_id=sid,size=1000,overlap=100)
                    await mutate('activate_chunk_set',chunk_set_id=candidate['result']['chunk_set_id'])
                    self.assertEqual((await call('list_chunks',source_id=sid))['chunk_set_id'],candidate['result']['chunk_set_id'])
                    rebuilt=await mutate('rebuild_search_index',source_ids=[sid])
                    self.assertGreater(rebuilt['result']['indexed_chunks'],listed['total'])
                    self.assertEqual((await call('read_chunk',chunk_id=cid))['citation'],chunk['citation'])
                    bad=await session.call_tool('retrieve_evidence',{'query':'Bayesian','mode':'unsupported'})
                    self.assertTrue(bad.is_error)

    async def test_manuscript_identity_across_revisions_review_export_and_restore(self):
        async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+self.token}, timeout=httpx2.Timeout(30, read=300)) as http:
            async with streamable_http_client(self.url, http_client=http) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    async def call(name, **arguments):
                        result = await session.call_tool(name, arguments)
                        self.assertFalse(result.is_error, str(result))
                        return result.structured_content
                    await call('start_project', topic='Manuscript identity protocol check with the brms PDF',
                               goal='Verify document identity; scientific content remains unresolved', unknowns=[],
                               expected_revision=0, idempotency_key='identity-project')
                    imported = await call('import_document', filename='brms.pdf', role='literature',
                                          origin='https://doi.org/10.18637/jss.v080.i01',
                                          bibliography={'title': 'brms: An R Package for Bayesian Multilevel Models Using Stan'},
                                          expected_revision=1, idempotency_key='identity-source')
                    evidence = await call('retrieve_evidence', query='Bayesian multilevel Stan')
                    arguments = dict(stage='manuscript', title='Unresolved manuscript identity protocol record',
                                     blocks=blocks('manuscript', evidence['hits'][0]['citation']),
                                     limitations=['Identity verification only; not a completed scientific manuscript.'],
                                     dependency_ids=[], expected_revision=imported['revision'], idempotency_key='identity-first')
                    first = await call('save_artifact', **arguments)
                    identifier = first['result']['id']
                    first_export = await call('export_manuscript', manuscript_id=identifier, expected_revision=first['revision'])
                    original_path = Path(first_export['directory'])/'manuscript.md'
                    original_bytes = original_path.read_bytes()
                    self.assertIn(f'Manuscript ID: {identifier}', original_bytes.decode())
                    self.assertEqual(first_export['manuscript_id'], identifier)
                    self.assertEqual(first_export['manuscript_version'], 1)
                    self.assertEqual(await call('save_artifact', **arguments), first)
                    revised = await call('save_artifact', **{**arguments, 'title': 'Renamed protocol record',
                                         'artifact_id': identifier, 'expected_revision': first['revision'],
                                         'idempotency_key': 'identity-revision'})
                    self.assertEqual(revised['result']['id'], identifier)
                    self.assertEqual(revised['result']['version'], 2)
                    self.assertEqual(revised['result']['status'], 'draft')
                    historical = await call('read_artifact', artifact_id=identifier, version=1)
                    self.assertEqual(historical['id'], identifier)
                    self.assertEqual(historical['title'], arguments['title'])
                    self.assertTrue(historical['historical'])
                    current = await call('workspace_status')
                    self.assertEqual(current['artifacts'][identifier]['version'], 2)
                    second_export = await call('export_manuscript', manuscript_id=identifier, expected_revision=revised['revision'])
                    self.assertEqual(second_export['manuscript_id'], identifier)
                    self.assertEqual(second_export['manuscript_version'], 2)
                    folder = Path(second_export['directory'])
                    self.assertIn(f'Manuscript ID: {identifier}', (folder/'manuscript.md').read_text())
                    self.assertIn('artifact version 2;', (folder/'manuscript.md').read_text())
                    package = json.loads((folder/'evidence.json').read_text())
                    self.assertEqual((package['manuscript']['id'], package['manuscript']['version']), (identifier, 2))
                    for filename, digest in json.loads((folder/'manifest.json').read_text()).items():
                        self.assertEqual(sha((folder/filename).read_bytes()), digest)
                    self.assertEqual(original_path.read_bytes(), original_bytes)
                    proc = subprocess.Popen([sys.executable, '-m', 'research_rag_mcp', '--workspace', self.tmp.name,
                                             'review', '--host', BIND_HOST], stdout=subprocess.PIPE, text=True)
                    try:
                        url = proc.stdout.readline().strip()
                        async with httpx2.AsyncClient() as review_http:
                            page = await review_http.get(url)
                        self.assertEqual(page.status_code, 200)
                        self.assertIn(f'รหัสต้นฉบับ: {identifier}', page.text)
                    finally:
                        proc.terminate()
                        proc.wait(timeout=10)
                        proc.stdout.close()
                    other = await call('save_artifact', **{**arguments, 'expected_revision': revised['revision'],
                                       'idempotency_key': 'identity-another'})
                    self.assertNotEqual(other['result']['id'], identifier)
                    backup = await call('backup_workspace')
                    destination = Path(self.tmp.name)/'restored'
                    Store.restore(backup['directory'], destination)
                    restored = Store(destination)
                    self.assertEqual(restored.get_artifact(identifier)['version'], 2)
                    self.assertEqual(restored.get_artifact(identifier, 1)['id'], identifier)

    async def test_http_authentication_origin_and_host(self):
        async with httpx2.AsyncClient() as http:
            response = await http.post(self.url, json={})
            self.assertEqual(response.status_code, 401)
            response = await http.post(self.url, headers={'Authorization': 'Bearer wrong'}, json={})
            self.assertEqual(response.status_code, 401)
            auth = {'Authorization': 'Bearer '+self.token}
            response = await http.post(self.url, headers={**auth, 'Origin': 'https://foreign.example'}, json={})
            self.assertEqual(response.status_code, 403)
            response = await http.post(self.url, headers={**auth, 'Host': 'foreign.example'}, json={})
            self.assertIn(response.status_code, (403, 421))

    @unittest.skipUnless(os.getenv('RESEARCH_RAG_LIVE_TESTS') == '1', 'Live Crossref is opt-in')
    async def test_live_crossref_over_real_mcp(self):
        async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+self.token}, timeout=httpx2.Timeout(30, read=300)) as http:
            async with streamable_http_client(self.url, http_client=http) as streams:
                async with ClientSession(*streams, read_timeout_seconds=40) as session:
                    await session.initialize()
                    args = dict(query='brms An R Package for Bayesian Multilevel Models Using Stan', limit=5,
                                year_from=2017, year_to=2017, expected_revision=0, idempotency_key='crossref')
                    result = await session.call_tool('search_literature', args)
                    self.assertFalse(result.is_error, str(result))
                    record = result.structured_content['result']
                    self.assertIn('10.18637/jss.v080.i01', [x['doi'].lower() for x in record['records']])
                    self.assertFalse(record['records'][0]['full_text_read'])
                    retry = await session.call_tool('search_literature', args)
                    self.assertEqual(retry.structured_content, result.structured_content)
                    self.assertEqual(len(self.store.read()['searches']), 1)


class HumanReviewIntegration(unittest.TestCase):
    def test_actual_review_and_reviewed_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, sources, lengths = populate(tmp)
            reference = cite(store, sources['literature'], 'brms')
            actual_result = cite(store, sources['results'])
            text = {
                'title': ('PDF text extraction measurements', 'researcher_input', []),
                'abstract': (f'We measured text extraction from a supplied PDF with {len(lengths)} pages.', 'analysis_result', [actual_result]),
                'introduction': ('The supplied article documents brms.', 'evidence', [reference]),
                'methods': ('The integration test counted extracted characters per physical PDF page using pypdf.', 'researcher_input', []),
                'results': (f'The source contains {len(lengths)} physical pages; exact page lengths are recorded in the CSV.', 'analysis_result', [actual_result]),
                'discussion': ('Character counts do not establish reading-order or semantic extraction accuracy.', 'proposal', []),
                'conclusion': ('Inspect original pages before interpreting extracted text.', 'proposal', []),
            }
            manuscript = save(store, 'manuscript', [dict(section=s, text=t, basis=b, citations=c) for s, (t,b,c) in text.items()])
            proc = subprocess.Popen([sys.executable, '-m', 'research_rag_mcp', '--workspace', tmp, 'review', '--host', BIND_HOST], stdout=subprocess.PIPE, text=True)
            try:
                url = proc.stdout.readline().strip()
                self.assertTrue(url.startswith('http://127.0.0.1:'))
                parsed = urllib.parse.urlparse(url)
                base = f'{parsed.scheme}://{parsed.netloc}'
                token = urllib.parse.parse_qs(parsed.query)['token'][0]
                with urllib.request.urlopen(url, timeout=10) as response:
                    page = response.read().decode()
                self.assertIn('brms', page)
                self.assertIn('ตรวจหลักฐาน', page)
                def review(artifact_id, origin=base, revision=None):
                    fields = dict(token=token, artifact_id=artifact_id,
                                  revision=store.read()['revision'] if revision is None else revision,
                                  verdict='accepted', reviewer='Protocol test operator; not a scientific reviewer',
                                  rationale='Exercise human-UI protocol and export state; not publication endorsement.')
                    request = urllib.request.Request(base+'/review', data=urllib.parse.urlencode(fields).encode(), headers={'Origin': origin})
                    with urllib.request.urlopen(request, timeout=10) as response:
                        return response.read().decode()
                for origin in ('https://foreign.example', 'null'):
                    with self.assertRaises(urllib.error.HTTPError) as cm:
                        review(manuscript['id'], origin)
                    self.assertEqual(cm.exception.code, 403)
                review(manuscript['id'])
                self.assertEqual(store.get_artifact(manuscript['id'])['effective_status'], 'accepted')
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    review(manuscript['id'], revision=0)
                self.assertEqual(cm.exception.code, 409)
                guideline = cite(store, sources['journal_guidelines'])
                submission_blocks = [dict(section=s, text='Protocol exercise only; no journal submission or complete policy assessment.',
                                           basis='proposal', citations=[guideline]) for s in STAGES['submission']['sections']]
                submission = save(store, 'submission', submission_blocks, [manuscript['id']])
                review(submission['id'])
                from research_rag_mcp.workflow import export_manuscript
                exported = export_manuscript(store, manuscript['id'], 'reviewed', store.read()['revision'], submission['id'], sources['journal_guidelines'])
                self.assertEqual(len(exported['files']), 5)
                for filename, digest in json.loads((Path(exported['directory'])/'manifest.json').read_text()).items():
                    self.assertEqual(sha((Path(exported['directory'])/filename).read_bytes()), digest)
                original = base+'/source?'+urllib.parse.urlencode({'token': token, 'id': sources['literature']})
                with urllib.request.urlopen(original, timeout=10) as response:
                    self.assertEqual(sha(response.read()), sources['literature'])
                changed = save(store, 'manuscript', artifact_id=manuscript['id'])
                self.assertEqual(changed['status'], 'draft')
                self.assertEqual(store.get_artifact(submission['id'])['effective_status'], 'needs_review')
            finally:
                proc.terminate()
                proc.wait(timeout=10)
                proc.stdout.close()


class StdioIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_same_server_direct_stdio(self):
        with tempfile.TemporaryDirectory() as tmp:
            params = StdioServerParameters(command=sys.executable, args=['-m', 'research_rag_mcp', '--workspace', tmp, 'serve', '--transport', 'stdio'])
            async with Client(params) as client:
                names = {t.name for t in (await client.list_tools()).tools}
                self.assertIn('prepare_submission', names)
                result = await client.call_tool('workspace_status', {})
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content['revision'], 0)
