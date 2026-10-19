/* SalesOps: all monetary aggregates are integer cents; flows and stock remain separate. */
const state = {
  b2c: null,
  b2b: null,
  b2bSnapshot: null,
  b2bAuxiliary: false,
  b2bLive: false,
  b2bScheduled: location.hostname.endsWith("github.io"),
  view: "overview",
  from: null,
  to: null,
  insightsMarkup: null,
  insightsPromise: null,
};
const $ = (id) => document.getElementById(id);
const money = (c) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    (c || 0) / 100,
  );
const short = (c) => {
  let v = (c || 0) / 100;
  return v >= 1e6
    ? `R$ ${(v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} mi`
    : v >= 1e3
      ? `R$ ${(v / 1e3).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mil`
      : money(c);
};
const integer = (n) => Number(n || 0).toLocaleString("pt-BR");
const percent = (a, b, d = 1) =>
  b
    ? `${((100 * a) / b).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d })}%`
    : "—";
const growth = (a, b) =>
  b
    ? `${((a / b - 1) * 100).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`
    : "—";
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        ch
      ],
  );
const month = (m) => {
  let [y, n] = m.split("-");
  return new Intl.DateTimeFormat("pt-BR", { month: "short" })
    .format(new Date(+y, +n - 1))
    .replace(".", "");
};
const longMonth = (m) => `${month(m)} ${m.slice(0, 4)}`;
const date = (s) => {
  if (!s) return "—";
  let [y, m, d] = s.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
};
const sum = (list, key) => list.reduce((t, r) => t + (Number(r[key]) || 0), 0);
const panel = (title, sub, body, wide = false) =>
  `<article class="panel${wide ? " panel-wide" : ""}"><div class="panel-head"><div><h3>${title}</h3><p>${sub}</p></div></div>${body}</article>`;
const kpi = (label, value, detail, featured = false) =>
  `<article class="kpi${featured ? " kpi-featured" : ""}"><span class="micro">${label}</span><strong>${value}</strong><small>${detail}</small></article>`;
const section = (index, title, desc) =>
  `<div class="section-lead"><div><span class="micro">${index} / PAINEL DE LEITURA</span><h2>${title}</h2></div><p>${desc}</p></div>`;
const note = (title, text) =>
  `<aside class="editorial"><span class="editorial-icon" aria-hidden="true">↗</span><div><span class="micro">IMPLICAÇÃO DE GESTÃO</span><h3>${title}</h3><p>${text}</p></div></aside>`;
const selected = () =>
  state.b2c.monthly.filter((r) => r.name >= state.from && r.name <= state.to);
const spikeInRange = () => "2025-09" >= state.from && "2025-09" <= state.to;
function comparison() {
  const monthly = state.b2c.monthly;
  return monthly
    .filter((r) => r.name.startsWith("2026-") && r.name >= state.from && r.name <= state.to)
    .map((b) => {
      const old = `2025-${b.name.slice(5)}`;
      return {
        name: month(b.name),
        a: monthly.find((r) => r.name === old),
        b,
      };
    })
    .filter((r) => r.a);
}
function grouped(list) {
  const map = new Map();
  for (const r of list || []) {
    if (r.month < state.from || r.month > state.to) continue;
    const row = map.get(r.name) || { name: r.name, cents: 0, count: 0 };
    row.cents += r.cents || 0;
    row.count += r.count || 0;
    map.set(r.name, row);
  }
  return [...map.values()].sort((a, b) => b.cents - a.cents);
}
function ranking(rows, key = "cents", limit = 6) {
  const data = [...rows].sort((a, b) => b[key] - a[key]).slice(0, limit),
    max = Math.max(1, ...data.map((r) => r[key]));
  return `<div class="rankings">${data.map((r, i) => `<div class="ranking"><span class="rank-n">${String(i + 1).padStart(2, "0")}</span><div class="rank-main"><div class="rank-caption"><span>${esc(r.name)}</span><strong>${short(r[key])}</strong></div><div class="rank-track"><span style="width:${Math.max(0, (100 * r[key]) / max)}%"></span></div></div></div>`).join("")}</div>`;
}
function trend(rows) {
  if (!rows.length) return '<p class="empty">Sem dados neste período.</p>';
  const W = 900,
    H = 280,
    L = 66,
    R = 16,
    T = 24,
    B = 42,
    pW = W - L - R,
    pH = H - T - B,
    max = Math.max(1, ...rows.map((r) => r.cents)) * 1.16,
    step = pW / rows.length,
    bw = Math.min(28, step * 0.54);
  const marks = [0, 0.25, 0.5, 0.75, 1]
    .map(
      (t) =>
        `<line x1="${L}" y1="${T + pH * (1 - t)}" x2="${W - R}" y2="${T + pH * (1 - t)}" class="chart-grid"/><text x="${L - 10}" y="${T + pH * (1 - t) + 4}" text-anchor="end" class="chart-axis">${t ? short(max * t) : "0"}</text>`,
    )
    .join("");
  const bars = rows
    .map((r, i) => {
      let x = L + step * i + (step - bw) / 2,
        h = (pH * r.cents) / max,
        y = T + pH - h,
        highlight = r.name === "2025-09";
      return `<g><rect class="trend-bar${highlight ? " spike" : ""}" x="${x}" y="${y}" width="${bw}" height="${h}" rx="3" tabindex="0" role="img" aria-label="${esc(longMonth(r.name) + ": " + money(r.cents) + " · " + integer(r.count) + " registros")}" data-tip="${esc(longMonth(r.name) + ": " + money(r.cents) + " · " + integer(r.count) + " registros")}"></rect><text x="${x + bw / 2}" y="${H - 12}" text-anchor="middle" class="chart-axis">${month(r.name)}${r.name.endsWith("-01") ? ` '${r.name.slice(2, 4)}` : ""}</text>${highlight ? `<text x="${x + bw / 2}" y="${Math.max(15, y - 9)}" text-anchor="middle" class="chart-callout">30/09 · 51,88% do mês</text>` : ""}</g>`;
    })
    .join("");
  return `<div class="chart-wrap"><svg class="chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Valor pago mensal de ${longMonth(rows[0].name)} a ${longMonth(rows.at(-1).name)}${rows.some((r) => r.name === "2025-09") ? ", com destaque para setembro de 2025" : ""}">${marks}${bars}</svg></div>`;
}
function yoy() {
  const pairs = comparison();
  if (!pairs.length)
    return '<p class="empty">Não há meses de 2026 neste filtro com referência equivalente em 2025.</p>';
  const max = Math.max(...pairs.map((r) => r.b.cents), 1),
    tot25 = sum(pairs.map((r) => r.a), "cents"),
    tot26 = sum(pairs.map((r) => r.b), "cents");
  return `<div class="legend"><span><i class="legend-navy"></i>2025 · referência</span><span><i class="legend-aqua"></i>2026 · filtro</span><strong>${growth(tot26, tot25)} no valor · meses selecionados</strong></div><div class="yoy-chart" role="img" aria-label="Comparativo de valor pago nos meses de 2026 selecionados contra os mesmos meses de 2025">${pairs.map((r) => `<div class="yoy-col"><div class="yoy-pair"><div class="yoy-bar navy" style="height:${Math.max(2, (r.a.cents / max) * 100)}%" tabindex="0" role="img" aria-label="${esc(r.name + " 2025: " + money(r.a.cents))}" data-tip="${esc(r.name + " 2025: " + money(r.a.cents))}"></div><div class="yoy-bar aqua" style="height:${Math.max(2, (r.b.cents / max) * 100)}%" tabindex="0" role="img" aria-label="${esc(r.name + " 2026: " + money(r.b.cents))}" data-tip="${esc(r.name + " 2026: " + money(r.b.cents))}"></div></div><span class="yoy-month">${r.name}</span></div>`).join("")}</div><p class="chart-foot">2026: somente meses no filtro. 2025: mesmos meses como referência comparativa, mesmo quando fora do intervalo selecionado. Valores exatos sobre as barras.</p><details class="chart-data"><summary>Ver valores exatos em tabela</summary><div class="chart-data-scroll"><table><caption>Valor pago B2C nos meses selecionados de 2026 e referência de 2025</caption><thead><tr><th scope="col">Mês</th><th scope="col">2025</th><th scope="col">2026</th></tr></thead><tbody>${pairs.map((r) => `<tr><th scope="row">${r.name}</th><td>${money(r.a.cents)}</td><td>${money(r.b.cents)}</td></tr>`).join("")}</tbody></table></div></details>`;
}
function bridge() {
  const pairs = comparison();
  if (!pairs.length)
    return '<p class="empty">Não há meses de 2026 neste filtro com referência equivalente em 2025 para decompor o crescimento.</p>';
  const a = pairs.map((r) => r.a),
    b = pairs.map((r) => r.b),
    ac = sum(a, "count"),
    bc = sum(b, "count"),
    av = sum(a, "cents"),
    bv = sum(b, "cents");
  let volume = (bc / ac - 1) * 100,
    ticket = (bv / bc / (av / ac) - 1) * 100;
  return `<div class="bridge"><div class="bridge-item"><span>01 / VOLUME</span><strong>${growth(bc, ac)}</strong><small>${integer(ac)} → ${integer(bc)} registros</small><div class="bridge-rail"><i style="width:${Math.max(0, Math.min(100, volume / 1.5))}%"></i></div></div><div class="bridge-operator">×</div><div class="bridge-item"><span>02 / TICKET MÉDIO</span><strong>${growth(bv / bc, av / ac)}</strong><small>${money(av / ac)} → ${money(bv / bc)}</small><div class="bridge-rail"><i style="width:${Math.max(3, Math.min(100, ticket / 1.5))}%"></i></div></div><div class="bridge-operator">=</div><div class="bridge-item bridge-result"><span>03 / VALOR PAGO</span><strong>${growth(bv, av)}</strong><small>${short(av)} → ${short(bv)}</small><div class="bridge-rail"><i style="width:100%"></i></div></div></div><p class="chart-foot">Meses de 2026 no filtro contra os mesmos meses de 2025 como referência. Valor = registros × média por registro.</p>`;
}
function matrix() {
  const data = state.b2c,
    raw = data.origin_product,
    origins = grouped(data.monthly_origin),
    products = grouped(data.monthly_product);
  if (!origins.length) return '<p class="empty">Sem dados neste recorte.</p>';
  let cols, rows, lookup, title;
  if (
    Array.isArray(raw) &&
    raw.length &&
    state.from === data.monthly[0].name &&
    state.to === data.monthly.at(-1).name
  ) {
    cols = products.map((r) => r.name);
    rows = origins;
    lookup = (o, p) =>
      raw.find(
        (r) =>
          (r.origin ?? r.origem ?? r.name) === o &&
          (r.product ?? r.produto) === p,
      )?.cents || 0;
    title = "Origem × produto · todo o histórico";
  } else {
    cols = data.monthly
      .filter((r) => r.name >= state.from && r.name <= state.to)
      .map((r) => r.name);
    rows = origins;
    lookup = (o, m) =>
      data.monthly_origin.find((r) => r.name === o && r.month === m)?.cents ||
      0;
    title = "Origem × mês · recorte selecionado";
  }
  const max = Math.max(
    1,
    ...rows.flatMap((r) => cols.map((c) => lookup(r.name, c))),
  );
  return `<p class="matrix-caption">${title} · intensidade = valor pago, não volume</p><div class="heat-scroll"><table class="heatmap"><thead><tr><th scope="col">Origem</th>${cols.map((c) => `<th scope="col">${esc(c.includes("-") ? month(c) : c.replace("Extensivo ", "Ext. ").replace("Programado ", "Prog. "))}</th>`).join("")}</tr></thead><tbody>${rows
    .map(
      (r) =>
        `<tr><th scope="row">${esc(r.name)}</th>${cols
          .map((c) => {
            let v = lookup(r.name, c),
              opacity = 0.12 + 0.8 * Math.max(0, v / max);
            return `<td style="--heat:${opacity.toFixed(3)}" tabindex="0" data-tip="${esc(r.name)} · ${esc(c)}: ${money(v)}"><span class="sr-only">${esc(r.name)}, ${esc(c)}: </span>${short(v)}</td>`;
          })
          .join("")}</tr>`,
    )
    .join(
      "",
    )}</tbody></table></div><p class="chart-foot">${Array.isArray(raw) && raw.length && cols.length === products.length ? "Cruzamento de origem e produto disponível para o histórico completo." : "Cruzamento origem × produto ainda não disponível neste agregado; exibimos a matriz origem × mês sem estimar interseções."}</p>`;
}
function quality() {
  const q = state.b2c.quality || {},
    items = (q.monthly || []).filter((r) => r.month >= state.from && r.month <= state.to),
    zero = sum(items, "zero"),
    negative = sum(items, "negative"),
    duplicates = sum(items, "identical_extra_rows_retained");
  return `<div class="quality-grid"><div><span>VALOR ZERO</span><strong>${integer(zero)}</strong><small>Ocorrência preservada no recorte</small></div><div><span>VALOR NEGATIVO</span><strong>${integer(negative)}</strong><small>Natureza não confirmada; valor individual não publicado</small></div><div><span>LINHAS IDÊNTICAS MANTIDAS</span><strong>${integer(duplicates)}</strong><small>Sem ID transacional para deduplicar</small></div></div><p class="chart-foot">Alertas apenas de ${longMonth(state.from)} a ${longMonth(state.to)}. Detalhes de vendas individuais não são publicados.</p>`;
}
function spike() {
  if (!spikeInRange()) return "";
  const m = state.b2c.monthly.find((r) => r.name === "2025-09"),
    d = state.b2c.daily.find((r) => r.name === "2025-09-30");
  if (!m || !d) return "";
  const dayOrigins = (state.b2c.daily_origin || [])
      .filter((r) => r.date === "2025-09-30")
      .sort((a, b) => b.cents - a.cents),
    monthOrigins = (state.b2c.monthly_origin || []).filter(
      (r) => r.month === "2025-09",
    );
  const rows = dayOrigins.length
    ? `<div class="spike-breakdown"><h4>O pico atravessa todas as origens</h4><div class="spike-origin-grid">${dayOrigins.map((r) => `<div><span>${esc(r.name)}</span><strong>${integer(r.count)} linhas</strong><small>${money(r.cents)}</small></div>`).join("")}</div><p>Exemplo: Orgânico foi ${percent(dayOrigins.find((r) => r.name === "Orgânico")?.count, d.count)} das linhas no dia vs ${percent((monthOrigins.find((r) => r.name === "Orgânico")?.count || 0) - (dayOrigins.find((r) => r.name === "Orgânico")?.count || 0), m.count - d.count)} no restante de setembro. Distribuição ampla entre canais; não há evidência de uma única campanha ou origem causal.</p></div>`
    : "";
  return `<aside class="spike-card"><span class="micro">PONTO FORA DA CURVA / 30 SET 2025</span><div class="spike-numbers"><div><strong>${integer(d.count)}</strong><span>linhas no dia<br>${percent(d.count, m.count, 2)} do volume de setembro</span></div><div><strong>${money(d.cents)}</strong><span>valor pago no dia<br>${percent(d.cents, m.cents, 2)} do valor de setembro</span></div></div>${rows}<p>Concentração observada, não causa comprovada. Examinar produto e cupom antes de atribuir o resultado a uma ação.</p></aside>`;
}
function b2bStale() {
  const fetched = new Date(state.b2b?.fetched_at).getTime();
  return (
    !state.b2bLive &&
    (!Number.isFinite(fetched) || Date.now() - fetched > 3 * 60 * 60 * 1000)
  );
}
function b2bNotice() {
  let stamp = new Date(state.b2b.fetched_at).toLocaleString("pt-BR");
  return state.b2bLive
    ? `API consultada em ${stamp}; status atual, não série histórica.${state.b2bAuxiliary ? ` Matrizes detalhadas do snapshot de ${new Date(state.b2bSnapshot.fetched_at).toLocaleString("pt-BR")}, com totais conciliados.` : ""}`
    : b2bStale()
      ? `ATENÇÃO: snapshot coletado em ${stamp}; mais de 3 horas sem coleta validada. Verifique a rotina antes de usar como dado atual.`
      : state.b2bScheduled
        ? `Snapshot coletado em ${stamp}; coleta agendada a cada hora no GitHub Pages.`
        : `Snapshot coletado em ${stamp}; API indisponível nesta visualização.`;
}
function overview() {
  const rows = selected(),
    cents = sum(rows, "cents"),
    count = sum(rows, "count"),
    b = state.b2b,
    m = state.b2c.monthly;
  const pairs = comparison(),
    old = pairs.map((r) => r.a),
    current = pairs.map((r) => r.b);
  const vOld = sum(old, "cents"),
    vCurrent = sum(current, "cents"),
    nOld = sum(old, "count"),
    nCurrent = sum(current, "count");
  const sep = m.find((r) => r.name === "2025-09"),
    spike = state.b2c.daily.find((r) => r.name === "2025-09-30");
  const overlap = (b.plan_region || []).filter(
    (r) => r.plan === "Institucional Enterprise" && r.region === "SP",
  );
  const overlapValue = sum(overlap, "active_monthly_cents"),
    overlapCount = sum(overlap, "count");
  const overlapHeadline = overlap.length
    ? percent(overlapValue, b.active_monthly_cents, 2)
    : "—";
  return (
    section(
      "01",
      "O crescimento exige <span>uma decisão.</span>",
      "A leitura conjunta separa vendas B2C no período e valor mensal contratado B2B na fotografia atual.",
    ) +
    `<div class="kpis">${kpi("B2C / VALOR PAGO", short(cents), `${longMonth(state.from)} — ${longMonth(state.to)} · ${integer(count)} registros`, true)}${kpi("B2B / VALOR MENSAL", short(b.active_monthly_cents), `${integer(b.active_contracts)} contratos ativos · ${integer(b.active_licenses)} licenças`)}</div>` +
    `<div class="story-thesis"><span class="micro">RESPOSTA PARA A GESTÃO</span><h3>Mais valor vendido não prova crescimento eficiente.</h3><p>${spikeInRange() ? "Antes de aumentar o investimento em aquisição, auditar o pico e medir margem/CAC por origem e produto." : "Antes de aumentar o investimento em aquisição, medir margem/CAC por origem e produto no período selecionado."} Em paralelo, acompanhar os contratos que concentram o valor mensal B2B.</p></div>` +
    `<div class="signal-grid" aria-label="Evidências do recorte selecionado e exposição B2B">` +
    (pairs.length ? `<article class="signal-card"><span>01 / MOTOR DO CRESCIMENTO</span><strong>${growth(vCurrent, vOld)}</strong><p>Valor B2C nos meses de 2026 filtrados contra os mesmos meses de 2025 como referência. A contagem cresceu ${growth(nCurrent, nOld)}; o valor médio por registro, ${growth(vCurrent / nCurrent, vOld / nOld)}.</p><small>Decisão: validar capacidade, margem e custo antes de ampliar verba.</small></article>` : `<article class="signal-card"><span>01 / COMPARAÇÃO ANUAL</span><strong>—</strong><p>Não há meses de 2026 no filtro com referência em 2025.</p></article>`) +
    (spikeInRange() ? `<article class="signal-card"><span>02 / ALERTA DE LEITURA</span><strong>${percent(spike.cents, sep.cents, 2)}</strong><p>Do valor de setembro/2025 aparece em 30/09, com registros nas quatro origens. A causa não está demonstrada pelo CSV.</p><small>Decisão: conferir pedidos, pagamentos e calendário antes de usar o mês como referência.</small></article>` : "") +
    `<article class="signal-card"><span>03 / EXPOSIÇÃO B2B</span><strong>${overlapHeadline}</strong><p>${overlap.length ? `${integer(overlapCount)} contratos Enterprise em SP concentram essa parcela do valor mensal ativo.` : "Cruzamento plano × região não disponível nesta coleta."} Plano e região são dimensões sobrepostas.</p><small>Decisão: acompanhar vigência e risco das contas materiais.</small></article>` +
    `</div>` +
    `${panel("Comparação B2C nos meses equivalentes", "Meses de 2026 no filtro × mesmos meses de 2025 como referência", yoy(), true)}` +
    `<div class="decision-stack"><div class="decision-title"><span class="micro">ORDEM DE AÇÃO</span><h3>O que fazer antes da próxima decisão de investimento</h3></div><ol>${spikeInRange() ? "<li><strong>Primeiro: auditar o pico.</strong> Confirmar data de pagamento, pedidos e origem de 30/09; não transformá-lo em meta ou sazonalidade sem validação.</li>" : ""}<li><strong>Medir a economia do crescimento.</strong> Cruzar valor por origem/produto com margem, CAC e conversão antes de redistribuir orçamento.</li><li><strong>Em paralelo: proteger a carteira B2B.</strong> Mapear vigência, uso de licenças e responsáveis pelos contratos de maior peso.</li></ol></div>` +
    `<div class="scope-strip"><div><span>FLUXO · B2C</span><p>Valor pago <strong>no período selecionado</strong>.</p></div><span class="scope-divider" aria-hidden="true">≠</span><div><span>ESTOQUE · B2B</span><p>Valor mensal <strong>dos contratos ativos no snapshot</strong>.</p></div><div class="scope-warning">Não somar como receita total.</div></div>` +
    `<p class="fine-print">CSV B2C é a fonte histórica recebida; B2B é atualizado por coleta agendada. ${esc(b2bNotice())} Explore as abas B2C e B2B para cortes detalhados.</p>`
  );
}
function b2cView() {
  let rows = selected(),
    c = sum(rows, "cents"),
    n = sum(rows, "count"),
    origins = grouped(state.b2c.monthly_origin),
    products = grouped(state.b2c.monthly_product);
  return (
    section(
      "02",
      "Vendas B2C. <span>O que move o valor?</span>",
      "Volume, ticket, sazonalidade e mix — com o mesmo cuidado para o dado atípico e o dado imperfeito.",
    ) +
    `<div class="kpis kpis-four">${kpi("VALOR PAGO", short(c), `${longMonth(state.from)} — ${longMonth(state.to)}`, true)}${kpi("REGISTROS", integer(n), "Linhas, não clientes únicos")}${kpi("MÉDIA / REGISTRO", n ? money(c / n) : "—", "Inclui os valores zero/negativo quando presentes no recorte")}${kpi("ORIGEM LÍDER", esc(origins[0]?.name || "—"), origins[0] ? `${percent(origins[0].cents, c)} do valor no recorte` : "Sem dados")}</div><div class="panel-grid">${panel("Comparação de meses equivalentes", "Meses de 2026 no filtro × mesmos meses de 2025 como referência", yoy(), true)}${panel("Ponte de crescimento", "Meses de 2026 filtrados × 2025 como referência", bridge(), true)}${panel("Valor ao longo do tempo", "B2C · cada mês no recorte selecionado", trend(rows), true)}${panel("Mapa de concentração", "Leitura cruzada das origens", matrix(), true)}${panel("Origens por valor", "Ranking · período selecionado", ranking(origins))}${panel("Produtos por valor", "Ranking · período selecionado", ranking(products))}${panel("Integridade do dado", "Exceções e linhas preservadas · período selecionado", quality(), true)}</div>${spike()}${spikeInRange() ? note("Pico não é estratégia por si só.", "A concentração de 30/09/2025 exige testar origem, produto e cupom no nível diário antes de replicar ações. O CSV não contém custos de aquisição, margem ou evidência causal.") : ""}`
  );
}
function cohort() {
  let b = state.b2b,
    raw = b.start_year_status;
  let rows = [];
  if (Array.isArray(raw) && raw.length) {
    for (let year of [2025, 2026]) {
      let group = raw.filter(
        (r) => String(r.year ?? r.start_year ?? r.name) === String(year),
      );
      rows.push({
        year,
        active: sum(
          group.filter((r) =>
            ["ativo", "active"].includes(String(r.status || "").toLowerCase()),
          ),
          "count",
        ),
        paused: sum(
          group.filter((r) =>
            ["pausado", "paused"].includes(
              String(r.status || "").toLowerCase(),
            ),
          ),
          "count",
        ),
        churn: sum(
          group.filter((r) => String(r.status || "").toLowerCase() === "churn"),
          "count",
        ),
      });
    }
  } else {
    return '<p class="empty">Coortes por ano e status não disponíveis nesta coleta. Não estimamos contratos ativos por ano apenas a partir das datas de início.</p>';
  }
  return `<div class="cohort-head"><span>ANO DE INÍCIO</span><span>ATIVOS HOJE</span></div>${rows.map((r) => `<div class="cohort-row"><strong>${r.year}</strong><div class="cohort-bar"><span style="width:${(100 * r.active) / Math.max(1, b.active_contracts)}%"></span></div><strong>${integer(r.active)} <small>de ${integer(b.active_contracts)}</small></strong></div>${r.paused || r.churn ? `<p class="cohort-extra">Início ${r.year}: ${integer(r.paused)} pausado · ${integer(r.churn)} churn (status hoje)</p>` : ""}`).join("")}<p class="chart-foot">${Array.isArray(raw) && raw.length ? "Coortes por início e status atual; não representam saldo histórico de cada ano." : "Divisão de ativos por ano informada no briefing do case; o snapshot atual ainda não contém coortes por status. Não inferimos status a partir de inícios totais."}</p>`;
}
function planRegion() {
  let b = state.b2b,
    raw = b.plan_region;
  if (Array.isArray(raw) && raw.length) {
    let plans = [...new Set(raw.map((r) => r.plan ?? r.plano ?? r.name))],
      regions = [...new Set(raw.map((r) => r.region ?? r.regiao))],
      max = Math.max(1, ...raw.map((r) => r.active_monthly_cents || 0));
    return `<div class="heat-scroll"><table class="heatmap"><thead><tr><th scope="col">Plano / região</th>${regions.map((r) => `<th scope="col">${esc(r)}</th>`).join("")}</tr></thead><tbody>${plans
      .map(
        (p) =>
          `<tr><th scope="row">${esc(p.replace("Institucional ", "") || p)}</th>${regions
            .map((region) => {
              let r = raw.find(
                  (x) =>
                    (x.plan ?? x.plano ?? x.name) === p &&
                    (x.region ?? x.regiao) === region,
                ),
                v = r?.active_monthly_cents || 0;
              return `<td style="--heat:${(0.12 + (0.8 * v) / max).toFixed(3)}" tabindex="0" data-tip="${esc(p)} · ${esc(region)}: ${money(v)}">${short(v)}</td>`;
            })
            .join("")}</tr>`,
      )
      .join(
        "",
      )}</tbody></table></div><p class="chart-foot">Valor mensal apenas dos contratos ativos. Escala de cor relativa à maior célula.</p>`;
  }
  return `<p class="empty">Cruzamento plano × região ainda não está no snapshot atual. Os rankings abaixo mostram marginais separados, sem inventar interseções.</p><div class="split-rank"><div><h4>Por plano</h4>${ranking(b.plans, "active_monthly_cents", 3)}</div><div><h4>Por região</h4>${ranking(b.regions, "active_monthly_cents", 7)}</div></div>`;
}
function b2bView() {
  let b = state.b2b,
    enterprise = b.plans.find((r) => r.name.includes("Enterprise")),
    sp = b.regions.find((r) => r.name === "SP"),
    pause = b.status.find((r) => r.name === "pausado"),
    churn = b.status.find((r) => r.name === "churn");
  return (
    section(
      "03",
      "Contratos B2B. <span>Carteira atual.</span>",
      "Um retrato de status, plano e território — não uma série temporal de receita recorrente.",
    ) +
    `<div class="source-banner"><span class="source-indicator" aria-hidden="true"></span>${esc(b2bNotice())}</div><div class="kpis kpis-four">${kpi("VALOR MENSAL ATIVO", short(b.active_monthly_cents), "Valor contratado, não recebido", true)}${kpi("CONTRATOS ATIVOS", integer(b.active_contracts), `${integer(b.total_contracts)} contratos no snapshot`)}${kpi("LICENÇAS ATIVAS", integer(b.active_licenses), "Somente status ativo")}${kpi("STATUS FORA DA BASE", `${integer(pause?.count || 0)} / ${integer(churn?.count || 0)}`, "Pausado / churn · status atual")}</div><div class="concentration"><div><span class="micro">CONCENTRAÇÃO / PLANO</span><strong>${percent(enterprise?.active_monthly_cents, b.active_monthly_cents, 2)}</strong><small>Enterprise no valor mensal ativo</small><div class="concentration-track"><i style="width:${(100 * (enterprise?.active_monthly_cents || 0)) / b.active_monthly_cents}%"></i></div></div><div><span class="micro">CONCENTRAÇÃO / TERRITÓRIO</span><strong>${percent(sp?.active_monthly_cents, b.active_monthly_cents, 2)}</strong><small>SP no valor mensal ativo</small><div class="concentration-track"><i style="width:${(100 * (sp?.active_monthly_cents || 0)) / b.active_monthly_cents}%"></i></div></div><p>Recortes sobrepostos: Enterprise e SP <strong>não</strong> devem ser somados.</p></div><div class="panel-grid">${panel("Coortes de início · status de hoje", "Ano de assinatura dos contratos ainda ativos", cohort())}${panel("Composição do portfólio", "Plano × região quando o cruzamento estiver disponível", planRegion(), true)}${panel("Planos contratados", "Valor mensal ativo por plano", ranking(b.plans, "active_monthly_cents", 3))}${panel("Territórios", "Valor mensal ativo por região", ranking(b.regions, "active_monthly_cents", 7))}</div>${note("Concentrar e reter são perguntas diferentes.", `Enterprise responde por ${percent(enterprise?.active_monthly_cents, b.active_monthly_cents, 2)} e SP por ${percent(sp?.active_monthly_cents, b.active_monthly_cents, 2)} do valor ativo; são dimensões que podem se cruzar. ${integer(pause?.count || 0)} contrato pausado e ${integer(churn?.count || 0)} em churn demandam investigação, mas não permitem calcular uma taxa histórica de churn.`)}<p class="fine-print">Sem data de encerramento, histórico de status, cobrança ou recebimento: nenhum gráfico desta seção representa MRR passado.</p>`
  );
}
function render() {
  hideTip();
  if (!state.b2c || !state.b2b) return;
  document.querySelectorAll(".tab").forEach((t) => {
    let active = t.dataset.view === state.view;
    t.classList.toggle("active", active);
    if (active) t.setAttribute("aria-current", "page");
    else t.removeAttribute("aria-current");
  });
  document.querySelector(".hero").hidden = state.view === "insights";
  $("control-bar").hidden = state.view === "b2b" || state.view === "insights";
  if (state.view === "insights") {
    $("content").innerHTML = state.insightsMarkup || '<p class="loading">Carregando insights…</p>';
    if (state.insightsMarkup) {
      try {
        window.MedwayInsights.render(window.MedwayInsights.computeInsights(state.b2c, state.b2b));
      } catch (error) {
        $("insight-error").hidden = false;
        console.error("Insights indisponíveis", error);
      }
    }
  } else {
    $("content").innerHTML = state.view === "b2c" ? b2cView() : state.view === "b2b" ? b2bView() : overview();
  }
  $("source-health").textContent = state.b2bLive
    ? "B2B · API consultada"
    : b2bStale()
      ? "B2B · coleta atrasada"
      : state.b2bScheduled
        ? "B2B · snapshot horário"
        : "B2B · snapshot datado";
  document.querySelectorAll(".source-indicator").forEach((el) => {
    el.classList.toggle("snapshot", !state.b2bLive);
    el.classList.toggle("stale", b2bStale());
  });
  $("asof").textContent =
    `B2C até ${date(state.b2c.period.last)} · B2B ${state.b2bLive ? "API" : "snapshot de " + date(state.b2b.fetched_at)}`;
  $("coverage").textContent =
    `CSV B2C fechado · ${date(state.b2c.period.first)} a ${date(state.b2c.period.last)}`;
}
async function getJson(url) {
  let r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw Error(`${url}: ${r.status}`);
  return r.json();
}
async function loadInsightsMarkup() {
  if (state.insightsMarkup) return;
  if (!state.insightsPromise) {
    state.insightsPromise = (async () => {
      const response = await fetch("insights.html", { cache: "no-store" });
      if (!response.ok) throw new Error(`insights.html: ${response.status}`);
      const parsed = new DOMParser().parseFromString(await response.text(), "text/html");
      const main = parsed.querySelector("main#main");
      if (!main || !main.querySelector("#hero-delta")) throw new Error("Template de insights inválido");
      state.insightsMarkup = [...main.children]
        .filter((element) => !element.classList.contains("insight-return"))
        .map((element) => element.outerHTML)
        .join("");
    })().catch((error) => {
      state.insightsPromise = null;
      throw error;
    });
  }
  return state.insightsPromise;
}
const hoverTip = document.createElement("div");
hoverTip.className = "hover-tip";
hoverTip.hidden = true;
hoverTip.setAttribute("aria-hidden", "true");
document.body.appendChild(hoverTip);
let activeTip = null;
function positionTip(x, y) {
  if (hoverTip.hidden) return;
  const w = hoverTip.offsetWidth,
    h = hoverTip.offsetHeight;
  hoverTip.style.left = `${Math.max(10, Math.min(x + 14, innerWidth - w - 10))}px`;
  hoverTip.style.top = `${y - h - 12 < 10 ? Math.min(innerHeight - h - 10, y + 18) : y - h - 12}px`;
}
function showTip(target, x, y) {
  activeTip = target;
  hoverTip.textContent = target.dataset.tip;
  hoverTip.hidden = false;
  positionTip(x, y);
}
function hideTip() {
  activeTip = null;
  hoverTip.hidden = true;
}
document.addEventListener("pointerover", (e) => {
  const target = e.target.closest?.("[data-tip]");
  if (target && target !== activeTip) showTip(target, e.clientX, e.clientY);
});
document.addEventListener("pointermove", (e) => {
  if (activeTip) positionTip(e.clientX, e.clientY);
});
document.addEventListener("pointerout", (e) => {
  if (
    activeTip &&
    e.target === activeTip &&
    !activeTip.contains(e.relatedTarget)
  )
    hideTip();
});
document.addEventListener("focusin", (e) => {
  const target = e.target.closest?.("[data-tip]");
  if (target) {
    const r = target.getBoundingClientRect();
    showTip(target, r.left + r.width / 2, r.top);
  }
});
document.addEventListener("focusout", (e) => {
  if (e.target === activeTip) hideTip();
});
window.addEventListener("resize", () => {
  if (activeTip) hideTip();
});
async function refreshB2B() {
  if (state.b2bScheduled) {
    try {
      state.b2b = state.b2bSnapshot = await getJson("data/b2b-snapshot.json");
    } catch (e) {
      console.warn("Snapshot B2B não atualizado", e);
    }
    render();
    return;
  }
  try {
    let live = await getJson("/api/b2b");
    if (!Number.isFinite(live.active_monthly_cents))
      throw Error("Métrica inválida");
    let snapshot = state.b2bSnapshot,
      same =
        snapshot &&
        live.active_monthly_cents === snapshot.active_monthly_cents &&
        live.active_contracts === snapshot.active_contracts &&
        live.active_licenses === snapshot.active_licenses;
    state.b2bAuxiliary = Boolean(
      same && (!live.plan_region || !live.start_year_status),
    );
    state.b2b = state.b2bAuxiliary
      ? {
          ...live,
          plan_region: live.plan_region || snapshot.plan_region,
          start_year_status:
            live.start_year_status || snapshot.start_year_status,
        }
      : live;
    state.b2bLive = true;
  } catch (e) {
    state.b2bLive = false;
    state.b2bAuxiliary = false;
    try {
      state.b2b = state.b2bSnapshot = await getJson("data/b2b-snapshot.json");
    } catch (e2) {
      console.warn("Mantendo último snapshot válido", e2);
    }
    console.warn("API B2B indisponível; snapshot rotulado", e);
  }
  render();
}
async function init() {
  try {
    const requestedView = new URLSearchParams(location.search).get("view");
    if (["overview", "b2c", "b2b", "insights"].includes(requestedView)) state.view = requestedView;
    [state.b2c, state.b2b] = await Promise.all([
      getJson("data/b2c.json"),
      getJson("data/b2b-snapshot.json"),
    ]);
    state.b2bSnapshot = state.b2b;
    let months = state.b2c.monthly.map((r) => r.name);
    state.from = months[0];
    state.to = months.at(-1);
    for (let id of ["from", "to"]) {
      $(id).innerHTML = months
        .map((m) => `<option value="${m}">${longMonth(m)}</option>`)
        .join("");
      $(id).value = state[id];
      $(id).addEventListener("change", () => {
        state.from = $("from").value;
        state.to = $("to").value;
        if (state.from > state.to) {
          state[id === "from" ? "to" : "from"] = state[id];
          $("from").value = state.from;
          $("to").value = state.to;
        }
        render();
      });
    }
    document.querySelectorAll(".tab").forEach((t) =>
      t.addEventListener("click", async () => {
        const view = t.dataset.view;
        state.view = view;
        const url = new URL(location.href);
        if (view === "overview") url.searchParams.delete("view");
        else url.searchParams.set("view", view);
        history.replaceState(null, "", url);
        render();
        if (view === "insights" && !state.insightsMarkup) {
          try {
            await loadInsightsMarkup();
            if (state.view === view) render();
          } catch (error) {
            if (state.view === view) $("content").innerHTML = '<div class="error" role="alert">Não foi possível carregar os insights. Tente abrir a aba novamente.</div>';
            console.error(error);
          }
        }
      }),
    );
    if (state.view === "insights") {
      try { await loadInsightsMarkup(); }
      catch (error) { console.error("Template de insights indisponível", error); }
    }
    render();
    if (!state.b2bScheduled) await refreshB2B();
    setInterval(refreshB2B, 15 * 60 * 1000);
  } catch (e) {
    $("source-health").textContent = "Dados indisponíveis";
    $("content").innerHTML =
      '<div class="error" role="alert">Não foi possível carregar os agregados. Verifique a geração dos arquivos de dados e atualize a página.</div>';
    console.error(e);
  }
}
init();
