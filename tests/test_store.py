import json
import tempfile
import unittest
from pathlib import Path

from research_rag_mcp.store import Store, sha
from research_rag_mcp.models import STAGES
from research_rag_mcp.workflow import stage_context, submission_check, export_manuscript
from support import populate, cite, blocks, save, accepted_proposal, ROOT


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store, self.sources, self.lengths = populate(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_pdf_ranked_retrieval_and_exact_spans(self):
        self.assertEqual(sha((ROOT/'tests/evidence/brms.pdf').read_bytes()), '35757e85ffb002fcb6c5dc34fec0daa6a84302d552e7555f2551838c4599fffb')
        result = self.store.search('Bayesian multilevel Stan', roles=['literature'], mode='lexical')
        self.assertTrue(result['hits'])
        self.assertEqual(result['corpus_sources'], 1)
        for hit in result['hits']:
            self.store.citation(hit['citation'], self.store.read())
            self.assertEqual(hit['source_id'], self.sources['literature'])
        self.assertGreater(len(result['hits'][0]['matched_terms']), 1)
        self.assertEqual(self.store.search('zxqvneverpresent98214', mode='lexical')['status'], 'insufficient_retrieved_evidence')

    def test_thai_search_from_real_readme(self):
        result = self.store.search('หลักฐานต้นฉบับ', roles=['project_note'], mode='lexical')
        self.assertTrue(result['hits'])
        self.assertTrue(any('หลักฐาน' in hit['text'] for hit in result['hits']))
        self.assertTrue(all(hit['source_id'] == self.sources['project_note'] for hit in result['hits']))

    def test_real_csv_summary(self):
        result = self.store.profile_csv(self.sources['results'])
        self.assertEqual(result['rows'], len(self.lengths))
        column = next(c for c in result['columns'] if c['column'] == 'text_characters')
        self.assertEqual(column['min'], min(self.lengths))
        self.assertEqual(column['max'], max(self.lengths))
        self.assertAlmostEqual(column['mean'], sum(self.lengths)/len(self.lengths))

    def test_reject_invalid_citation_and_foreign_import(self):
        citation = cite(self.store, self.sources['literature'], 'brms')
        citation['end'] += 1
        initial = self.store.read()['revision']
        with self.assertRaisesRegex(ValueError, 'exact source page span'):
            save(self.store, 'exploration', blocks('exploration', citation))
        self.assertEqual(self.store.read()['revision'], initial)
        with self.assertRaisesRegex(ValueError, 'inside this workspace inbox'):
            self.store.import_document(str(ROOT/'README.md'), 'Local README', 'project_note', {'title': 'README'}, initial, 'foreign')

    def test_evidence_and_result_roles_enforced(self):
        content = blocks('analysis')
        content[0].update(basis='analysis_result', text='This attempts to label literature as our result.',
                          citations=[cite(self.store, self.sources['literature'], 'brms')])
        with self.assertRaisesRegex(ValueError, 'actual project data or results'):
            save(self.store, 'analysis', content)
        content[0]['citations'] = []
        with self.assertRaisesRegex(ValueError, 'require citations'):
            save(self.store, 'analysis', content)

    def test_idempotency_revision_and_history(self):
        revision = self.store.read()['revision']
        args = ('question', 'Question protocol record', blocks('question'), [], [], revision, 'once')
        first = self.store.save_artifact(*args)
        self.assertEqual(self.store.save_artifact(*args), first)
        with self.assertRaisesRegex(ValueError, 'different input'):
            self.store.save_artifact('question', 'Changed', blocks('question'), [], [], revision, 'once')
        with self.assertRaisesRegex(ValueError, 'Stale revision'):
            self.store.save_artifact('question', 'Changed', blocks('question'), [], [], revision, 'new-key')
        updated = save(self.store, 'question', artifact_id=first['result']['id'])
        self.assertEqual(updated['version'], 2)
        self.assertEqual(updated['status'], 'draft')
        self.assertTrue(self.store.get_artifact(updated['id'], 1)['historical'])

    def test_dependency_revisions_and_cycles(self):
        question = accepted_proposal(self.store)
        design = accepted_proposal(self.store, 'design', [question['id']])
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            save(self.store, 'question', dependencies=[design['id']], artifact_id=question['id'])
        save(self.store, 'question', artifact_id=question['id'])
        self.assertEqual(self.store.get_artifact(design['id'])['effective_status'], 'needs_review')

    def test_dependency_review_withdrawal_invalidates_acceptance(self):
        question = accepted_proposal(self.store)
        design = accepted_proposal(self.store, 'design', [question['id']])
        self.store.review(question['id'], 'unresolved', 'Protocol test operator', 'Withdraw this protocol acceptance',
                          self.store.read()['revision'], 'withdraw')
        self.assertEqual(self.store.get_artifact(design['id'])['effective_status'], 'needs_review')

    def test_tampering_blocks_retrieval_and_export(self):
        manuscript = save(self.store, 'manuscript', blocks('manuscript', cite(self.store, self.sources['literature'], 'brms')))
        source = self.store.read()['sources'][self.sources['literature']]
        original = self.store.root/source['file']
        original.write_bytes(original.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            self.store.search('brms')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            export_manuscript(self.store, manuscript['id'], 'draft', self.store.read()['revision'])

    def test_seven_contexts_and_submission_blockers(self):
        for stage in ('exploration', 'gaps', 'question', 'design', 'execution', 'analysis', 'manuscript'):
            result = stage_context(self.store, stage, 'Bayesian multilevel Stan')
            self.assertTrue(result['retrieval']['hits'])
            self.assertEqual(result['stage'], stage)
            artifact = save(self.store, stage, blocks(stage, cite(self.store, self.sources['literature'], 'brms')))
        result = submission_check(self.store, artifact['id'], self.sources['journal_guidelines'])
        self.assertTrue(result['blockers'])
        self.assertFalse(result['semantic_citation_support_checked'])
        with self.assertRaisesRegex(ValueError, 'Reviewed export'):
            export_manuscript(self.store, artifact['id'], 'reviewed', self.store.read()['revision'])
        export = export_manuscript(self.store, artifact['id'], 'draft', self.store.read()['revision'])
        directory = Path(export['directory'])
        self.assertIn('brms', (directory/'manuscript.md').read_text())
        for name, digest in json.loads((directory/'manifest.json').read_text()).items():
            self.assertEqual(sha((directory/name).read_bytes()), digest)

    def test_backup_restore_preserves_sources_artifacts_and_search_index(self):
        artifact = save(self.store, 'question')
        snapshot = self.store.backup()
        destination = Path(self.tmp.name)/'restored'
        Store.restore(snapshot['directory'], destination)
        restored = Store(destination)
        self.assertEqual(restored.read(), self.store.read())
        self.assertEqual(restored.get_artifact(artifact['id'])['version'], 1)
        self.assertTrue(restored.search('Bayesian')['hits'])
        self.assertFalse((destination/'.http-token').exists())

    def test_restore_rejects_absolute_manifest_paths(self):
        snapshot = self.store.backup()
        folder = Path(snapshot['directory'])
        manifest = json.loads((folder/'manifest.json').read_text())
        source_path = next(name for name in manifest if name.startswith('sources/'))
        manifest[str(folder/source_path)] = manifest.pop(source_path)
        (folder/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'relative'):
            Store.restore(folder, Path(self.tmp.name)/'invalid-restore')
        self.assertFalse((Path(self.tmp.name)/'invalid-restore').exists())

    def test_whitespace_is_not_evidence(self):
        citation = cite(self.store, self.sources['literature'], ' ')
        with self.assertRaisesRegex(ValueError, 'nonempty'):
            self.store.citation(citation, self.store.read())

    def test_literature_note_rejects_project_material_as_study(self):
        content = blocks('literature_note', cite(self.store, self.sources['project_note']))
        with self.assertRaisesRegex(ValueError, 'one literature source'):
            save(self.store, 'literature_note', content)

    def test_literature_matrix_retains_actual_citations_and_unknowns(self):
        content = blocks('literature_note')
        content[2] = dict(section='method', text='The source explicitly mentions Stan.', basis='evidence',
                          citations=[cite(self.store, self.sources['literature'], 'Stan')])
        artifact = save(self.store, 'literature_note', content)
        result = stage_context(self.store, 'gaps', 'Bayesian multilevel Stan')
        row = result['literature_matrix'][0]
        self.assertEqual(row['source_id'], self.sources['literature'])
        self.assertEqual(row['fields']['method'][0]['artifact_id'], artifact['id'])
        self.assertEqual(row['fields']['method'][0]['citations'][0]['quote'], 'Stan')
        self.assertEqual(row['fields']['population'][0]['basis'], 'unresolved')
        self.assertFalse(result['coverage']['novelty_proven'])


if __name__ == '__main__':
    unittest.main()
