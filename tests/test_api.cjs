const test = require('node:test');
const assert = require('node:assert/strict');
const { collect, summarize } = require('../api/b2b');

test('pagination reconciles total and preserves unique contracts', async () => {
  const pages = [
    {total: 3, contratos: [{id_contrato:'A'}, {id_contrato:'B'}]},
    {total: 3, contratos: [{id_contrato:'C'}]},
  ];
  const rows = await collect('test-only', async () => ({ok:true, json:async()=>pages.shift()}));
  assert.equal(rows.length, 3);
});

test('fails closed on inconsistent pagination', async () => {
  const pages = [{total:2,contratos:[{id_contrato:'A'}]},{total:2,contratos:[{id_contrato:'A'}]}];
  await assert.rejects(collect('test-only', async()=>({ok:true,json:async()=>pages.shift()})),/duplicado/);
});

test('active monthly value excludes paused/churn', () => {
  const base = {plano:'Pro',regiao:'SP',produto:'R1',num_licencas:3,data_inicio:'2025-01-01'};
  const data = summarize([
    {...base,id_contrato:'A',status:'ativo',valor_mensal:100.50},
    {...base,id_contrato:'B',status:'pausado',valor_mensal:300},
  ],new Date('2026-10-18T00:00:00Z'));
  assert.equal(data.active_monthly_cents,10050);
  assert.equal(data.active_contracts,1);
  assert.equal(data.active_licenses,3);
  assert.equal(data.plan_region[0].active_monthly_cents,10050);
  assert.equal(data.start_year_status.find(x=>x.status==='pausado').active_monthly_cents,0);
  assert.equal(JSON.stringify(data).includes('id_contrato'),false);
});
