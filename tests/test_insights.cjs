const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const b2c = JSON.parse(fs.readFileSync(path.join(root, 'public/data/b2c.json')));
const b2b = JSON.parse(fs.readFileSync(path.join(root, 'public/data/b2b-snapshot.json')));
const { computeInsights } = require('../public/insights.js');

test('insight drivers reconcile both dimensions to the same B2C increase', () => {
  const d = computeInsights(b2c, b2b);
  assert.equal(d.delta, 934913810);
  assert.equal(d.origins.reduce((n, x) => n + x.delta, 0), d.delta);
  assert.equal(d.products.reduce((n, x) => n + x.delta, 0), d.delta);
  assert.equal(d.originPairDelta, 624944488);
  assert.equal(d.productPairDelta, 614920245);
  assert.equal(d.course.count2026, 303);
  assert.equal(d.courseDelta, 22737892);
  assert.deepEqual([d.eventTypes[0].name, d.eventTypes[0].count, d.eventTypes[0].cents], ['Encontro Local', 278, 258706000]);
  assert.deepEqual([d.ambassadors[0].name, d.ambassadors[0].count, d.ambassadors[0].cents], ['Embaixador 07', 61, 49570057]);
  assert.deepEqual([d.icps[0].name, d.icps[0].count, d.icps[0].cents], ['Recém-formado', 1191, 1089572468]);
  assert.deepEqual([d.topIcpProduct.icp, d.topIcpProduct.product, d.topIcpProduct.count, d.topIcpProduct.cents], ['Recém-formado', 'Extensivo R1', 380, 425940196]);
  assert.equal(d.couponDifferent.count, 705);
  assert.equal(d.couponDifferent.cents, 589708043);
  assert.equal(d.couponComparableCount, 741);
  assert.equal(d.couponAudit.reduce((n, x) => n + x.count, 0), 786);
  const sourceCell = b2b.plan_region.find((r) => r.plan === 'Institucional Enterprise' && r.region === 'SP');
  assert.deepEqual(d.b2bCell, sourceCell);
  assert.equal(d.b2bActiveCents, b2b.active_monthly_cents);
  assert.ok(d.b2bCell.active_monthly_cents <= d.b2bActiveCents);
});

test('Insights is a fourth in-place tab, and old deep link redirects to it', () => {
  const page = fs.readFileSync(path.join(root, 'public/insights.html'), 'utf8');
  const home = fs.readFileSync(path.join(root, 'public/index.html'), 'utf8');
  assert.match(home, /data-view="insights"/);
  assert.equal((home.match(/data-view="(?:overview|b2c|b2b|insights)"/g) || []).length, 4);
  assert.doesNotMatch(home, /class="insights-entry"/);
  assert.match(home, /insights\.js\?v=/);
  assert.match(page, /location\.replace\("index\.html\?view=insights"\)/);
  assert.match(fs.readFileSync(path.join(root, 'public/app.js'), 'utf8'), /state\.view === "b2b" \|\| state\.view === "insights"/);
  assert.match(page, /Cinco decisões sustentadas por evidência/);
  assert.match(page, /ALERTA DE ATRIBUIÇÃO · EMBAIXADOR × CUPOM/);
  assert.match(page, /Sem o de-para oficial/);
  assert.match(page, /Maior valor pago não prova maior eficiência/);
  assert.match(page, /class="jump-b2c"/);
  assert.doesNotMatch(page, /\bAds\b|mídia|piloto de busca/i);
});

test('fails closed if a source dimension stops reconciling', () => {
  const broken = structuredClone(b2c);
  broken.monthly_product[0].cents += 1;
  assert.throws(() => computeInsights(broken, b2b), /não reconciliam/);
});
