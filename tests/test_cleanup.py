"""Cleanup through the real Streamable HTTP server, using real source files."""
import unittest
from contextlib import asynccontextmanager

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

import test_http
from research_rag_mcp.store import Store
from support import blocks


class CleanupHTTPIntegration(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_http.HTTPIntegration.asyncSetUp
    asyncTearDown = test_http.HTTPIntegration.asyncTearDown

    @asynccontextmanager
    async def client(self):
        async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+self.token},
                                     timeout=httpx2.Timeout(30, read=300)) as http:
            async with streamable_http_client(self.url, http_client=http) as streams:
                async with ClientSession(*streams, read_timeout_seconds=300) as session:
                    await session.initialize()
                    yield session

    async def call(self, session, name, **arguments):
        result = await session.call_tool(name, arguments)
        self.assertFalse(result.is_error, str(result))
        return result.structured_content

    async def import_source(self, session, pdf=False, key='import'):
        state = await self.call(session, 'workspace_status')
        return await self.call(session, 'import_document', filename='brms.pdf' if pdf else 'guidelines.txt',
            origin='Real integration evidence bundled with this project', role='literature',
            bibliography={'title': 'brms: An R Package for Bayesian Multilevel Models Using Stan' if pdf else 'Elsevier policy excerpt'},
            expected_revision=state['revision'], idempotency_key=key)

    async def cleanup(self, session, scope, key='cleanup'):
        plan = await self.call(session, 'preview_workspace_cleanup', scope=scope)
        return await self.call(session, 'cleanup_workspace', scope=scope,
            plan_hash=plan['plan_hash'], expected_revision=plan['revision'], idempotency_key=key)

    async def test_index_clear_rebuild_restore_and_retry_over_http(self):
        async with self.client() as session:
            names = {t.name for t in (await session.list_tools()).tools}
            self.assertTrue({'preview_workspace_cleanup', 'cleanup_workspace'} <= names)
            imported = await self.import_source(session, pdf=True)
            sid = imported['result']['source_id']
            before = await self.call(session, 'workspace_status')
            hits = await self.call(session, 'retrieve_evidence', query='Bayesian multilevel models', mode='semantic', limit=3)
            chunk = hits['hits'][0]
            plan = await self.call(session, 'preview_workspace_cleanup', scope='search_index')
            self.assertEqual(plan['revision'], before['revision'])
            self.assertEqual(plan['delete_counts']['embeddings'], before['search_index']['indexed_chunks'])
            self.assertEqual(plan['delete_counts']['documents'], 0)
            self.assertEqual(list((self.store.root/'backups').iterdir()), [])
            args = dict(scope='search_index', plan_hash=plan['plan_hash'],
                        expected_revision=plan['revision'], idempotency_key='clear-index')
            cleared = await self.call(session, 'cleanup_workspace', **args)
            self.assertEqual(cleared, await self.call(session, 'cleanup_workspace', **args))
            self.assertEqual(len(list((self.store.root/'backups').iterdir())), 1)
            after = await self.call(session, 'workspace_status')
            self.assertEqual(after['sources'], before['sources'])
            self.assertEqual(after['search_index']['indexed_chunks'], 0)
            self.assertEqual(after['search_index']['total_chunks'], before['search_index']['total_chunks'])
            self.assertFalse(after['search_index']['ready'])
            read = await self.call(session, 'read_chunk', chunk_id=chunk['id'])
            self.assertEqual(read['citation'], chunk['citation'])
            missing = await session.call_tool('retrieve_evidence', {'query': 'Bayesian multilevel models', 'mode': 'semantic'})
            self.assertTrue(missing.is_error)
            self.assertIn('rebuild_search_index', str(missing))
            restored_dir = self.store.root/'restored'
            Store.restore(cleared['result']['backup']['directory'], restored_dir)
            restored = Store(restored_dir)
            self.assertEqual(restored.read()['sources'], self.store.read()['sources'])
            self.assertTrue(restored.search_index_status()['ready'])
            rebuilt = await self.call(session, 'rebuild_search_index', expected_revision=after['revision'], idempotency_key='rebuild')
            self.assertGreater(rebuilt['result']['indexed_chunks'], 0)
            recovered = await self.call(session, 'retrieve_evidence', query='Bayesian multilevel models', mode='semantic', limit=3)
            self.assertEqual([h['id'] for h in recovered['hits']], [h['id'] for h in hits['hits']])
            self.assertEqual((await self.call(session, 'read_source_page', source_id=sid, page_index=chunk['page_index']))['text'][chunk['start']:chunk['end']], chunk['text'])
            self.assertEqual(self.store.http_token(), self.token)

    async def test_documents_clear_preserves_originals_and_allows_real_reimport(self):
        async with self.client() as session:
            await self.call(session, 'start_project', topic='Cleanup protocol verification',
                goal='Verify lifecycle operations on the supplied real documents', unknowns=[],
                expected_revision=0, idempotency_key='start')
            imported = await self.import_source(session)
            before = await self.call(session, 'workspace_status')
            original = self.store.root/imported['result']['file']
            original_bytes = original.read_bytes()
            cleared = await self.cleanup(session, 'documents')
            after = await self.call(session, 'workspace_status')
            self.assertEqual(after['sources'], {})
            self.assertEqual(after['search_index']['total_chunks'], 0)
            self.assertEqual(after['project'], before['project'])
            self.assertEqual(original.read_bytes(), original_bytes)
            self.assertEqual((self.store.root/'inbox/guidelines.txt').read_bytes(), original_bytes)
            self.assertEqual(cleared['result']['source_files_retained'], 1)
            # A pre-cleanup import retry must not report a deleted document as present.
            old = await session.call_tool('import_document', dict(filename='guidelines.txt',
                origin='Real integration evidence bundled with this project', role='literature',
                bibliography={'title': 'Elsevier policy excerpt'}, expected_revision=after['revision'], idempotency_key='import'))
            self.assertTrue(old.is_error)
            self.assertIn('retired by cleanup', str(old))
            reimported = await self.import_source(session, key='new-import')
            self.assertEqual(reimported['result']['source_id'], imported['result']['source_id'])
            self.assertNotEqual(reimported['result']['document_id'], imported['result']['document_id'])
            self.assertTrue((await self.call(session, 'search_index_status'))['ready'])

    async def test_workspace_scope_dependency_guard_preview_and_invalid_requests(self):
        async with self.client() as session:
            await self.call(session, 'start_project', topic='Cleanup protocol verification',
                goal='Verify lifecycle operations on the supplied real documents', unknowns=[],
                expected_revision=0, idempotency_key='start')
            imported = await self.import_source(session)
            before = await self.call(session, 'workspace_status')
            plan = await self.call(session, 'preview_workspace_cleanup', scope='documents')
            artifact = await self.call(session, 'save_artifact', stage='question', title='Cleanup protocol record',
                blocks=blocks('question'), limitations=['Protocol test only'], dependency_ids=[],
                expected_revision=before['revision'], idempotency_key='artifact')
            stale = await session.call_tool('cleanup_workspace', dict(scope='documents', plan_hash=plan['plan_hash'],
                expected_revision=plan['revision'], idempotency_key='stale'))
            self.assertTrue(stale.is_error)
            guarded = await self.call(session, 'preview_workspace_cleanup', scope='documents')
            self.assertFalse(guarded['can_execute'])
            self.assertTrue(guarded['blockers'])
            result = await session.call_tool('cleanup_workspace', dict(scope='documents', plan_hash=guarded['plan_hash'],
                expected_revision=guarded['revision'], idempotency_key='blocked'))
            self.assertTrue(result.is_error)
            for scope, digest in [('all', plan['plan_hash']), ('workspace', 'wrong')]:
                result = await session.call_tool('cleanup_workspace', dict(scope=scope, plan_hash=digest,
                    expected_revision=artifact['revision'], idempotency_key='invalid-'+scope))
                self.assertTrue(result.is_error)
            self.assertEqual(list((self.store.root/'backups').iterdir()), [])
            self.assertEqual((await self.call(session, 'workspace_status'))['revision'], artifact['revision'])
            cleared = await self.cleanup(session, 'workspace')
            state = await self.call(session, 'workspace_status')
            self.assertIsNone(state['project'])
            self.assertEqual(state['sources'], {})
            self.assertEqual(state['artifacts'], {})
            self.assertEqual(state['searches'], [])
            self.assertEqual(state['revision'], artifact['revision']+1)
            with self.store.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM versions').fetchone()[0], 0)
                events = db.execute('SELECT operation FROM events').fetchall()
                self.assertEqual([row[0] for row in events], ['cleanup_workspace'])
            Store.restore(cleared['result']['backup']['directory'], self.store.root/'restored')
            restored = Store(self.store.root/'restored')
            self.assertIn(imported['result']['source_id'], restored.read()['sources'])
            self.assertIn(artifact['result']['id'], restored.read()['artifacts'])

    async def test_backup_failure_leaves_live_state_unchanged(self):
        async with self.client() as session:
            await self.import_source(session)
            before = await self.call(session, 'workspace_status')
            plan = await self.call(session, 'preview_workspace_cleanup', scope='workspace')
            # Real filesystem failure, not a patched backup function.
            backup_dir = self.store.root/'backups'
            backup_dir.rmdir()
            backup_dir.write_text('A real file blocks creation of the backup directory.')
            result = await session.call_tool('cleanup_workspace', dict(scope='workspace', plan_hash=plan['plan_hash'],
                expected_revision=before['revision'], idempotency_key='backup-failure'))
            self.assertTrue(result.is_error)
            self.assertEqual(self.store.read()['revision'], before['revision'])
            self.assertEqual(self.store.read()['sources'].keys(), before['sources'].keys())
            backup_dir.unlink()
            backup_dir.mkdir()
            self.assertEqual((await self.call(session, 'workspace_status'))['search_index'], before['search_index'])
