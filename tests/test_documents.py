"""Real-source integration checks for document and chunk lifecycle; no model judge."""
import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from research_rag_mcp.store import Store
from research_rag_mcp import semantic
from support import prepare_files, blocks, save


class DocumentIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.TemporaryDirectory()
        store, _ = prepare_files(cls.base.name)
        store.start_project('Trace the supplied brms article', 'Verify source and chunk identities, not scientific claims', [], 0, 'project')
        cls.source = store.import_document('brms.pdf', 'https://doi.org/10.18637/jss.v080.i01', 'literature',
                        {'title':'brms: An R Package for Bayesian Multilevel Models Using Stan'}, 1, 'pdf')['result']

    @classmethod
    def tearDownClass(cls):
        cls.base.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        shutil.copytree(self.base.name, self.tmp.name, dirs_exist_ok=True)
        self.store = Store(self.tmp.name)
        self.sid = self.source['source_id']
        self.cid = self.store.list_chunks(self.sid)['chunks'][0]['id']

    def tearDown(self):
        self.tmp.cleanup()

    def mutate(self, name, *args):
        return getattr(self.store, name)(*args, self.store.read()['revision'], uuid.uuid4().hex)

    def test_original_thai_query_recovers_exact_abstract_with_no_lexical_hit(self):
        # Codex inspected this real abstract as relevant to the query; this assertion
        # records that narrow locator regression, not an automated semantic judgement.
        query='การประมาณค่าแบบเบย์สำหรับข้อมูลที่มีโครงสร้างหลายระดับ'
        self.assertEqual(self.store.search(query,mode='lexical')['hits'],[])
        for mode in ('semantic','hybrid'):
            hits=self.store.search(query,mode=mode,limit=3)['hits']
            self.assertTrue(any(h['page_index']==0 and h['start']==0 for h in hits))
            for hit in hits:
                self.assertEqual(self.store.citation(hit['citation'],self.store.read()),hit['citation'])

    def test_identity_context_integrity_and_coverage(self):
        inventory=self.store.list_documents()
        self.assertEqual(inventory['total'],1)
        chunk=self.store.read_chunk(self.cid)
        self.assertEqual(chunk['document_id'],self.source['document_id'])
        self.assertEqual(chunk['source_version'],1)
        self.assertEqual(chunk['embedding']['model_fingerprint'],semantic.FINGERPRINT)
        context=self.store.get_chunk_context(self.cid)
        self.assertEqual(context['source_page']['text'][chunk['start']:chunk['end']],chunk['text'])
        inspected=self.store.inspect_document_chunks(self.sid)
        self.assertFalse(any(p['uncovered_nonblank_spans'] for p in inspected['pages']))
        self.assertTrue(self.store.search_index_status()['ready'])

    def test_rechunk_preserves_citations_ids_history_and_switches_search(self):
        original=self.store.read_chunk(self.cid)
        artifact=save(self.store,'manuscript',blocks('manuscript',original['citation']))
        revised=save(self.store,'manuscript',blocks('manuscript',original['citation']),artifact_id=artifact['id'])
        candidate=self.mutate('rechunk_document',self.sid,800,100)['result']
        self.assertFalse(candidate['active'])
        self.assertEqual(self.store.list_chunks(self.sid)['chunk_set_id'],original['chunk_set_id'])
        self.mutate('activate_chunk_set',candidate['chunk_set_id'])
        hits=self.store.search('Bayesian multilevel',mode='hybrid')['hits']
        self.assertTrue(hits)
        self.assertTrue(all(h['chunk_set_id']==candidate['chunk_set_id'] for h in hits))
        self.assertEqual(self.store.read_chunk(self.cid)['citation'],original['citation'])
        self.assertEqual(self.store.get_artifact(artifact['id'],1)['blocks'][0]['citations'][0],original['citation'])
        usages=self.store.find_evidence_usage(self.cid)['usages']
        self.assertEqual({u['version'] for u in usages},{1,2})
        self.assertTrue(any(u['current'] and u['version']==revised['version'] for u in usages))
        self.assertEqual(self.store.get_artifact(artifact['id'])['issues'],[])

    def test_exclusion_filters_search_and_flags_manuscript(self):
        hit=self.store.search('Bayesian multilevel',mode='semantic')['hits'][0]
        manuscript=save(self.store,'manuscript',blocks('manuscript',hit['citation']))
        self.mutate('set_chunk_status',hit['id'],'needs_review','Researcher must inspect the original extraction')
        for mode in ('lexical','semantic','hybrid'):
            self.assertNotIn(hit['id'],{h['id'] for h in self.store.search('Bayesian multilevel',limit=30,mode=mode)['hits']})
        self.assertIn('needs_review',self.store.get_artifact(manuscript['id'])['effective_status'])
        self.assertTrue(self.store.find_evidence_usage(hit['id'])['usages'])
        self.mutate('set_chunk_status',hit['id'],'active','Original extraction inspected in this lifecycle test')
        self.assertEqual(self.store.get_artifact(manuscript['id'])['issues'],[])

    def test_document_versions_and_explicit_historical_search(self):
        # A real extracted-text representation of the same paper, not invented scientific content.
        text='\n\n'.join(p['text'] for p in self.store.read()['sources'][self.sid]['pages'])
        (self.store.root/'inbox/brms-extracted.txt').write_text(text)
        second=self.store.import_document('brms-extracted.txt','Text extracted from the supplied brms PDF','literature',
                    {'title':self.source['bibliography']['title']},self.store.read()['revision'],'text-representation',self.source['document_id'])['result']
        self.assertEqual(second['document_id'],self.source['document_id'])
        self.assertEqual(second['source_version'],2)
        self.assertNotEqual(second['source_id'],self.sid)
        self.assertTrue(all(h['source_id']==second['source_id'] for h in self.store.search('Bayesian',mode='lexical')['hits']))
        self.assertTrue(all(h['source_id']==self.sid for h in self.store.search('Bayesian',source_ids=[self.sid])['hits']))
        self.assertEqual(len(self.store.list_documents()['documents'][0]['versions']),2)
        self.assertEqual(self.store.read_chunk(self.cid)['source_version'],1)

    def test_vector_corruption_errors_and_explicit_rebuild(self):
        with self.store.connect() as db:
            db.execute('UPDATE embeddings SET vector=? WHERE chunk_id=?',(b'corrupt',self.cid))
        self.assertFalse(self.store.search_index_status()['ready'])
        with self.assertRaisesRegex(ValueError,'integrity'):
            self.store.search('Bayesian',mode='semantic')
        self.assertTrue(self.store.search('Bayesian',mode='lexical')['hits'])
        self.mutate('rebuild_search_index',[self.sid])
        self.assertTrue(self.store.search_index_status()['ready'])
        self.assertTrue(self.store.search('Bayesian',mode='semantic')['hits'])

    def test_invalid_mutations_are_atomic_and_idempotent(self):
        before=self.store.read()['revision']
        with self.assertRaises(ValueError):
            self.mutate('rechunk_document',self.sid,200,200)
        self.assertEqual(before,self.store.read()['revision'])
        arguments=(self.cid,'excluded','Lifecycle test',before,'exclude-once')
        result=self.store.set_chunk_status(*arguments)
        self.assertEqual(self.store.set_chunk_status(*arguments),result)
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.store.set_chunk_status(self.cid,'active','Reset',before,'new-key')

    def test_backup_restores_identity_and_semantic_index(self):
        expected=self.store.search('Bayesian estimation',mode='semantic',limit=3)
        backup=self.store.backup()
        dest=Path(self.tmp.name)/'restored'
        Store.restore(backup['directory'],dest)
        restored=Store(dest)
        actual=restored.search('Bayesian estimation',mode='semantic',limit=3)
        self.assertEqual(actual['hits'],expected['hits'])
        self.assertEqual(restored.read_chunk(self.cid),self.store.read_chunk(self.cid))
        self.assertTrue(restored.search_index_status()['ready'])
