"""Bounded public HTTPS PDF acquisition, independent of evidence import."""
import hashlib
import http.client
import ipaddress
import os
import re
import socket
import ssl
import tempfile
import time
from urllib.parse import urljoin, urlsplit

import pymupdf

MAX_BYTES = 50 * 1024 * 1024


def download_url(url=None, arxiv_id=None):
    if bool(url) == bool(arxiv_id):
        raise ValueError('Supply exactly one public HTTPS PDF url or arxiv_id')
    if arxiv_id:
        if not re.fullmatch(r'(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v[1-9]\d*)?', arxiv_id):
            raise ValueError('Invalid arXiv identifier; supply an ID, optionally with a version')
        url = 'https://arxiv.org/pdf/' + arxiv_id
    validate_url(url)
    return url


def validate_url(url):
    if not isinstance(url, str) or not 1 <= len(url) <= 4000 or any(ord(c) <= 32 for c in url):
        raise ValueError('Invalid HTTPS URL')
    parts = urlsplit(url)
    if (parts.scheme != 'https' or not parts.hostname or parts.port not in (None, 443)
            or parts.username is not None or parts.password is not None or parts.fragment):
        raise ValueError('Only public HTTPS URLs on port 443 without credentials or fragments are allowed')
    return parts


class PublicHTTPS(http.client.HTTPSConnection):
    """Pin each connection to validated DNS results, retaining TLS hostname checks."""
    def connect(self):
        addresses = socket.getaddrinfo(self.host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError('Download destination must resolve exclusively to public IP addresses')
        # No second hostname lookup, environment proxy, tunnel or auth forwarding.
        family, kind, proto, _, address = addresses[0]
        sock = socket.socket(family, kind, proto)
        try:
            sock.settimeout(self.timeout)
            sock.connect(address)
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


def fetch_pdf(url):
    requested_url = url
    redirects = []
    deadline = time.monotonic() + 120
    for hop in range(6):
        parts = validate_url(url)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('PDF download exceeded its 120 second deadline')
        connection = PublicHTTPS(parts.hostname, timeout=min(20, remaining), context=ssl.create_default_context())
        try:
            path = parts.path or '/'
            if parts.query:
                path += '?' + parts.query
            connection.request('GET', path, headers={'Accept': 'application/pdf',
                'Accept-Encoding': 'identity', 'User-Agent': 'Research-RAG/0.5 PDF acquisition'})
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location or hop == 5:
                    raise ValueError('Missing redirect location or PDF redirect limit exceeded')
                following = urljoin(url, location)
                validate_url(following)
                redirects.append({'url': url, 'status': response.status, 'location': following})
                url = following
                continue
            if response.status != 200:
                raise ValueError(f'PDF download returned HTTP {response.status}; nothing imported')
            length = response.getheader('Content-Length')
            if length and (not length.isdigit() or int(length) > MAX_BYTES):
                raise ValueError('PDF exceeds 50 MiB or has invalid Content-Length')
            if response.getheader('Content-Encoding', 'identity').lower() != 'identity':
                raise ValueError('Compressed HTTP response is unsupported; request an original PDF URL')
            raw = bytearray()
            while True:
                if time.monotonic() > deadline:
                    raise ValueError('PDF download exceeded its 120 second deadline')
                block = response.read1(min(65536, MAX_BYTES + 1 - len(raw)))
                if not block:
                    break
                raw.extend(block)
                if len(raw) > MAX_BYTES:
                    raise ValueError('PDF exceeds 50 MiB')
            if length and len(raw) != int(length):
                raise ValueError('Truncated PDF download')
            if not raw.startswith(b'%PDF-'):
                raise ValueError('Response is not a PDF; HTML or a summary cannot replace the original file')
            try:
                with pymupdf.open(stream=bytes(raw), filetype='pdf') as reader:
                    if reader.is_encrypted or not 1 <= len(reader) <= 1000:
                        raise ValueError('Encrypted, empty or over-1000-page PDFs are unsupported')
                    page_count = len(reader)
            except (RuntimeError, pymupdf.FileDataError) as exc:
                raise ValueError('Downloaded PDF cannot be parsed') from exc
            return bytes(raw), {'requested_url': requested_url, 'final_url': url,
                'redirects': redirects, 'content_type': response.getheader('Content-Type'),
                'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'page_count': page_count}
        finally:
            connection.close()
    raise ValueError('PDF redirect limit exceeded')


class DownloadManagement:
    def download_document(self, url, arxiv_id, expected_revision, key):
        from .store import now
        resolved = download_url(url, arxiv_id)
        def action(db, state):
            raw, receipt = fetch_pdf(resolved)
            filename = 'download-' + receipt['sha256'] + '.pdf'
            target = self.root / 'inbox' / filename
            if target.exists():
                if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest() != receipt['sha256']:
                    raise ValueError('Existing inbox filename has conflicting contents')
            else:
                descriptor, temporary = tempfile.mkstemp(prefix='.download-', dir=target.parent)
                try:
                    with os.fdopen(descriptor, 'wb') as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, target)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            return {**receipt, 'filename': filename, 'arxiv_id': arxiv_id, 'downloaded_at': now(),
                'status': 'downloaded_to_inbox', 'imported_by_this_call': False,
                'next_step': 'preview_inbox_document, then import_document only when import is authorized'}
        return self.mutate('download_document', {'url': url, 'arxiv_id': arxiv_id}, expected_revision, key, action)

    def document_ingestion_status(self, filename):
        from .inbox import preview_inbox_document
        preview = preview_inbox_document(self.root, filename, max_chars=1)
        raw = self.raw_state()
        source = raw['sources'].get(preview['sha256'])
        chunks = [c for c in raw['chunks'].values() if c['source_id'] == preview['sha256']
                  and c['status'] == 'active' and raw['chunk_sets'][c['chunk_set_id']]['active']]
        if source:
            self.verify_source(source)
        receipt = next((r['response']['result'] for r in reversed(list(raw['requests'].values()))
            if r.get('response') and isinstance(r['response'].get('result'), dict)
            and r['response']['result'].get('status') == 'downloaded_to_inbox'
            and r['response']['result'].get('sha256') == preview['sha256']), None)
        return {'filename': preview['filename'], 'sha256': preview['sha256'], 'format': preview['format'],
            'bytes': preview['bytes'], 'page_count': preview['page_count'], 'revision': raw['revision'],
            'status': 'imported' if source else 'inbox_only', 'imported': bool(source),
            'source': self.source_summary(source) if source else None, 'active_chunks': len(chunks),
            'download_receipt': receipt, 'workspace_index': self.search_index_status(),
            'limitation': 'Import and index status do not certify full text extraction, OCR, scientific support or human acceptance.'}
