"""Live bibliographic discovery from the real Crossref service."""
import json
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .store import now, require_text, dump


def search_literature(store, query, limit, year_from, year_to, expected_revision, key):
    require_text(query, 'public literature query', 1000)
    if not 1 <= limit <= 50:
        raise ValueError('limit must be 1..50')
    for year in (year_from, year_to):
        if year is not None and not 1000 <= year <= 9999:
            raise ValueError('Invalid publication year')
    if year_from and year_to and year_from > year_to:
        raise ValueError('year_from must not exceed year_to')
    params = {'query.bibliographic': query, 'rows': limit}
    filters = []
    if year_from:
        filters.append(f'from-pub-date:{year_from}-01-01')
    if year_to:
        filters.append(f'until-pub-date:{year_to}-12-31')
    if filters:
        params['filter'] = ','.join(filters)
    url = 'https://api.crossref.org/works?' + urllib.parse.urlencode(params)
    def action(db, state):
        request = urllib.request.Request(url, headers={
            'User-Agent': 'codex-research-rag-mcp/0.1.0 (public bibliographic discovery)',
            'Accept': 'application/json',
        })
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read(5*1024*1024+1)
            if len(raw) > 5*1024*1024:
                raise ValueError('Crossref response exceeds size limit')
            message = json.loads(raw)['message']
            records = []
            seen = set()
            for item in message['items']:
                doi = item.get('DOI')
                if doi and doi.casefold() in seen:
                    continue
                if doi:
                    seen.add(doi.casefold())
                records.append(dict(
                    doi=doi, title='; '.join(item.get('title', [])),
                    authors=[' '.join(x for x in (a.get('given'), a.get('family')) if x) or a.get('name', '')
                             for a in item.get('author', [])],
                    date_parts=item.get('published', item.get('issued', {})).get('date-parts'),
                    venue=item.get('container-title', []), url=item.get('URL'),
                    resource_type=item.get('type'), license=item.get('license', []),
                    full_text_read=False,
                ))
        except urllib.error.HTTPError as exc:
            raise ValueError(f'Crossref HTTP {exc.code}; no search result saved. Retry later if rate limited.') from exc
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f'Crossref unavailable or invalid response ({type(exc).__name__}); no search result saved') from exc
        record = dict(id=uuid.uuid4().hex, provider='Crossref', query=query, url=url,
                      searched_at=now(), total_results=message.get('total-results'),
                      returned=len(records), limit=limit, year_from=year_from, year_to=year_to, records=records,
                      coverage='One page of Crossref bibliographic metadata. Not exhaustive; no full-text reading or novelty assessment.')
        db.execute('INSERT INTO searches VALUES(?,?)', (record['id'], dump(record)))
        return record
    return store.mutate('search_literature', params, expected_revision, key, action)
