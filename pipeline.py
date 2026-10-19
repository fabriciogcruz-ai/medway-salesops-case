#!/usr/bin/env python3
"""Medway SalesOps: reproducible CSV/API ingestion and aggregate export."""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / 'input' / 'b2c-original.csv'
PUBLIC = ROOT / 'public' / 'data'
API_URL = 'http://yeh3066gfbw2sw3ywghufr90.187.77.56.193.sslip.io/contratos'
HEADERS = ['data_venda', 'quarter', 'origem', 'embaixador', 'tipo_evento', 'regiao_evento', 'produto', 'icp_comprador', 'cupom', 'valor_pago']


def parse_date(raw: str) -> tuple[dt.date, str]:
    for fmt, label in (('%Y-%m-%d', 'ISO'), ('%d/%m/%Y', 'BR')):
        try:
            return dt.datetime.strptime(raw.strip(), fmt).date(), label
        except ValueError:
            pass
    raise ValueError(f'data inválida: {raw!r}')


def parse_money(raw: str) -> tuple[Decimal, str]:
    s = raw.strip().replace('R$', '').replace(' ', '').replace('\u00a0', '')
    if re.fullmatch(r'-?\d{1,3}(?:\.\d{3})+,\d{2}', s):
        value, label = s.replace('.', '').replace(',', '.'), 'BR'
    elif re.fullmatch(r'-?\d+,\d{2}', s):
        value, label = s.replace(',', '.'), 'BR'
    elif re.fullmatch(r'-?\d+\.\d{2}', s):
        value, label = s, 'PONTO'
    elif re.fullmatch(r'-?\d+', s):
        value, label = s, 'INTEIRO'
    else:
        raise ValueError(f'moeda inválida: {raw!r}')
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError(f'moeda não finita: {raw!r}')
    return result, label


def cents(value: Decimal) -> int:
    return int(value * 100)


def summarize(items: list[dict], dimension: str, measure: str = 'cents') -> list[dict]:
    grouped = collections.defaultdict(lambda: [0, 0])
    for row in items:
        key = row[dimension]
        grouped[key][0] += 1
        grouped[key][1] += row[measure]
    return [{'name': k, 'count': n, 'cents': total} for k, (n, total) in sorted(grouped.items())]


def load_b2c(path: Path) -> tuple[dict, dict]:
    data = path.read_bytes()
    records = []
    formats = collections.Counter()
    date_formats = collections.Counter()
    exceptions = []
    signatures = collections.Counter()
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != HEADERS:
            raise ValueError(f'cabeçalho inesperado: {reader.fieldnames}')
        for line, raw in enumerate(reader, 2):
            if None in raw or any(v is None for v in raw.values()):
                raise ValueError(f'linha CSV malformada: {line}')
            date, date_label = parse_date(raw['data_venda'])
            amount, money_label = parse_money(raw['valor_pago'])
            if raw['quarter'] != 'Q' + str((date.month - 1) // 3 + 1):
                raise ValueError(f'quarter não corresponde à data na linha {line}')
            formats[money_label] += 1
            date_formats[date_label] += 1
            norm = {k: (v.strip() if v is not None else '') for k, v in raw.items()}
            signatures[tuple(norm.values())] += 1
            region = norm['regiao_evento'].upper() or 'Não aplicável'
            record = {
                'date': date.isoformat(), 'month': date.strftime('%Y-%m'),
                'quarter': f'{date.year}-Q{(date.month - 1) // 3 + 1}',
                'origem': norm['origem'], 'produto': norm['produto'],
                'icp': norm['icp_comprador'], 'cupom': norm['cupom'],
                'embaixador': norm['embaixador'] or 'Não aplicável',
                'tipo_evento': norm['tipo_evento'] or 'Não aplicável',
                'regiao_evento': region,
                'cents': cents(amount),
            }
            if amount <= 0:
                exceptions.append({'line': line, 'type': 'negative' if amount < 0 else 'zero', 'cents': cents(amount), 'date': date.isoformat()})
            records.append(record)
    if not records:
        raise ValueError('CSV vazio')
    months = summarize(records, 'month')
    all_total = sum(r['cents'] for r in records)
    monthly_origin = collections.defaultdict(lambda: [0, 0])
    monthly_product = collections.defaultdict(lambda: [0, 0])
    daily_origin = collections.defaultdict(lambda: [0, 0])
    daily_product = collections.defaultdict(lambda: [0, 0])
    daily_coupon = collections.defaultdict(lambda: [0, 0])
    origin_product = collections.defaultdict(lambda: [0, 0])
    for r in records:
        for key, target in (
            ((r['month'], r['origem']), monthly_origin),
            ((r['month'], r['produto']), monthly_product),
            ((r['date'], r['origem']), daily_origin),
            ((r['date'], r['produto']), daily_product),
            ((r['date'], r['cupom']), daily_coupon),
            ((r['origem'], r['produto']), origin_product),
        ):
            target[key][0] += 1
            target[key][1] += r['cents']
    duplicate_pairs = sum(n - 1 for n in signatures.values() if n > 1)
    monthly_quality = collections.defaultdict(lambda: {'negative': 0, 'zero': 0, 'identical_extra_rows_retained': 0})
    for item in exceptions:
        monthly_quality[item['date'][:7]][item['type']] += 1
    for signature, count in signatures.items():
        if count > 1:
            month = parse_date(signature[0])[0].strftime('%Y-%m')
            monthly_quality[month]['identical_extra_rows_retained'] += count - 1
    quality = {
        'rows': len(records), 'csv_sha256': hashlib.sha256(data).hexdigest(),
        'money_formats': dict(formats), 'date_formats': dict(date_formats),
        'identical_extra_rows_retained': duplicate_pairs, 'exceptions': exceptions,
        'monthly': [{'month': month, **values} for month, values in sorted(monthly_quality.items())],
        'note': 'Linhas idênticas preservadas: ausência de ID transacional impede deduplicação segura.'
    }
    result = {
        'source': 'CSV entregue para o case; snapshot não conectado à planilha de origem',
        'period': {'first': min(r['date'] for r in records), 'last': max(r['date'] for r in records)},
        'total': {'count': len(records), 'cents': all_total},
        'monthly': months, 'daily': summarize(records, 'date'),
        'by_origin': summarize(records, 'origem'), 'by_product': summarize(records, 'produto'),
        'by_icp': summarize(records, 'icp'), 'by_coupon': summarize(records, 'cupom'),
        'by_ambassador': summarize(records, 'embaixador'),
        'by_event_type': summarize(records, 'tipo_evento'),
        'by_event_region': summarize(records, 'regiao_evento'),
        'monthly_origin': [{'month': m, 'name': n, 'count': v[0], 'cents': v[1]} for (m, n), v in sorted(monthly_origin.items())],
        'monthly_product': [{'month': m, 'name': n, 'count': v[0], 'cents': v[1]} for (m, n), v in sorted(monthly_product.items())],
        'daily_origin': [{'date': d, 'name': n, 'count': v[0], 'cents': v[1]} for (d, n), v in sorted(daily_origin.items())],
        'daily_product': [{'date': d, 'name': n, 'count': v[0], 'cents': v[1]} for (d, n), v in sorted(daily_product.items())],
        'daily_coupon': [{'date': d, 'name': n, 'count': v[0], 'cents': v[1]} for (d, n), v in sorted(daily_coupon.items())],
        'origin_product': [{'origin': o, 'product': p, 'count': v[0], 'cents': v[1]} for (o, p), v in sorted(origin_product.items())],
        'quality': quality,
    }
    assert sum(x['cents'] for x in months) == all_total
    assert sum(x['count'] for x in result['by_origin']) == len(records)
    assert sum(x['cents'] for x in result['by_product']) == all_total
    return result, quality


def public_b2c_view(result: dict, quality: dict) -> tuple[dict, dict]:
    """Publish only the aggregates the dashboard uses; never publish single-sale cells."""
    anchor = '2025-09-30'  # Named case anomaly, not a general transaction-level export.
    safe = {key: result[key] for key in (
        'source', 'period', 'total', 'monthly', 'by_origin', 'by_product',
        'monthly_origin', 'monthly_product', 'origin_product',
    )}
    safe['daily'] = [row for row in result['daily'] if row['name'] == anchor]
    safe['daily_origin'] = [row for row in result['daily_origin'] if row['date'] == anchor]
    safe['daily_product'] = [row for row in result['daily_product'] if row['date'] == anchor]
    if len(safe['daily']) != 1 or any(row['count'] < 5 for key in ('daily_origin', 'daily_product') for row in safe[key]):
        raise ValueError('anomaly slice is absent or too granular for public release')
    exceptions = collections.Counter(item['type'] for item in quality['exceptions'])
    safe_quality = {key: value for key, value in quality.items() if key != 'exceptions'}
    safe_quality['exceptions'] = [{'type': key, 'count': count} for key, count in sorted(exceptions.items())]
    safe['quality'] = safe_quality
    return safe, safe_quality


def fetch_b2b(token: str, base: str = API_URL) -> list[dict]:
    if not token:
        raise ValueError('MEDWAY_B2B_TOKEN não definido')
    seen = set()
    rows = []
    total = None
    offset = 0
    while total is None or offset < total:
        url = base + '?' + urllib.parse.urlencode({'limit': 100, 'offset': offset})
        request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/json'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=12) as response:
                    if response.status != 200:
                        raise ValueError(f'API B2B HTTP {response.status}')
                    payload = json.load(response)
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 2:
                    raise RuntimeError(f'API B2B indisponível: {type(exc).__name__}') from exc
                time.sleep(0.5 * (attempt + 1))
        if not isinstance(payload, dict) or not isinstance(payload.get('contratos'), list) or not isinstance(payload.get('total'), int):
            raise ValueError('formato da API B2B inesperado')
        if total is None:
            total = payload['total']
        elif total != payload['total']:
            raise ValueError('total da API mudou durante paginação; refazer coleta')
        batch = payload['contratos']
        if not batch and offset < total:
            raise ValueError('API retornou página vazia antes do total')
        for row in batch:
            key = row['id_contrato']
            if key in seen:
                raise ValueError(f'ID B2B repetido na paginação: {key}')
            seen.add(key)
            rows.append(row)
        offset += len(batch)
        if len(rows) > total:
            raise ValueError('API retornou mais registros do que total informado')
    if len(rows) != total:
        raise ValueError('contagem B2B divergente')
    return rows


def summarize_b2b(rows: list[dict], fetched_at: str) -> dict:
    status = collections.defaultdict(lambda: [0, 0, 0])
    plan = collections.defaultdict(lambda: [0, 0, 0])
    region = collections.defaultdict(lambda: [0, 0, 0])
    product = collections.defaultdict(lambda: [0, 0, 0])
    starts = collections.Counter()
    plan_region = collections.defaultdict(lambda: [0, 0, 0])
    start_year_status = collections.defaultdict(lambda: [0, 0, 0])
    ids = set()
    for row in rows:
        required = ('id_contrato', 'status', 'plano', 'regiao', 'produto', 'num_licencas', 'valor_mensal', 'data_inicio')
        if any(field not in row for field in required):
            raise ValueError('contrato sem campos obrigatórios')
        if row['id_contrato'] in ids:
            raise ValueError('contrato duplicado')
        ids.add(row['id_contrato'])
        date, _ = parse_date(str(row['data_inicio']))
        amount = cents(Decimal(str(row['valor_mensal'])))
        licences = int(row['num_licencas'])
        if amount < 0 or licences < 0:
            raise ValueError('valor/licenças negativos em B2B')
        starts[date.strftime('%Y-%m')] += 1
        for key, target in (((row['plano'], str(row['regiao']).upper()), plan_region), ((str(date.year), row['status']), start_year_status)):
            target[key][0] += 1
            if row['status'] == 'ativo':
                target[key][1] += amount
                target[key][2] += licences
        for dimension, target in (('status', status), ('plano', plan), ('regiao', region), ('produto', product)):
            key = str(row[dimension]).upper() if dimension == 'regiao' else str(row[dimension])
            target[key][0] += 1
            if row['status'] == 'ativo':
                target[key][1] += amount
                target[key][2] += licences
    def pack(groups):
        return [{'name': k, 'count': v[0], 'active_monthly_cents': v[1], 'active_licenses': v[2]} for k, v in sorted(groups.items())]
    active_mrr = sum(cents(Decimal(str(r['valor_mensal']))) for r in rows if r['status'] == 'ativo')
    active_licenses = sum(int(r['num_licencas']) for r in rows if r['status'] == 'ativo')
    return {
        'source': 'API de contratos B2B (snapshot de status no momento da coleta)',
        'fetched_at': fetched_at, 'total_contracts': len(rows),
        'active_contracts': status['ativo'][0], 'active_monthly_cents': active_mrr,
        'active_licenses': active_licenses,
        'status': pack(status), 'plans': pack(plan), 'regions': pack(region), 'products': pack(product),
        'plan_region': [{'plan': p, 'region': r, 'count': v[0], 'active_monthly_cents': v[1], 'active_licenses': v[2]} for (p, r), v in sorted(plan_region.items())],
        'start_year_status': [{'year': y, 'status': s, 'count': v[0], 'active_monthly_cents': v[1], 'active_licenses': v[2]} for (y, s), v in sorted(start_year_status.items())],
        'starts': [{'month': k, 'count': v} for k, v in sorted(starts.items())],
        'limits': 'Sem data_fim, histórico de status, cobrança ou recebimento. Inícios são coortes de assinatura, não MRR histórico.',
    }


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=CSV_PATH)
    parser.add_argument('--b2b-json', type=Path, help='JSON bruto da API já coletado, para teste/reprocessamento offline')
    parser.add_argument('--b2c-only', action='store_true', help='Não atualizar B2B; mantém snapshot anterior')
    parser.add_argument('--b2b-only', action='store_true', help='Atualiza apenas snapshot B2B; ideal para agendamento sem CSV')
    parser.add_argument('--out', type=Path, default=PUBLIC)
    args = parser.parse_args()
    if args.b2c_only and args.b2b_only:
        parser.error('--b2c-only e --b2b-only são mutuamente exclusivos')
    b2c = quality = None
    if not args.b2b_only:
        b2c, quality = load_b2c(args.csv)
    # Prepare all outputs before writing so a failure never replaces a valid previous snapshot.
    b2b = None
    if not args.b2c_only:
        if args.b2b_json:
            payload = json.loads(args.b2b_json.read_text(encoding='utf-8'))
            rows = payload['contratos'] if isinstance(payload, dict) else payload
        else:
            rows = fetch_b2b(os.environ.get('MEDWAY_B2B_TOKEN', ''))
        b2b = summarize_b2b(rows, dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'))
    if b2c is not None:
        public_b2c, public_quality = public_b2c_view(b2c, quality)
        atomic_json(args.out / 'b2c.json', public_b2c)
        atomic_json(args.out / 'quality.json', public_quality)
    if b2b is not None:
        atomic_json(args.out / 'b2b-snapshot.json', b2b)
    print(json.dumps({'b2c_rows': b2c['total']['count'] if b2c else 'unchanged', 'b2c_cents': b2c['total']['cents'] if b2c else 'unchanged', 'b2b_contracts': b2b['total_contracts'] if b2b else 'unchanged', 'b2b_active_monthly_cents': b2b['active_monthly_cents'] if b2b else 'unchanged'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
