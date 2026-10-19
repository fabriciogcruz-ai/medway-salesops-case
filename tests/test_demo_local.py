import csv
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo_local import Watcher
from pipeline import HEADERS


class LocalDemoTests(unittest.TestCase):
    def test_valid_invalid_and_restored_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'local.csv'
            out = root / 'public-data'
            rows = [
                {
                    'data_venda': '2025-09-30', 'quarter': 'Q3', 'origem': 'Orgânico',
                    'embaixador': '', 'tipo_evento': '', 'regiao_evento': '',
                    'produto': 'Extensivo R1', 'icp_comprador': 'DEMO',
                    'cupom': f'DEMO_{n}', 'valor_pago': 'R$ 10,00',
                }
                for n in range(5)
            ]

            def save(values):
                with source.open('w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS)
                    writer.writeheader()
                    writer.writerows(values)

            save(rows)
            original = source.read_bytes()
            watcher = Watcher(source, out)
            self.assertTrue(watcher.update())
            baseline = json.loads((out / 'b2c.json').read_text())
            self.assertEqual(baseline['total'], {'count': 5, 'cents': 5000})
            self.assertFalse(watcher.update())

            malformed = [dict(row) for row in rows]
            malformed[0]['quarter'] = 'Q1'
            save(malformed)
            self.assertFalse(watcher.update())
            self.assertEqual(json.loads((out / 'b2c.json').read_text()), baseline)
            self.assertEqual(watcher.last_error, 'ValueError')

            source.write_bytes(original)
            self.assertFalse(watcher.update())
            self.assertIsNone(watcher.last_error)
            self.assertEqual(json.loads((out / 'b2c.json').read_text()), baseline)

            rows.append(dict(rows[0], cupom='DEMO_6'))
            save(rows)
            self.assertTrue(watcher.update())
            updated = json.loads((out / 'b2c.json').read_text())
            self.assertEqual(updated['total'], {'count': 6, 'cents': 6000})
            self.assertNotEqual(updated['quality']['csv_sha256'], baseline['quality']['csv_sha256'])


if __name__ == '__main__':
    unittest.main()
