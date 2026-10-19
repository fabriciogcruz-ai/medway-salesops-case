#!/usr/bin/env python3
"""Export the saved Numbers document into the private CSV watched by demo_local.

Never touches the .numbers document or the received CSV. Failed exports leave the
last valid watched CSV in place. Launch independently of the local HTTP server.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import time

from pipeline import HEADERS, load_b2c, public_b2c_view

ROOT = Path(__file__).resolve().parent
DEFAULT_DOCUMENT = Path.home() / 'Documents' / 'b2c-demo.numbers'
DEFAULT_DESTINATION = ROOT / 'input' / 'b2c-demo.csv'
EXPECTED_ROWS = 4435


def numbers_state() -> tuple[Path, bool]:
    script = ('tell application "Numbers" to return '
              '(POSIX path of (file of front document as alias)) & linefeed & '
              '((modified of front document) as string)')
    result = subprocess.run(['osascript', '-e', script], capture_output=True,
                            text=True, check=True, timeout=20).stdout.strip().splitlines()
    if len(result) != 2:
        raise ValueError('Numbers did not report document path and saved state')
    return Path(result[0]).resolve(), result[1].lower() == 'true'


def export_numbers(path: Path) -> None:
    # The destination does not exist yet: coercing it to an alias would fail.
    script = ('tell application "Numbers" to export front document to '
              '(POSIX file ' + '"' + str(path).replace('\\', '\\\\').replace('"', '\\"') + '") as CSV')
    subprocess.run(['osascript', '-e', script], capture_output=True, text=True,
                   check=True, timeout=90)


def normalize_and_validate(raw_path: Path) -> bytes:
    with raw_path.open(encoding='utf-8-sig', newline='') as source:
        rows = list(csv.reader(source, delimiter=';'))
    if not rows or rows[0] != HEADERS or len(rows) != EXPECTED_ROWS + 1:
        raise ValueError(f'Unexpected Numbers CSV shape: {len(rows)-1} data rows')
    if any(len(row) != len(HEADERS) for row in rows):
        raise ValueError('Unexpected column count in Numbers CSV')
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerows(rows)
    data = output.getvalue().encode('utf-8')
    with tempfile.TemporaryDirectory(prefix='medway-validate-') as tmp:
        sample = Path(tmp) / 'normalized.csv'
        sample.write_bytes(data)
        full, quality = load_b2c(sample)
        public_b2c_view(full, quality)
        if full['total']['count'] != EXPECTED_ROWS:
            raise ValueError('Numbers export row count changed')
    return data


def sync_once(document: Path, destination: Path) -> dict:
    expected = document.resolve(strict=True)
    opened, modified = numbers_state()
    if opened != expected:
        raise ValueError(f'Wrong Numbers document open: {opened} (expected {expected})')
    if modified:
        raise ValueError('Numbers document has unsaved edits; save before exporting')
    before = expected.stat().st_mtime_ns
    with tempfile.TemporaryDirectory(prefix='medway-numbers-') as tmp:
        exported = Path(tmp) / 'export.csv'
        export_numbers(exported)
        if numbers_state() != (expected, False) or expected.stat().st_mtime_ns != before:
            raise ValueError('Numbers document changed during export; retry')
        data = normalize_and_validate(exported)
    digest = hashlib.sha256(data).hexdigest()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() == digest:
        return {'changed': False, 'sha256': digest, 'rows': EXPECTED_ROWS}
    # Atomic hand-off: the CSV watcher can never see a partial file.
    fd, temp_name = tempfile.mkstemp(prefix='.numbers-ready-', suffix='.csv', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {'changed': True, 'sha256': digest, 'rows': EXPECTED_ROWS}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document', type=Path, default=DEFAULT_DOCUMENT)
    parser.add_argument('--destination', type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=float, default=1.0)
    args = parser.parse_args()
    if not args.document.is_file():
        parser.error(f'Numbers document not found: {args.document}')
    last_stamp = None
    last_failure = None
    while True:
        try:
            stamp = (args.document.stat().st_mtime_ns, args.document.stat().st_size)
            if args.once or stamp != last_stamp:
                # A save may still be writing; sync_once verifies stability afterward.
                result = sync_once(args.document, args.destination)
                last_stamp, last_failure = stamp, None
                print(f"[Numbers] {'Updated' if result['changed'] else 'Unchanged'}: {result['rows']} rows; sha256={result['sha256']}", flush=True)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            message = f'{type(exc).__name__}: {exc}'
            if message != last_failure:
                print(f'[Numbers] Not synced (last valid CSV retained): {message}', flush=True)
                last_failure = message
            if args.once:
                raise
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
