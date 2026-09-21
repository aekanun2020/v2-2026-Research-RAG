"""LlamaIndex sentence chunks with exact locators into unchanged source pages.

No LLM calls or semantic splitting. Tokenization assets are pinned and bundled.
"""
import hashlib
import re
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path

from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.schema import Document
from tokenizers import Tokenizer


DEFAULT_SIZE = 512
DEFAULT_OVERLAP = 64
TOKENIZER_PATH = Path(__file__).parent / 'assets' / 'nomic-tokenizer.json'


@lru_cache(maxsize=1)
def tokenizer():
    result = Tokenizer.from_file(str(TOKENIZER_PATH))
    result.no_truncation()
    result.no_padding()
    return result


def token_ids(text):
    return tokenizer().encode(text, add_special_tokens=False).ids


@lru_cache(maxsize=1)
def english_sentences():
    import nltk.data
    import llama_index.core
    from nltk.tokenize import PunktTokenizer
    cache = Path(llama_index.core.__file__).parent / '_static' / 'nltk_cache'
    nltk.data.path.insert(0, str(cache))
    return PunktTokenizer('english')


def sentence_parts(text):
    if not text.strip():
        return [text]
    if re.search(r'[\u0e00-\u0e7f]', text):
        from pythainlp.tokenize import sent_tokenize
        result = sent_tokenize(text, engine='crfcut', keep_whitespace=True)
        if ''.join(result) != text:
            raise ValueError('Thai sentence segmentation changed original text')
        return result
    spans = list(english_sentences().span_tokenize(text))
    starts = [0] + [start for start, _ in spans[1:]] + [len(text)]
    return [text[a:b] for a, b in zip(starts, starts[1:])]


def configuration(size=DEFAULT_SIZE, overlap=DEFAULT_OVERLAP, markdown=False):
    if type(size) is not int or not 64 <= size <= 2048:
        raise ValueError('chunk_size_tokens must be an integer from 64 to 2048')
    if type(overlap) is not int or not 0 <= overlap < (size - 2) // 2:
        raise ValueError('chunk_overlap_tokens must be below half the content token budget')
    return dict(method='llamaindex-markdown-sentence-v1' if markdown else 'llamaindex-sentence-v1', size=size, overlap=overlap,
                unit='tokens', special_token_reserve=2,
                tokenizer='nomic-ai/nomic-embed-text-v1.5',
                tokenizer_sha256=hashlib.sha256(TOKENIZER_PATH.read_bytes()).hexdigest(),
                llama_index_version=version('llama-index-core'),
                sentence_engines={'english': 'nltk-punkt-english', 'thai': 'pythainlp-crfcut'},
                page_boundary='hard; no cross-page chunks')


def sections(text, markdown):
    """Map the official parser's boundaries back to untouched source characters.

    MarkdownNodeParser may normalize heading whitespace. Only its boundaries and
    heading metadata are used; every stored/embedded chunk remains a source slice.
    Any non-whitespace rewrite or omission is an error, never silently accepted.
    """
    if not markdown or not text.strip():
        return [dict(start=0, end=len(text), heading=None, header_path=None)]
    nodes = MarkdownNodeParser().get_nodes_from_documents([Document(text=text)])
    positions = [i for i, char in enumerate(text) if not char.isspace()]
    compact = ''.join(text[i] for i in positions)
    cursor = 0
    result = []
    for node in nodes:
        expected = ''.join(char for char in node.text if not char.isspace())
        if not expected or compact[cursor:cursor+len(expected)] != expected:
            raise ValueError('Markdown parser changed non-whitespace source content')
        start = positions[cursor] if cursor else 0
        heading = re.match(r'^#{1,6}\s+([^\r\n]+)', text[start:].lstrip())
        result.append(dict(start=start, end=len(text),
                           heading=heading.group(1).strip() if heading else None,
                           header_path=node.metadata.get('header_path')))
        cursor += len(expected)
    if cursor != len(compact):
        raise ValueError('Markdown parser omitted source content')
    for current, following in zip(result, result[1:]):
        current['end'] = following['start']
    return result


def page_chunks(text, size=DEFAULT_SIZE, overlap=DEFAULT_OVERLAP, markdown=False):
    for section in sections(text, markdown):
        for chunk in sentence_chunks(text[section['start']:section['end']], size, overlap):
            yield {**chunk, 'start': section['start']+chunk['start'],
                   'end': section['start']+chunk['end'], 'section': section}


def sentence_chunks(text, size=DEFAULT_SIZE, overlap=DEFAULT_OVERLAP):
    configuration(size, overlap)
    splitter = SentenceSplitter(chunk_size=size-2, chunk_overlap=overlap,
                                tokenizer=token_ids, chunking_tokenizer_fn=sentence_parts,
                                paragraph_separator='\n\n', secondary_chunking_regex=None)
    previous_start = -1
    previous_end = 0
    for part in splitter.split_text(text):
        start = text.find(part, previous_start+1)
        while start != -1 and start+len(part) <= previous_end:
            start = text.find(part, start+1)
        if start == -1:
            raise ValueError('LlamaIndex chunk cannot be located in unchanged source text')
        end = start+len(part)
        if text[previous_end:start].strip():
            raise ValueError('Chunking left nonblank source text uncovered')
        count = len(tokenizer().encode(part, add_special_tokens=True).ids)
        if count > size:
            raise ValueError('Chunk exceeds its configured token budget')
        yield dict(start=start, end=end, text=text[start:end], token_count=count)
        previous_start, previous_end = start, end
    if text[previous_end:].strip():
        raise ValueError('Chunking left nonblank source text uncovered')
