import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import CSV_PATH, load_b2c, parse_date, parse_money, summarize_b2b, atomic_json, public_b2c_view


class ParsingTests(unittest.TestCase):
    def test_money_formats(self):
        self.assertEqual(parse_money('R$ 6.333,42'), (Decimal('6333.42'), 'BR'))
        self.assertEqual(parse_money('14174.34'), (Decimal('14174.34'), 'PONTO'))
        self.assertEqual(parse_money('-R$ 1.750,00'), (Decimal('-1750.00'), 'BR'))
        self.assertEqual(parse_money('R$ 0,00'), (Decimal('0.00'), 'BR'))
        with self.assertRaises(ValueError): parse_money('R$ 6.333.42')

    def test_date_formats(self):
        self.assertEqual(parse_date('01/02/2026')[0].isoformat(), '2026-02-01')
        self.assertEqual(parse_date('2026-02-01')[0].isoformat(), '2026-02-01')
        with self.assertRaises(ValueError): parse_date('2026-13-01')

    @unittest.skipUnless(CSV_PATH.exists(), 'CSV bruto não publicado; testes unitários seguem disponíveis')
    def test_real_csv_reconciles(self):
        result, quality = load_b2c(CSV_PATH)
        self.assertEqual(result['total'], {'count': 4435, 'cents': 4016521974})
        self.assertEqual(quality['money_formats']['PONTO'], 116)
        self.assertEqual(quality['date_formats']['BR'], 746)
        self.assertEqual(quality['identical_extra_rows_retained'], 3)
        self.assertEqual(len(quality['exceptions']), 2)
        self.assertEqual(sum(x['negative'] for x in quality['monthly']), 1)
        self.assertEqual(sum(x['zero'] for x in quality['monthly']), 1)
        self.assertEqual(sum(x['identical_extra_rows_retained'] for x in quality['monthly']), 3)
        self.assertEqual(sum(x['cents'] for x in result['monthly']), result['total']['cents'])
        self.assertEqual(sum(x['cents'] for x in result['monthly_origin']), result['total']['cents'])
        self.assertEqual(sum(x['cents'] for x in result['monthly_product']), result['total']['cents'])
        self.assertEqual(sum(x['cents'] for x in result['daily_origin']), result['total']['cents'])
        self.assertEqual(sum(x['cents'] for x in result['daily_product']), result['total']['cents'])
        self.assertEqual(sum(x['cents'] for x in result['daily_coupon']), result['total']['cents'])
        self.assertEqual(sum(x['cents'] for x in result['origin_product']), result['total']['cents'])
        day = next(x for x in result['daily'] if x['name'] == '2025-09-30')
        self.assertEqual((day['count'], day['cents']), (327, 312791719))

    @unittest.skipUnless(CSV_PATH.exists(), 'CSV bruto não publicado; teste de minimização requer fonte local')
    def test_public_view_minimizes_granularity(self):
        full, quality = load_b2c(CSV_PATH)
        safe, safe_quality = public_b2c_view(full, quality)
        self.assertEqual(safe['total'], full['total'])
        self.assertEqual(len(safe['daily']), 1)
        self.assertEqual(sum(x['cents'] for x in safe['daily_origin']), safe['daily'][0]['cents'])
        self.assertNotIn('daily_coupon', safe)
        self.assertNotIn('by_ambassador', safe)
        self.assertTrue(all(set(x) == {'type', 'count'} for x in safe_quality['exceptions']))
        self.assertTrue(all(set(x) == {'month','negative','zero','identical_extra_rows_retained'} for x in safe_quality['monthly']))
        self.assertNotIn('cents', json.dumps(safe_quality['monthly']))

    def test_b2b_snapshot_semantics(self):
        rows = [
            {'id_contrato':'A','status':'ativo','plano':'Pro','regiao':'sp','produto':'R1','num_licencas':2,'valor_mensal':100.50,'data_inicio':'2025-01-01'},
            {'id_contrato':'B','status':'churn','plano':'Pro','regiao':'sp','produto':'R1','num_licencas':3,'valor_mensal':200,'data_inicio':'2025-02-01'},
        ]
        out = summarize_b2b(rows,'2026-01-01T00:00:00Z')
        self.assertEqual(out['total_contracts'], 2)
        self.assertEqual(out['active_monthly_cents'], 10050)
        self.assertEqual(out['active_licenses'], 2)
        self.assertEqual(out['starts'], [{'month':'2025-01','count':1},{'month':'2025-02','count':1}])
        self.assertEqual(sum(x['active_monthly_cents'] for x in out['plan_region']), out['active_monthly_cents'])
        self.assertEqual(sum(x['active_monthly_cents'] for x in out['start_year_status']), out['active_monthly_cents'])
        rows[1]['id_contrato']='A'
        with self.assertRaises(ValueError): summarize_b2b(rows,'2026-01-01T00:00:00Z')

    def test_atomic_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'nested'/'data.json'
            atomic_json(path,{'cents':100,'label':'João'})
            self.assertEqual(json.loads(path.read_text()),{'cents':100,'label':'João'})
            self.assertFalse(path.with_suffix('.json.tmp').exists())


if __name__ == '__main__': unittest.main()
