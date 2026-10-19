// Server-side only. Never expose the Bearer token or contract-level data to the browser.
const BASE = process.env.MEDWAY_B2B_URL || 'http://yeh3066gfbw2sw3ywghufr90.187.77.56.193.sslip.io/contratos';

async function collect(token, fetchImpl = fetch) {
  if (!token) throw new Error('MEDWAY_B2B_TOKEN indisponível');
  let offset = 0, total = null;
  const rows = [], ids = new Set();
  while (total === null || offset < total) {
    const url = new URL(BASE);
    url.searchParams.set('limit', '100');
    url.searchParams.set('offset', String(offset));
    const response = await fetchImpl(url, {
      headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
      signal: AbortSignal.timeout(12000),
    });
    if (!response.ok) throw new Error(`API B2B respondeu ${response.status}`);
    const payload = await response.json();
    if (!payload || !Number.isInteger(payload.total) || !Array.isArray(payload.contratos)) throw new Error('Formato de API inesperado');
    if (total === null) total = payload.total;
    if (total !== payload.total) throw new Error('Total mudou durante paginação');
    if (payload.contratos.length === 0 && offset < total) throw new Error('Página vazia antes do total');
    for (const row of payload.contratos) {
      if (!row.id_contrato || ids.has(row.id_contrato)) throw new Error('ID duplicado/inválido');
      ids.add(row.id_contrato);
      rows.push(row);
    }
    offset += payload.contratos.length;
    if (offset > total) throw new Error('Mais contratos que total informado');
  }
  if (rows.length !== total) throw new Error('Contagem divergente');
  return rows;
}

function summarize(rows, now = new Date()) {
  const dimensions = { status: {}, plans: {}, regions: {}, products: {} };
  const starts = {}, planRegion = {}, startYearStatus = {};
  let activeContracts = 0, activeMonthlyCents = 0, activeLicenses = 0;
  for (const row of rows) {
    for (const key of ['status', 'plano', 'regiao', 'produto', 'num_licencas', 'valor_mensal', 'data_inicio']) {
      if (row[key] === undefined || row[key] === null) throw new Error(`Campo ausente: ${key}`);
    }
    const amount = Math.round(Number(row.valor_mensal) * 100);
    const licences = Number(row.num_licencas);
    if (!Number.isSafeInteger(amount) || amount < 0 || !Number.isSafeInteger(licences) || licences < 0) throw new Error('Valor inválido');
    const month = String(row.data_inicio).slice(0, 7);
    if (!/^\d{4}-\d{2}$/.test(month)) throw new Error('Data de início inválida');
    starts[month] = (starts[month] || 0) + 1;
    const active = row.status === 'ativo';
    const co = [{bucket:planRegion,key:`${row.plano}|||${String(row.regiao).toUpperCase()}`}, {bucket:startYearStatus,key:`${month.slice(0,4)}|||${row.status}`}];
    for(const {bucket,key} of co){const item=bucket[key] ||= {count:0,active_monthly_cents:0,active_licenses:0};item.count++;if(active){item.active_monthly_cents+=amount;item.active_licenses+=licences}}
    if (active) { activeContracts++; activeMonthlyCents += amount; activeLicenses += licences; }
    const labels = { status: row.status, plans: row.plano, regions: String(row.regiao).toUpperCase(), products: row.produto };
    for (const [dimension, name] of Object.entries(labels)) {
      const item = dimensions[dimension][name] ||= { name, count: 0, active_monthly_cents: 0, active_licenses: 0 };
      item.count++;
      if (active) { item.active_monthly_cents += amount; item.active_licenses += licences; }
    }
  }
  const sorted = groups => Object.values(groups).sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
  return {
    source: 'API de contratos B2B (snapshot de status no momento da coleta)',
    fetched_at: now.toISOString(), total_contracts: rows.length, active_contracts: activeContracts,
    active_monthly_cents: activeMonthlyCents, active_licenses: activeLicenses,
    status: sorted(dimensions.status), plans: sorted(dimensions.plans),
    regions: sorted(dimensions.regions), products: sorted(dimensions.products),
    plan_region: Object.entries(planRegion).sort(([a],[b])=>a.localeCompare(b)).map(([key,value])=>{const [plan,region]=key.split('|||');return {plan,region,...value}}),
    start_year_status: Object.entries(startYearStatus).sort(([a],[b])=>a.localeCompare(b)).map(([key,value])=>{const [year,status]=key.split('|||');return {year,status,...value}}),
    starts: Object.entries(starts).sort(([a], [b]) => a.localeCompare(b)).map(([month, count]) => ({ month, count })),
    limits: 'Sem data_fim, histórico de status, cobrança ou recebimento. Inícios são coortes de assinatura, não MRR histórico.',
  };
}

async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ error: 'Método não permitido' });
  try {
    const rows = await collect(process.env.MEDWAY_B2B_TOKEN);
    res.setHeader('Cache-Control', 'public, s-maxage=900, stale-while-revalidate=300');
    return res.status(200).json(summarize(rows));
  } catch (error) {
    console.error('Falha na consulta B2B:', error.message); // no token, body or contract-level data
    res.setHeader('Cache-Control', 'no-store');
    return res.status(503).json({ error: 'Fonte B2B temporariamente indisponível; consulte o snapshot rotulado.' });
  }
}
module.exports = handler;
module.exports.collect = collect;
module.exports.summarize = summarize;
