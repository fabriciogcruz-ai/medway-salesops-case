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
  const sourceCell = b2b.plan_region.find((r) => r.plan === 'Institucional Enterprise' && r.region === 'SP');
  assert.deepEqual(d.b2bCell, sourceCell);
  assert.equal(d.b2bActiveCents, b2b.active_monthly_cents);
  assert.ok(d.b2bCell.active_monthly_cents <= d.b2bActiveCents);
});

test('page links are reciprocal, and Ads recommendation is explicitly conditional', () => {
  const page = fs.readFileSync(path.join(root, 'public/insights.html'), 'utf8');
  const home = fs.readFileSync(path.join(root, 'public/index.html'), 'utf8');
  assert.match(home, /href="insights\.html"/);
  assert.match(page, /href="index\.html"/);
  assert.match(page, /HIPÓTESE, NÃO ROI MEDIDO/);
  assert.match(page, /Não existe “melhor canal de Ads” demonstrado aqui/);
  assert.doesNotMatch(page, /invista R\$|ROI de \d/);
});

test('fails closed if a source dimension stops reconciling', () => {
  const broken = structuredClone(b2c);
  broken.monthly_product[0].cents += 1;
  assert.throws(() => computeInsights(broken, b2b), /não reconciliam/);
});
