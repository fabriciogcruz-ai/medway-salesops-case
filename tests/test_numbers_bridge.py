import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numbers_bridge as bridge
from demo_local import Watcher
from pipeline import load_b2c


class NumbersBridgeTests(unittest.TestCase):
    def test_normalize_actual_numbers_export_and_preserve_baseline(self):
        source = Path('/tmp/medway-numbers-export.csv')
        if not source.exists():
            self.skipTest('Private Numbers export not available')
        data = bridge.normalize_and_validate(source)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'converted.csv'
            path.write_bytes(data)
            result, _ = load_b2c(path)
            self.assertEqual(result['total'], {'count': 4435, 'cents': 4016521974})

    def test_saved_change_invalid_export_and_restore(self):
        original = Path('/tmp/medway-numbers-export.csv')
        if not original.exists():
            self.skipTest('Private Numbers export not available')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            document = root / 'test.numbers'
            document.write_text('saved v1')
            destination = root / 'private.csv'
            exported = root / 'sample.csv'
            exported.write_bytes(original.read_bytes())
            out = root / 'data'

            def fake_export(target):
                target.write_bytes(exported.read_bytes())

            with patch.object(bridge, 'numbers_state', side_effect=lambda: (document.resolve(), False)), \
                 patch.object(bridge, 'export_numbers', side_effect=fake_export):
                self.assertTrue(bridge.sync_once(document, destination)['changed'])
                watcher = Watcher(destination, out)
                self.assertTrue(watcher.update())
                baseline = json.loads((out / 'b2c.json').read_text())
                baseline_bytes = destination.read_bytes()
                self.assertEqual(baseline['total'], {'count': 4435, 'cents': 4016521974})
                with exported.open(encoding='utf-8-sig', newline='') as file:
                    rows = list(csv.reader(file, delimiter=';'))
                rows[1][-1] = 'R$ 106.333,42'
                with exported.open('w', encoding='utf-8', newline='') as file:
                    csv.writer(file, delimiter=';').writerows(rows)
                self.assertTrue(bridge.sync_once(document, destination)['changed'])
                self.assertTrue(watcher.update())
                changed = json.loads((out / 'b2c.json').read_text())
                self.assertEqual(changed['total']['cents'] - baseline['total']['cents'], 10_000_000)
                exported.write_bytes(b'broken export')
                with self.assertRaises(ValueError):
                    bridge.sync_once(document, destination)
                self.assertEqual(changed, json.loads((out / 'b2c.json').read_text()))
                exported.write_bytes(original.read_bytes())
                self.assertTrue(bridge.sync_once(document, destination)['changed'])
                self.assertTrue(watcher.update())
                self.assertEqual(destination.read_bytes(), baseline_bytes)
                self.assertEqual(json.loads((out / 'b2c.json').read_text()), baseline)

    def test_reject_wrong_or_unsaved_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = Path(tmp) / 'expected.numbers'
            document.touch()
            destination = Path(tmp) / 'private.csv'
            for state in ((Path(tmp) / 'other.numbers', False), (document.resolve(), True)):
                with patch.object(bridge, 'numbers_state', return_value=state):
                    with self.assertRaises(ValueError):
                        bridge.sync_once(document, destination)
                self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
