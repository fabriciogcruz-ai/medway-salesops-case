import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'public' / 'data'


class PublishedAggregateTests(unittest.TestCase):
    def test_b2c_reconciles_all_views(self):
        d = json.loads((DATA / 'b2c.json').read_text())
        total = d['total']['cents']
        self.assertEqual(total, 4016521974)
        self.assertEqual(d['total']['count'], 4435)
        for key in ('monthly', 'by_origin', 'by_product', 'monthly_origin', 'monthly_product', 'origin_product'):
            self.assertEqual(sum(r['cents'] for r in d[key]), total, key)
            self.assertEqual(sum(r['count'] for r in d[key]), 4435, key)
        for key in ('daily_coupon', 'by_ambassador', 'by_coupon', 'by_icp', 'by_event_type', 'by_event_region'):
            self.assertNotIn(key, d)
        self.assertEqual(len(d['daily']), 1)
        spike = d['daily'][0]
        self.assertEqual((spike['name'], spike['count'], spike['cents']), ('2025-09-30', 327, 312791719))
        for key in ('daily_origin', 'daily_product'):
            self.assertEqual(sum(r['cents'] for r in d[key]), spike['cents'])
            self.assertTrue(all(r['count'] >= 5 for r in d[key]))
        self.assertTrue(all(set(item) == {'type', 'count'} for item in d['quality']['exceptions']))
        monthly_quality = d['quality']['monthly']
        self.assertEqual(sum(r['negative'] for r in monthly_quality), 1)
        self.assertEqual(sum(r['zero'] for r in monthly_quality), 1)
        self.assertEqual(sum(r['identical_extra_rows_retained'] for r in monthly_quality), 3)
        self.assertEqual(sum(r['negative'] + r['zero'] for r in monthly_quality if '2026-06' <= r['month'] <= '2026-07'), 0)
        yoy = {}
        for year in ('2025', '2026'):
            subset = [r for r in d['monthly'] if year+'-01' <= r['name'] <= year+'-07']
            yoy[year] = (sum(r['count'] for r in subset), sum(r['cents'] for r in subset))
        self.assertEqual(yoy, {'2025': (745, 667939685), '2026': (1760, 1602853495)})

    def test_b2b_reconciles_current_snapshot_without_fake_history(self):
        d = json.loads((DATA / 'b2b-snapshot.json').read_text())
        self.assertEqual(sum(r['count'] for r in d['status']), d['total_contracts'])
        self.assertEqual(next(r['count'] for r in d['status'] if r['name'] == 'ativo'), d['active_contracts'])
        for key in ('status', 'plans', 'regions', 'products', 'plan_region', 'start_year_status'):
            self.assertEqual(sum(r['active_monthly_cents'] for r in d[key]), d['active_monthly_cents'], key)
            self.assertEqual(sum(r['active_licenses'] for r in d[key]), d['active_licenses'], key)
        self.assertEqual(sum(r['count'] for r in d['starts']), d['total_contracts'])
        self.assertIn('Sem data_fim', d['limits'])
        self.assertNotIn('instituicao', json.dumps(d, ensure_ascii=False))


if __name__ == '__main__':
    unittest.main()
