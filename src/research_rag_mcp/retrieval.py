"""CPU lexical retrieval: BM25 plus Unicode Thai character n-grams.

No embeddings, translation, model calls or fabricated semantic confidence scores.
Offsets always address the unnormalized extracted original text.
"""
import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache


@lru_cache(maxsize=8192)
def tokens(text):
    value = unicodedata.normalize('NFKC', text).casefold()
    terms = re.findall(r'[^\W_]+', re.sub(r'[\u0e00-\u0e7f]+', ' ', value), re.UNICODE)
    for run in re.findall(r'[\u0e00-\u0e7f]+', value):
        terms.extend('th:' + run[i:i+n] for n in (2, 3) for i in range(max(0, len(run)-n+1)))
        if len(run) == 1:
            terms.append('th:' + run)
    return tuple(terms)


def chunks(text, size=1200, overlap=200):
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = text.rfind('\n', start + size//2, end)
            if boundary != -1:
                end = boundary + 1
        if text[start:end].strip():
            yield start, end, text[start:end]
        if end == len(text):
            break
        start = max(start+1, end-overlap)


def rank(rows, query, limit, remove_overlap=True):
    terms = set(tokens(query))
    if not terms:
        raise ValueError('query must contain searchable text')
    counts = [Counter(tokens(row['text'])) for row in rows]
    lengths = [sum(count.values()) for count in counts]
    average = sum(lengths)/max(1, len(lengths)) or 1
    frequencies = {t: sum(t in count for count in counts) for t in terms}
    scored = []
    for row, count, length in zip(rows, counts, lengths):
        score = 0.0
        matched = []
        for term in terms:
            tf = count[term]
            if tf:
                idf = math.log(1 + (len(rows)-frequencies[term]+0.5)/(frequencies[term]+0.5))
                score += idf * tf * 2.2 / (tf + 1.2*(0.25+0.75*length/average))
                matched.append(term)
        if score:
            scored.append({**row, 'score': round(score, 6), 'matched_terms': sorted(matched)})
    scored.sort(key=lambda r: (-r['score'], r['source_id'], r['page_index'], r['start']))
    return deduplicate(scored, limit) if remove_overlap else scored[:limit]


def deduplicate(scored, limit):
    selected = []
    for row in scored:
        # Avoid near-duplicate overlapping chunks on the same source page.
        if any(row['source_id'] == old['source_id'] and row['page_index'] == old['page_index']
               and min(row['end'], old['end'])-max(row['start'], old['start']) > min(row['end']-row['start'], old['end']-old['start'])*0.5
               for old in selected):
            continue
        selected.append(row)
        if len(selected) == limit:
            break
    return selected
