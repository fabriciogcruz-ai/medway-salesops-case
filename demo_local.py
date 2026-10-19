#!/usr/bin/env python3
"""Local Medway demo: watch a private CSV and serve the real dashboard.

No raw CSV or Bearer token is published. The original received CSV is never edited.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from http.server import ThreadingHTTPServer

from dev_server import Handler
from pipeline import ROOT, PUBLIC, atomic_json, load_b2c, public_b2c_view

DEFAULT_CSV = ROOT / 'input' / 'b2c-demo.csv'
DEFAULT_TOKEN_FILE = ROOT / 'input' / 'b2b-token.txt'


def process_csv(source: Path, out: Path = PUBLIC) -> dict:
    """Validate everything before replacing any browser-visible aggregate."""
    full, quality = load_b2c(source)
    safe, safe_quality = public_b2c_view(full, quality)
    # CSV may have changed between read_bytes and DictReader during a save.
    if hashlib.sha256(source.read_bytes()).hexdigest() != quality['csv_sha256']:
        raise ValueError('CSV changed during processing; retry after save')
    atomic_json(out / 'b2c.json', safe)
    atomic_json(out / 'quality.json', safe_quality)
    return {'sha256': quality['csv_sha256'], 'rows': safe['total']['count'], 'cents': safe['total']['cents']}


class Watcher(threading.Thread):
    def __init__(self, source: Path, out: Path, interval: float = 0.5):
        super().__init__(daemon=True)
        self.source, self.out, self.interval = source, out, interval
        self.stop_event = threading.Event()
        self.last_sha = None
        self.failed_sha = None
        self.updated_at = None
        self.last_error = None

    def update(self) -> bool:
        digest = None
        try:
            raw = self.source.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest == self.last_sha:
                if self.last_error:
                    self.last_error, self.failed_sha = None, None
                    print('[B2C] Arquivo válido restaurado; mantendo agregado original', flush=True)
                return False
            if digest == self.failed_sha:
                return False
            result = process_csv(self.source, self.out)
            self.last_sha, self.failed_sha = result['sha256'], None
            self.updated_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
            self.last_error = None
            print(f"[B2C] CSV processado: {result['rows']} linhas, {result['cents']} centavos; dashboard local atualizado", flush=True)
            return True
        except (OSError, ValueError, KeyError) as exc:
            if digest is not None and digest != self.failed_sha:
                self.failed_sha = digest
                print(f'[B2C] Arquivo inválido; mantendo último agregado válido ({type(exc).__name__}: {exc})', flush=True)
            self.last_error = type(exc).__name__
            return False

    def run(self) -> None:
        signature = None
        stable_since = 0.0
        while not self.stop_event.wait(self.interval):
            try:
                stat = self.source.stat()
                current = (stat.st_mtime_ns, stat.st_size)
            except OSError:
                continue
            if current != signature:
                signature, stable_since = current, time.monotonic()
                continue
            if time.monotonic() - stable_since >= 0.7:
                self.update()


class DemoHandler(Handler):
    watcher: Watcher | None = None

    def do_GET(self):
        if self.path.split('?')[0] != '/api/local-status':
            return super().do_GET()
        watcher = self.watcher
        if watcher is None:
            self.send_error(503)
            return
        data = {
            'mode': 'local-demo', 'source': watcher.source.name,
            'sha256': watcher.last_sha, 'updated_at': watcher.updated_at,
            'error': watcher.last_error,
        }
        body = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=DEFAULT_CSV, help='Arquivo CSV local editável; o original recebido não é alterado')
    parser.add_argument('--token-file', type=Path, default=DEFAULT_TOKEN_FILE, help='Token B2B privado fora do Git')
    parser.add_argument('--port', type=int, default=8791)
    parser.add_argument('--once', action='store_true', help='Processa CSV uma vez, sem iniciar o servidor')
    parser.add_argument('--out', type=Path, default=PUBLIC, help='Pasta de agregados (somente com --once)')
    args = parser.parse_args()
    if not args.csv.is_file():
        parser.error(f'CSV não encontrado: {args.csv}')
    if not args.once and args.out != PUBLIC:
        parser.error('--out só pode ser usado com --once')
    watcher = Watcher(args.csv, args.out)
    if not watcher.update():
        parser.error('CSV inicial inválido; nenhuma alteração foi publicada')
    if args.once:
        return
    if args.token_file.is_file() and not os.environ.get('MEDWAY_B2B_TOKEN'):
        token = args.token_file.read_text(encoding='utf-8').strip()
        if not token:
            parser.error('Arquivo do token B2B vazio')
        os.environ['MEDWAY_B2B_TOKEN'] = token
    print(f'[B2B] Token servidor: {"configurado" if os.environ.get("MEDWAY_B2B_TOKEN") else "ausente (snapshot rotulado)"}', flush=True)
    DemoHandler.watcher = watcher
    server = ThreadingHTTPServer(('127.0.0.1', args.port), DemoHandler)
    watcher.start()
    print(f'Prévia local: http://127.0.0.1:{args.port}/ | CSV observado: {args.csv}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop_event.set()
        server.server_close()


if __name__ == '__main__':
    main()
