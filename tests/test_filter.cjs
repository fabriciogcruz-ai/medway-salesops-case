const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'public/app.js'), 'utf8');
const b2c = JSON.parse(fs.readFileSync(path.join(root, 'public/data/b2c.json')));
const b2b = JSON.parse(fs.readFileSync(path.join(root, 'public/data/b2b-snapshot.json')));

function setup(from, to) {
  const document = {
    createElement: () => ({ setAttribute() {}, style: {} }),
    body: { appendChild() {} },
    addEventListener() {},
  };
  const sandbox = { document, window: { addEventListener() {} }, location: { hostname: 'example.github.io' }, console, Date, Intl, Map, Math, Number, String, Array, Set, Error, fetch() {} };
  vm.createContext(sandbox);
  assert.match(source, /\ninit\(\);\s*$/);
  vm.runInContext(source.replace(/\ninit\(\);\s*$/, ''), sandbox);
  vm.runInContext(`state.b2c = ${JSON.stringify(b2c)}; state.b2b = ${JSON.stringify(b2b)}; state.from = ${JSON.stringify(from)}; state.to = ${JSON.stringify(to)};`, sandbox);
  return (expression) => vm.runInContext(expression, sandbox);
}

test('June–July 2026 filters B2C cards, comparison, spike, and quality', () => {
  const run = setup('2026-06', '2026-07');
  const html = run('b2cView()');
  const overview = run('overview()');
  assert.match(html, /R\$ 5,52 mi/);
  assert.match(html, /600<\/strong>/);
  assert.equal((html.match(/class="yoy-col"/g) || []).length, 2);
  assert.match(html, /2025 · referência/);
  assert.doesNotMatch(html, /spike-card|Pico não é estratégia|30\/09\/2025|R\$ 3\.127\.917/);
  assert.equal((html.match(/class="trend-bar/g) || []).length, 2);
  assert.match(html, /Alertas apenas de jun 2026 a jul 2026/);
  assert.doesNotMatch(overview, /30\/09/);
  assert.equal((overview.match(/class="yoy-col"/g) || []).length, 2);
  assert.match(overview, /150,96%/);
  assert.equal(run('comparison().length'), 2);
  assert.equal(run('spike()'), '');
});

test('full history restores seven comparative months and September anomaly', () => {
  const run = setup('2025-01', '2026-07');
  const html = run('b2cView()');
  assert.equal((html.match(/class="yoy-col"/g) || []).length, 7);
  assert.match(html, /spike-card/);
  assert.match(html, /Pico não é estratégia/);
  assert.match(html, /30\/09\/2025/);
  assert.equal(run('comparison().length'), 7);
});

test('a 2025-only selection does not invent a year-over-year comparison', () => {
  const run = setup('2025-09', '2025-09');
  const html = run('b2cView()');
  assert.match(html, /Não há meses de 2026 neste filtro/);
  assert.doesNotMatch(html, /class="yoy-col"/);
  assert.match(html, /spike-card/);
});
