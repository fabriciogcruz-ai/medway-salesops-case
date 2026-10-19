/* Decision brief: only published aggregates; no transaction-level data or token. */
(function (root) {
  "use strict";
  const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 2 });
  const number = new Intl.NumberFormat("pt-BR");
  const percent = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const money = (cents) => BRL.format(cents / 100);
  const pct = (part, total) => total ? `${percent.format(100 * part / total)}%` : "—";
  const shortMoney = (cents) => `R$ ${new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(cents / 100000000)} mi`;

  function grouped(rows, year) {
    const out = new Map();
    for (const row of rows) {
      if (row.month < `${year}-01` || row.month > `${year}-07`) continue;
      const current = out.get(row.name) || { name: row.name, count: 0, cents: 0 };
      current.count += row.count;
      current.cents += row.cents;
      out.set(row.name, current);
    }
    return out;
  }

  function drivers(rows) {
    const old = grouped(rows, "2025"), current = grouped(rows, "2026");
    if (old.size !== current.size || !current.size) throw new Error("Dimensões B2C incompletas entre os anos");
    return [...current.values()].map((item) => {
      const prior = old.get(item.name);
      if (!prior) throw new Error(`Categoria sem referência: ${item.name}`);
      return { name: item.name, count2025: prior.count, count2026: item.count, cents2025: prior.cents, cents2026: item.cents, delta: item.cents - prior.cents };
    }).sort((a, b) => b.delta - a.delta);
  }

  function computeInsights(b2c, b2b) {
    const janJul = (year) => b2c.monthly.filter((row) => row.name >= `${year}-01` && row.name <= `${year}-07`);
    const sum = (rows, key) => rows.reduce((acc, row) => acc + row[key], 0);
    const old = janJul("2025"), current = janJul("2026");
    if (old.length !== 7 || current.length !== 7) throw new Error("Jan–jul incompleto");
    const delta = sum(current, "cents") - sum(old, "cents");
    if (delta <= 0) throw new Error("Diferença B2C não positiva; revisar narrativa");
    const origins = drivers(b2c.monthly_origin), products = drivers(b2c.monthly_product);
    if (sum(origins, "delta") !== delta || sum(products, "delta") !== delta) throw new Error("Dimensões não reconciliam com o total");
    const pairDelta = (list, names) => names.reduce((acc, name) => {
      const found = list.find((row) => row.name === name);
      if (!found) throw new Error(`Categoria ausente: ${name}`);
      return acc + found.delta;
    }, 0);
    const course = products.find((row) => row.name === "Curso Avulso");
    const cell = b2b.plan_region.find((row) => row.plan === "Institucional Enterprise" && row.region === "SP");
    if (!cell || !b2b.active_monthly_cents) throw new Error("Cruzamento B2B ausente");
    return {
      delta, origins, products,
      originPairDelta: pairDelta(origins, ["Orgânico", "Indicação Direta"]),
      productPairDelta: pairDelta(products, ["Extensivo R1", "Extensivo R+"]),
      course,
      courseDelta: course.delta,
      b2bCell: cell,
      b2bActiveCents: b2b.active_monthly_cents,
      b2bFetchedAt: b2b.fetched_at,
    };
  }

  function renderBars(container, rows, total) {
    container.replaceChildren();
    const max = Math.max(1, ...rows.map((row) => Math.abs(row.delta)));
    for (const row of rows) {
      const item = document.createElement("div"); item.className = "driver-row";
      if (row === rows[0]) item.classList.add("is-lead");
      const label = document.createElement("span"); label.className = "driver-name"; label.textContent = row.name;
      const value = document.createElement("strong"); value.className = "driver-value"; value.textContent = `${pct(row.delta, total)} · ${money(row.delta)}`;
      const track = document.createElement("div"); track.className = "driver-track";
      const bar = document.createElement("span"); bar.style.width = `${Math.max(0, 100 * Math.abs(row.delta) / max)}%`;
      track.append(bar); item.append(label, value, track); container.append(item);
    }
  }

  function render(data) {
    const set = (id, text) => { document.getElementById(id).textContent = text; };
    set("hero-delta", `+${shortMoney(data.delta)}`);
    set("origin-pair-share", pct(data.originPairDelta, data.delta));
    set("product-pair-share", pct(data.productPairDelta, data.delta));
    set("paid-signal", pct(data.productPairDelta, data.delta));
    set("earned-signal", pct(data.originPairDelta, data.delta));
    set("course-volume", number.format(data.course.count2026));
    set("course-growth-share", pct(data.courseDelta, data.delta));
    set("b2b-cell-share", pct(data.b2bCell.active_monthly_cents, data.b2bActiveCents));
    set("b2b-cell-count", number.format(data.b2bCell.count));
    const fetched = new Date(data.b2bFetchedAt);
    set("b2b-stamp", Number.isNaN(fetched.getTime()) ? "data indisponível" : new Intl.DateTimeFormat("pt-BR", { timeZone: "America/Sao_Paulo", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(fetched));
    renderBars(document.getElementById("origin-bars"), data.origins, data.delta);
    renderBars(document.getElementById("product-bars"), data.products, data.delta);
  }

  async function init() {
    try {
      const [b2cResponse, b2bResponse] = await Promise.all([
        fetch("data/b2c.json", { cache: "no-store" }),
        fetch("data/b2b-snapshot.json", { cache: "no-store" }),
      ]);
      if (!b2cResponse.ok || !b2bResponse.ok) throw new Error("Agregados indisponíveis");
      render(computeInsights(await b2cResponse.json(), await b2bResponse.json()));
    } catch (error) {
      document.getElementById("insight-error").hidden = false;
      document.getElementById("hero-delta").textContent = "Dados indisponíveis";
      console.error("Falha ao carregar insights", error);
    }
  }
  if (typeof module !== "undefined" && module.exports) module.exports = { computeInsights };
  if (typeof document !== "undefined" && document.getElementById("hero-delta")) init();
})(typeof window !== "undefined" ? window : globalThis);
