"""Eight stage-specific evidence packets, checks, and manuscript export."""
import uuid

from .models import STAGES
from .store import dump, now


def status(store):
    state = store.read()
    return {**state,
            'sources': {sid: store.source_summary(src) for sid, src in state['sources'].items()},
            'artifacts': {aid: store.artifact_view(a, state) for aid, a in state['artifacts'].items()},
            'inbox': sorted(p.name for p in (store.root/'inbox').iterdir() if p.is_file()),
            'stages': STAGES, 'search_index': store.search_index_status(),
            'capabilities': {'transport': 'streamable-http', 'online_discovery': 'Crossref metadata',
                             'retrieval': 'Thai lexical / Ollama semantic / hybrid (default), local CPU; cross-language quality must be checked', 'generation': 'connected MCP client',
                             'external_model_calls': False, 'automatic_semantic_grading': False,
                             'automatic_experiments': False, 'automatic_submission': False}}


def matrix(store, state):
    rows = []
    for sid, source in state['sources'].items():
        if source['role'] != 'literature':
            continue
        notes = [store.artifact_view(a, state) for a in state['artifacts'].values()
                 if a['stage'] == 'literature_note' and any(c['source_id'] == sid for b in a['blocks'] for c in b['citations'])]
        fields = {name: [] for name in STAGES['literature_note']['sections']}
        for note in notes:
            for block in note['blocks']:
                if block['section'] in fields:
                    fields[block['section']].append({**block, 'artifact_id': note['id'], 'version': note['version'],
                                                    'review_status': note['effective_status']})
        rows.append(dict(source_id=sid, bibliography=source['bibliography'], origin=source['origin'],
                         fields=fields, missing_fields=[name for name, values in fields.items() if not values]))
    return rows


def stage_context(store, stage, query, limit=8):
    if stage not in STAGES or stage == 'literature_note':
        raise ValueError('Choose one of the eight research stages')
    state = store.read()
    if not state['project']:
        raise ValueError('Start the research project first')
    result = {'stage': stage, **STAGES[stage], 'revision': state['revision'], 'project': state['project'],
              'retrieval': store.search(query, limit=limit),
              'saved_artifacts': [store.artifact_view(a, state) for a in state['artifacts'].values()
                                  if a['stage'] != 'literature_note'],
              'required_output': {'tool': 'save_artifact', 'stage': stage, 'sections': STAGES[stage]['sections'],
                                  'rule': 'Use cited blocks. Mark unsupported fields unresolved; list source artifacts in dependency_ids.'},
              'generation_status': 'context_ready_for_connected_client; no prose generated or saved by this tool'}
    if stage in ('exploration', 'gaps', 'question', 'design'):
        result['literature'] = store.search(query, roles=['literature'], limit=limit)
    if stage in ('exploration', 'gaps'):
        result['literature_matrix'] = matrix(store, state)
        result['search_history'] = state['searches']
        result['coverage'] = {'imported_literature': sum(s['role'] == 'literature' for s in state['sources'].values()),
                              'searches_recorded': len(state['searches']),
                              'unread_crossref_records': sum(s['returned'] for s in state['searches']),
                              'exhaustive': False, 'novelty_proven': False}
    if stage in ('execution', 'analysis', 'manuscript'):
        result['project_evidence'] = store.search(query, roles=['protocol', 'project_note', 'data', 'results'], limit=limit)
        result['literature'] = store.search(query, roles=['literature'], limit=limit)
        result['execution_log'] = [store.artifact_view(a, state) for a in state['artifacts'].values() if a['stage'] == 'execution']
        if stage == 'analysis':
            result['available_datasets'] = [store.source_summary(s) for s in state['sources'].values()
                                            if s['role'] in ('data', 'results')]
            result['analysis_hint'] = 'Use summarize_dataset for real CSV descriptive summaries. Import actual inferential analysis outputs; this server does not run statistical experiments.'
    return result


def submission_check(store, manuscript_id, guideline_source_id, submission_id=None):
    state = store.read()
    manuscript = state['artifacts'].get(manuscript_id)
    guidelines = state['sources'].get(guideline_source_id)
    if not manuscript or manuscript['stage'] != 'manuscript':
        raise ValueError('A saved manuscript artifact is required')
    if not guidelines or guidelines['role'] != 'journal_guidelines':
        raise ValueError('An imported original journal_guidelines source is required')
    store.verify_source(guidelines)
    blockers = store.artifact_issues(manuscript, state)
    if manuscript['status'] != 'accepted':
        blockers.append('Manuscript has not been accepted in the human review UI')
    unsupported = []
    unresolved = []
    for i, block in enumerate(manuscript['blocks']):
        if block['basis'] == 'unresolved':
            unresolved.append(i)
        if block['basis'] not in ('evidence', 'analysis_result') or not block['citations']:
            unsupported.append(i)
    if unresolved:
        blockers.append('Manuscript contains unresolved blocks')
    if not any(b['section'] == 'results' and b['basis'] == 'analysis_result' for b in manuscript['blocks']):
        blockers.append('No results block linked to actual project data/results; inspect applicability for this article type')
    for ref in manuscript['dependencies']:
        dependency = state['artifacts'][ref['id']]
        if dependency['status'] != 'accepted':
            blockers.append('Manuscript dependency has not been accepted: ' + ref['id'])
    submission = state['artifacts'].get(submission_id) if submission_id else None
    if submission_id and (not submission or submission['stage'] != 'submission'):
        raise ValueError('submission_id must identify a submission artifact')
    if submission:
        blockers.extend(store.artifact_issues(submission, state))
        if submission['status'] != 'accepted':
            blockers.append('Submission checklist has not been accepted by the researcher')
        if not any(r['id'] == manuscript_id and r['version'] == manuscript['version'] for r in submission['dependencies']):
            blockers.append('Submission checklist must depend on this exact manuscript version')
        if not any(c['source_id'] == guideline_source_id for b in submission['blocks'] for c in b['citations']):
            blockers.append('Submission checklist must cite the selected journal guidelines')
    else:
        blockers.append('Save and review a submission artifact with the real venue checklist and AI disclosure')
    return dict(stage='submission', **STAGES['submission'], revision=state['revision'],
                manuscript=store.artifact_view(manuscript, state), guideline=store.source_summary(guidelines),
                guideline_page_count=len(guidelines['pages']),
                submission=store.artifact_view(submission, state) if submission else None,
                blockers=list(dict.fromkeys(blockers)), blocks_requiring_author_judgement=unsupported,
                citation_presence_checked=True, semantic_citation_support_checked=False,
                journal_compliance='Requires researcher comparison against original guidelines',
                next_action='Read guideline pages, draft a submission artifact and obtain researcher review' if blockers else 'Researcher makes final submission decision',
                automatic_submission=False)


def export_manuscript(store, manuscript_id, mode, expected_revision, submission_id=None, guideline_source_id=None):
    with store.snapshot() as state:
        if mode not in ('draft', 'reviewed'):
            raise ValueError('mode must be draft or reviewed')
        if state['revision'] != expected_revision:
            raise ValueError('Stale export revision')
        artifact = state['artifacts'].get(manuscript_id)
        if not artifact or artifact['stage'] != 'manuscript':
            raise ValueError('A manuscript artifact is required')
        issues = store.artifact_issues(artifact, state)
        if issues:
            raise ValueError('; '.join(issues))
        check = None
        if mode == 'reviewed':
            if not submission_id or not guideline_source_id:
                raise ValueError('Reviewed export requires submission_id and guideline_source_id')
            check = submission_check(store, manuscript_id, guideline_source_id, submission_id)
            if check['blockers']:
                raise ValueError('Reviewed export blocked: ' + '; '.join(check['blockers']))
            if check['revision'] != state['revision']:
                raise ValueError('Workspace changed during submission check; read status and retry')
        citations = []
        for block in artifact['blocks']:
            for c in block['citations']:
                store.citation(c, state)
                if c['source_id'] not in citations:
                    citations.append(c['source_id'])
        lines = [f'# {artifact["title"]}', '', f'Manuscript ID: {artifact["id"]}', '',
                 f'Export: {mode}; artifact version {artifact["version"]}; workspace revision {state["revision"]}.', '']
        for block in artifact['blocks']:
            lines.extend(['## '+block['section'], '', block['text'], ''])
            if block['citations']:
                lines.append('Evidence: ' + '; '.join(f'[{citations.index(c["source_id"])+1}], page index {c["page_index"]}, characters {c["start"]}–{c["end"]}' for c in block['citations']))
                lines.append('')
            elif mode == 'draft':
                lines.extend([f'Basis: {block["basis"]}; author verification required.', ''])
        lines.extend(['## Limitations', '', *['- '+x for x in artifact['limitations']], '', '## References', ''])
        for i, sid in enumerate(citations, 1):
            source = state['sources'][sid]
            b = source['bibliography']
            lines.append(f'{i}. {"; ".join(b["authors"]) or "Author metadata not supplied"}. ({b["year"] or "Year not supplied"}). {b["title"]}. {source["origin"]}')
        dest = store.root / 'exports' / uuid.uuid4().hex
        dest.mkdir()
        (dest/'manuscript.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
        package = dict(exported_at=now(), workspace_revision=state['revision'], mode=mode,
                       manuscript=store.artifact_view(artifact, state), submission_check=check,
                       sources={sid: store.source_summary(state['sources'][sid]) for sid in citations},
                       note='Human review record, not automated scientific certification. Source files are not redistributed.')
        (dest/'evidence.json').write_text(dump(package)+'\n', encoding='utf-8')
        if check:
            for section, filename in [('cover_letter', 'cover-letter.md'), ('ai_disclosure', 'ai-disclosure.md'), ('checklist', 'submission-checklist.md')]:
                text = '\n\n'.join(b['text'] for b in check['submission']['blocks'] if b['section'] == section)
                (dest/filename).write_text(text+'\n', encoding='utf-8')
        manifest = store.manifest(dest)
        return dict(directory=str(dest), files=sorted(manifest), mode=mode, submitted=False, revision=state['revision'],
                    manuscript_id=artifact['id'], manuscript_version=artifact['version'])
