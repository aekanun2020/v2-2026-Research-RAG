"""Separate loopback review surface. MCP clients cannot approve work."""
import html
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse


def esc(value):
    return html.escape(str(value), quote=True)


def render(store, token, workspace_id='default', workspaces=None):
    state = store.read()
    project = state['project'] or {'topic': 'ยังไม่มีหัวข้อ', 'goal': ''}
    body = ['''<!doctype html><html lang="th"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Research RAG — ตรวจหลักฐาน</title><style>
    body{font:16px system-ui;max-width:1000px;margin:32px auto;padding:0 20px;color:#20303d;background:#f5f7f9}
    article{background:white;border:1px solid #c8d2db;padding:20px;margin:20px 0;border-radius:8px}
    pre,blockquote{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}
    label{display:block;margin:12px 0}textarea{width:100%;min-height:70px;box-sizing:border-box}
    input,select,textarea,button{font:inherit;padding:8px;max-width:100%;box-sizing:border-box}
    .issue{color:#922f24}a{color:#075a84}small{display:block}button{cursor:pointer}
    </style><h1>ตรวจหลักฐานงานวิจัย</h1>
    <p>หน้านี้บันทึกการตัดสินใจของนักวิจัย การพบข้อความตรงกับต้นฉบับยังไม่ใช่การรับรองข้อสรุป</p>''',
            f'<h2>{esc(project["topic"])}</h2><p>{esc(project["goal"])}</p>',
            f'<p>ข้อมูลรุ่น {state["revision"]} · แหล่งข้อมูล {len(state["sources"])} · งานที่บันทึก {len(state["artifacts"])}</p>']
    if workspaces:
        body.append('<nav><p>เลือกพื้นที่งาน: '+ ' · '.join(
            '<a href="/?'+esc(urlencode({'token':token,'workspace_id':w['workspace_id']}))+'">'+esc(w['name'])+'</a>'
            for w in workspaces.list()['workspaces'])+'</p></nav>')
    body.append('<p>Workspace: '+esc(workspace_id)+'</p>')
    for aid, artifact in state['artifacts'].items():
        view = store.artifact_view(artifact, state)
        body.append(f'<article id="{esc(aid)}"><h2>{esc(artifact["title"])}</h2><p>{esc(artifact["stage"])} · ฉบับ {artifact["version"]} · {esc(view["effective_status"])}</p>')
        if artifact['stage'] == 'manuscript':
            body.append(f'<p>รหัสต้นฉบับ: {esc(aid)}</p>')
        for issue in view['issues']:
            body.append(f'<p class="issue">{esc(issue)}</p>')
        for block in artifact['blocks']:
            body.append(f'<h3>{esc(block["section"])}</h3><small>ที่มาของข้อความ: {esc(block["basis"])}</small><pre>{esc(block["text"])}</pre>')
            for citation in block['citations']:
                try:
                    page = store.page(citation['source_id'], citation['page_index'], state)
                    store.citation(citation, state)
                    url = '/source?' + urlencode({'token': token, 'id': citation['source_id'], 'workspace_id': workspace_id})
                    body.append(f'<details><summary>หลักฐาน: {esc(page["title"])} · หน้าไฟล์ {page["page_index"]+1} · {esc(citation["relation"])}</summary><blockquote>{esc(citation["quote"])}</blockquote><a href="{esc(url)}" target="_blank" rel="noreferrer">เปิดไฟล์ต้นฉบับ</a><pre>{esc(page["text"])}</pre></details>')
                except (ValueError, OSError) as exc:
                    body.append(f'<p class="issue">{esc(exc)}</p>')
        body.append('<h3>ข้อจำกัด</h3><ul>'+''.join(f'<li>{esc(x)}</li>' for x in artifact['limitations'])+'</ul>')
        if artifact['dependencies']:
            body.append('<p>อ้างงานก่อนหน้า: '+', '.join(f'<a href="#{esc(r["id"])}">{esc(state["artifacts"][r["id"]]["title"])}, ฉบับ {r["version"]}</a>' for r in artifact['dependencies'])+'</p>')
        if artifact['review']:
            review = artifact['review']
            body.append(f'<p>ผลตรวจ: {esc(review["reviewer"])} · {esc(review["verdict"])} · {esc(review["rationale"])}</p>')
        body.append(f'''<form action="/review" method="post">
        <input type="hidden" name="token" value="{esc(token)}">
        <input type="hidden" name="workspace_id" value="{esc(workspace_id)}">
        <input type="hidden" name="revision" value="{state['revision']}">
        <input type="hidden" name="artifact_id" value="{esc(aid)}">
        <label>ชื่อผู้ตรวจ <input required name="reviewer" maxlength="300"></label>
        <label>ผลตรวจ <select name="verdict"><option value="unresolved">ยังสรุปไม่ได้</option><option value="accepted">ตรวจรับ</option><option value="rejected">ปฏิเสธ</option></select></label>
        <label>เหตุผล <textarea required name="rationale" maxlength="5000"></textarea></label>
        <button>บันทึกการตัดสินใจ</button></form></article>''')
    body.append('</html>')
    return ''.join(body)


def serve_review(store, port=0, host='127.0.0.1', workspaces=None):
    token = secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body, media='text/html; charset=utf-8'):
            data = body if isinstance(body, bytes) else body.encode('utf-8')
            self.send_response(status)
            for name, value in [('Content-Type', media), ('Content-Length', str(len(data))),
                                ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'),
                                ('Referrer-Policy', 'same-origin'),
                                ('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")]:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            if not self.valid_host() or not secrets.compare_digest(query.get('token', [''])[0], token):
                return self.reply(403, 'Forbidden')
            try:
                workspace_id = query.get('workspace_id', ['default'])[0]
                active = workspaces.context(workspace_id)[0] if workspaces else store
                if urlparse(self.path).path == '/source':
                    source = active.read()['sources'].get(query.get('id', [''])[0])
                    if not source:
                        return self.reply(404, 'Unknown source')
                    original = active.verify_source(source)
                    media = 'application/pdf' if original.suffix == '.pdf' else 'text/plain; charset=utf-8'
                    return self.reply(200, original.read_bytes(), media)
                if urlparse(self.path).path != '/':
                    return self.reply(404, 'Not found')
                return self.reply(200, render(active, token, workspace_id, workspaces))
            except (ValueError, OSError) as exc:
                return self.reply(409, esc(exc))

        def do_POST(self):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if not self.valid_host() or self.headers.get('Origin') != origin:
                return self.reply(403, 'Foreign or missing Origin')
            if self.path != '/review':
                return self.reply(404, 'Not found')
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 32000:
                    return self.reply(413, 'Invalid request size')
                fields = parse_qs(self.rfile.read(length).decode('utf-8'), keep_blank_values=True)
                if not secrets.compare_digest(fields.get('token', [''])[0], token):
                    return self.reply(403, 'Forbidden')
                workspace_id = fields.get('workspace_id', ['default'])[0]
                active = workspaces.context(workspace_id)[0] if workspaces else store
                active.review(fields['artifact_id'][0], fields['verdict'][0], fields['reviewer'][0], fields['rationale'][0],
                             int(fields['revision'][0]), secrets.token_hex(16))
            except (ValueError, OSError, KeyError) as exc:
                return self.reply(409, esc(exc))
            self.send_response(303)
            self.send_header('Location', '/?'+urlencode({'token': token, 'workspace_id': workspace_id}))
            self.end_headers()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f'http://127.0.0.1:{server.server_port}/?'+urlencode({'token': token}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
