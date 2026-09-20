"""Real HTTP preview-to-import regression; real source documents, no mocks."""
import hashlib
import unittest

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from pypdf import PdfReader

import test_http


class InboxHTTPIntegration(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_http.HTTPIntegration.asyncSetUp
    asyncTearDown = test_http.HTTPIntegration.asyncTearDown

    async def test_preview_before_import_over_actual_http(self):
        async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+self.token},
                                     timeout=httpx2.Timeout(30, read=300)) as http:
            async with streamable_http_client(self.url, http_client=http) as streams:
                async with ClientSession(*streams, read_timeout_seconds=300) as session:
                    await session.initialize()
                    async def call(name, **arguments):
                        result = await session.call_tool(name, arguments)
                        self.assertFalse(result.is_error, str(result))
                        return result.structured_content
                    preview = await call('preview_inbox_document', filename='brms.pdf')
                    original = self.store.root/'inbox/brms.pdf'
                    reader = PdfReader(original)
                    first_page = reader.pages[0].extract_text()
                    self.assertEqual(preview['text'], first_page[:12000])
                    self.assertEqual(preview['sha256'], hashlib.sha256(original.read_bytes()).hexdigest())
                    self.assertEqual(preview['page_count'], len(reader.pages))
                    self.assertEqual(preview['metadata']['title'], reader.metadata.title)
                    self.assertIn('brms', preview['text'])
                    state = await call('workspace_status')
                    self.assertEqual(state['revision'], 0)
                    self.assertEqual(state['sources'], {})
                    self.assertEqual(state['search_index']['total_chunks'], 0)
                    self.assertEqual(list((self.store.root/'sources').iterdir()), [])
                    imported = await call('import_document', filename='brms.pdf',
                        origin='https://doi.org/10.18637/jss.v080.i01', role='literature',
                        bibliography={'title': 'brms: An R Package for Bayesian Multilevel Models Using Stan'},
                        expected_revision=0, idempotency_key='preview-to-import')
                    self.assertEqual(imported['result']['source_id'], preview['sha256'])
                    page = await call('read_source_page', source_id=preview['sha256'], page_index=0)
                    self.assertEqual(page['text'], first_page)
                    self.assertTrue((await call('search_index_status'))['ready'])

    async def test_preview_pagination_and_inbox_boundary(self):
        # A link to the real test workspace token must not allow an inbox escape.
        (self.store.root/'inbox/outside.txt').symlink_to(self.store.root/'.http-token')
        async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+self.token}, timeout=30) as http:
            async with streamable_http_client(self.url, http_client=http) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    async def preview(**arguments):
                        result = await session.call_tool('preview_inbox_document', arguments)
                        self.assertFalse(result.is_error, str(result))
                        return result.structured_content
                    first = await preview(filename='brms.pdf', start=0, max_chars=100)
                    second = await preview(filename='brms.pdf', start=first['next_start'], max_chars=100)
                    expected = PdfReader(self.store.root/'inbox/brms.pdf').pages[0].extract_text()
                    self.assertEqual(first['text']+second['text'], expected[:200])
                    self.assertEqual(second['start'], 100)
                    last = await preview(filename='brms.pdf', start=first['page_characters'])
                    self.assertEqual(last['text'], '')
                    self.assertIsNone(last['next_start'])
                    text = await preview(filename='guidelines.txt')
                    self.assertEqual(text['text'], (self.store.root/'inbox/guidelines.txt').read_text())
                    self.assertEqual(text['metadata'], {})
                    for args in [dict(filename='../.http-token'), dict(filename='outside.txt'),
                                 dict(filename='absent.pdf'), dict(filename='brms.pdf', page_index=-1),
                                 dict(filename='brms.pdf', page_index=1000),
                                 dict(filename='brms.pdf', start=first['page_characters']+1),
                                 dict(filename='brms.pdf', max_chars=20001),
                                 dict(filename='brms.pdf', max_chars=0)]:
                        result = await session.call_tool('preview_inbox_document', args)
                        self.assertTrue(result.is_error, args)
                        self.assertNotIn(self.token, str(result))
                    state = await session.call_tool('workspace_status', {})
                    self.assertEqual(state.structured_content['revision'], 0)
                    self.assertEqual(state.structured_content['sources'], {})
