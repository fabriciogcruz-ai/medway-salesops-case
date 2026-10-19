#!/usr/bin/env python3
"""Local preview with the same /api/b2b route as Vercel; requires MEDWAY_B2B_TOKEN."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import datetime as dt
import json
import os
from pathlib import Path
from pipeline import ROOT, fetch_b2b, summarize_b2b

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'public'), **kwargs)

    def do_GET(self):
        if self.path.split('?')[0] != '/api/b2b':
            return super().do_GET()
        try:
            data = summarize_b2b(fetch_b2b(os.environ.get('MEDWAY_B2B_TOKEN', '')), dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'))
            status = 200
        except Exception as exc:
            print(f'B2B indisponível: {type(exc).__name__}')
            data, status = {'error':'Fonte B2B indisponível'}, 503
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', int(os.getenv('PORT','8777'))), Handler).serve_forever()
