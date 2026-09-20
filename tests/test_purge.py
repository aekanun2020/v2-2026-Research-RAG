"""Permanent cleanup integration through the real MCP HTTP server."""
import hashlib
import json
import shutil
import unittest

import test_cleanup
import test_http
from support import blocks


class PurgeHTTPIntegration(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_http.HTTPIntegration.asyncSetUp
    asyncTearDown = test_http.HTTPIntegration.asyncTearDown
    client = test_cleanup.CleanupHTTPIntegration.client
    call = test_cleanup.CleanupHTTPIntegration.call
    import_source = test_cleanup.CleanupHTTPIntegration.import_source

    def inbox_hashes(self):
        return {str(p.relative_to(self.store.root/'inbox')): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.store.root/'inbox').rglob('*') if p.is_file()}

    async def prepare(self, session):
        await self.call(session, 'start_project', topic='Permanent cleanup protocol verification',
            goal='Verify inbox preservation while deleting real derived workspace data', unknowns=[],
            expected_revision=0, idempotency_key='start')
        imported = await self.import_source(session, pdf=True)
        artifact = await self.call(session, 'save_artifact', stage='manuscript', title='Unresolved protocol record',
            blocks=blocks('manuscript'), limitations=['Protocol test, not research findings'], dependency_ids=[],
            expected_revision=imported['revision'], idempotency_key='manuscript')
        await self.call(session, 'export_manuscript', manuscript_id=artifact['result']['id'],
            expected_revision=artifact['revision'])
        await self.call(session, 'backup_workspace')
        runs = self.store.root/'import-runs'
        runs.mkdir()
        (runs/'actual-import.json').write_text(json.dumps(imported))
        (self.store.root/'actual-import.json').write_text(json.dumps(imported))
        return imported

    async def test_purge_all_data_keeps_inbox_and_credentials_and_retry_is_inert(self):
        async with self.client() as session:
            imported = await self.prepare(session)
            inbox = self.inbox_hashes()
            token = (self.store.root/'.http-token').read_bytes()
            before = await self.call(session, 'workspace_status')
            plan = await self.call(session, 'preview_workspace_cleanup', scope='all_except_inbox')
            self.assertFalse(plan['backup_required'])
            self.assertEqual(plan['source_files_retained'], 0)
            self.assertGreater(plan['filesystem']['files'], 5)
            self.assertEqual(before, await self.call(session, 'workspace_status'))
            args = dict(scope='all_except_inbox', expected_revision=plan['revision'],
                        plan_hash=plan['plan_hash'], idempotency_key='purge-all')
            result = await self.call(session, 'cleanup_workspace', **args)
            self.assertEqual(result['result']['status'], 'completed')
            self.assertIsNone(result['result']['backup'])
            self.assertTrue(result['result']['inbox_unchanged'])
            self.assertEqual(self.inbox_hashes(), inbox)
            self.assertEqual((self.store.root/'.http-token').read_bytes(), token)
            for directory in ('sources', 'exports', 'backups'):
                self.assertEqual(list((self.store.root/directory).iterdir()), [])
            self.assertFalse((self.store.root/'import-runs').exists())
            self.assertFalse((self.store.root/'actual-import.json').exists())
            after = await self.call(session, 'workspace_status')
            self.assertEqual(after['sources'], {})
            self.assertEqual(after['artifacts'], {})
            self.assertEqual(after['searches'], [])
            self.assertIsNone(after['project'])
            self.assertIsNone(after['pending_cleanup'])
            self.assertEqual(after['search_index']['total_chunks'], 0)
            with self.store.connect() as db:
                for table in ('documents','chunks','embeddings','chunk_sets','chunk_metadata','artifacts','versions','searches','events','cleanup_jobs'):
                    self.assertEqual(db.execute(f'SELECT count(*) FROM {table}').fetchone()[0], 0, table)
                self.assertEqual(db.execute('SELECT count(*) FROM requests').fetchone()[0], 1)
            reimported = await self.import_source(session, pdf=True, key='after-purge')
            self.assertEqual(result, await self.call(session, 'cleanup_workspace', **args))
            live = await self.call(session, 'workspace_status')
            self.assertEqual(live['revision'], reimported['revision'])
            self.assertEqual(len(live['sources']), 1)
            self.assertEqual(reimported['result']['source_id'], imported['result']['source_id'])
            self.assertNotEqual(reimported['result']['document_id'], imported['result']['document_id'])

    async def test_changed_files_and_symlinks_do_not_delete_anything(self):
        async with self.client() as session:
            await self.import_source(session)
            before = await self.call(session, 'workspace_status')
            plan = await self.call(session, 'preview_workspace_cleanup', scope='all_except_inbox')
            added = self.store.root/'exports/late-copy.txt'
            shutil.copyfile(self.store.root/'inbox/guidelines.txt', added)
            result = await session.call_tool('cleanup_workspace', dict(scope='all_except_inbox',
                expected_revision=plan['revision'], plan_hash=plan['plan_hash'], idempotency_key='stale-files'))
            self.assertTrue(result.is_error)
            self.assertIn('plan changed', str(result).lower())
            self.assertEqual(before, await self.call(session, 'workspace_status'))
            self.assertTrue(added.exists())
            link = self.store.root/'exports/inbox-link'
            link.symlink_to(self.store.root/'inbox', target_is_directory=True)
            result = await session.call_tool('preview_workspace_cleanup', {'scope': 'all_except_inbox'})
            self.assertTrue(result.is_error)
            self.assertIn('symbolic link', str(result).lower())
            self.assertTrue(link.is_symlink())
            self.assertEqual(before, await self.call(session, 'workspace_status'))

    async def test_partial_filesystem_failure_is_reported_blocks_writes_and_resumes(self):
        locked = self.store.root/'import-runs'
        async with self.client() as session:
            await self.import_source(session)
            locked.mkdir()
            shutil.copyfile(self.store.root/'inbox/guidelines.txt', locked/'original-excerpt.txt')
            locked.chmod(0o500)
            try:
                plan = await self.call(session, 'preview_workspace_cleanup', scope='all_except_inbox')
                args = dict(scope='all_except_inbox', expected_revision=plan['revision'],
                            plan_hash=plan['plan_hash'], idempotency_key='resumable-purge')
                result = await self.call(session, 'cleanup_workspace', **args)
                self.assertEqual(result['result']['status'], 'incomplete')
                self.assertIsNone(result['result']['inbox_unchanged'])
                self.assertIsNone(result['result']['source_files_retained'])
                state = await self.call(session, 'workspace_status')
                self.assertIsNotNone(state['pending_cleanup'])
                self.assertEqual(state['sources'], {})
                backup = await session.call_tool('backup_workspace', {})
                self.assertTrue(backup.is_error)
                start = await session.call_tool('start_project', dict(topic='Protocol retry', goal='Verify pending guard', unknowns=[],
                    expected_revision=state['revision'], idempotency_key='blocked-write'))
                self.assertTrue(start.is_error)
                self.assertIn('pending cleanup', str(start).lower())
                locked.chmod(0o700)
                done = await self.call(session, 'cleanup_workspace', **args)
                self.assertEqual(done['result']['status'], 'completed')
                self.assertIsNone((await self.call(session, 'workspace_status'))['pending_cleanup'])
                self.assertEqual(list((self.store.root/'backups').iterdir()), [])
            finally:
                if locked.exists():
                    locked.chmod(0o700)
