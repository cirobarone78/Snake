"use strict";

const SOURCES = {
  crypto: "data/crypto_report.json",
  equity: "data/equity_report.json",
  education: "data/education.json",
  market: "data/market_series.json",
  events: "data/events.json",
  health: "data/data_health.json",
  paper: "data/paper_report.json",
  replay: "data/paper_replay.json",
  dca: "data/dca_report.json",
  ranking: "data/ranking_report.json",
  rankingModel: "data/ranking_model.json",
  rankingBacktest: "data/ranking_backtest.json",
};

const HEALTH_LABEL = { match: "Fonti concordi", mismatch: "Divergenza", single_source: "Fonte unica" };
// A health check that can't see its own staleness is a smoke alarm with a dead
// battery: if the cron stops, the dots stay green forever. Flag past this age.
const HEALTH_STALE_HOURS = 36;

const CLASS_LABEL = { "market-wide": "Di mercato", "asset-specific": "Specifico dell'asset", unknown: "Da definire" };
const CLASS_CLASS = { "market-wide": "market", "asset-specific": "specific", unknown: "unknown" };
const EVENT_TYPE_LABEL = {
  hack: "Hack/Exploit", regulation: "Regolatorio", legal: "Legale", fed: "Fed/Tassi",
  inflation: "Inflazione", macro: "Macro", geopolitical: "Geopolitico", etf_flow: "Flussi ETF",
  earnings: "Earnings", listing: "Listing", delisting: "Delisting", upgrade: "Upgrade",
  partnership: "Partnership", other: "Altro",
};

const STATUS_LABEL = {
  hot: "In forza", warm: "In rafforzamento", neutral: "Neutrale", weak: "In calo", risk: "Rischio",
};

const NF = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 2 });
const NF0 = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 0 });
// Fixed-decimal variants: a column of "+3,31 pp" next to "+1 pp" reads as a
// different kind of number, so the aligned metrics pin their decimals.
const NF1 = new Intl.NumberFormat("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const NF2 = new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const EUR0 = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const EUR2 = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 });
const ORDER_STATUS_LABEL = { pending: "in attesa", filled: "eseguito", cancelled: "annullato", rejected: "rifiutato" };

document.addEventListener("DOMContentLoaded", init);

async function init() {
  setupTabs();
  const [crypto, equity, education, market, events, health, paper, replay, dca,
    ranking, rankingModel, rankingBacktest] = await Promise.all([
    fetchJSON(SOURCES.crypto), fetchJSON(SOURCES.equity),
    fetchJSON(SOURCES.education), fetchJSON(SOURCES.market), fetchJSON(SOURCES.events),
    fetchJSON(SOURCES.health), fetchJSON(SOURCES.paper), fetchJSON(SOURCES.replay),
    fetchJSON(SOURCES.dca), fetchJSON(SOURCES.ranking), fetchJSON(SOURCES.rankingModel),
    fetchJSON(SOURCES.rankingBacktest),
  ]);
  renderTicker(market);
  renderHero(market);
  renderHealth(health);
  renderCrypto(crypto);
  renderEquity(equity);
  renderEvents(events);
  renderPaper(paper);
  renderReplay(replay);
  renderDca(dca);
  renderRanking(ranking);
  renderRankingModel(rankingModel, rankingBacktest);
  renderOverview(crypto, equity);
  renderEducation(education);
  renderFooter(crypto, equity, market);
}

async function fetchJSON(path) {
  try {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch (_e) { return null; }
}

/* ---------- Tabs ---------- */
function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".panel");
  const activate = (name, scroll) => {
    const tab = [...tabs].find((t) => t.dataset.tab === name);
    if (!tab) return;
    tabs.forEach((t) => t.classList.remove("is-active"));
    panels.forEach((p) => p.classList.remove("is-active"));
    tab.classList.add("is-active");
    const target = document.getElementById(name);
    if (target) target.classList.add("is-active");
    // Nove tab non entrano in 390px: senza questo, su mobile la tab attiva
    // resta fuori schermo e la pagina sembra aperta su un'altra sezione.
    const strip = tab.parentElement;
    if (strip && strip.scrollWidth > strip.clientWidth) {
      strip.scrollTo({ left: tab.offsetLeft - (strip.clientWidth - tab.offsetWidth) / 2, behavior: scroll ? "smooth" : "auto" });
    }
    if (scroll) window.scrollTo({ top: 0, behavior: "smooth" });
  };
  tabs.forEach((tab) => tab.addEventListener("click", () => {
    activate(tab.dataset.tab, true);
    history.replaceState(null, "", `#${tab.dataset.tab}`);
  }));
  // Deep link: #events opens the Eventi tab directly.
  const hash = (location.hash || "").slice(1);
  if (hash && document.getElementById(hash)) activate(hash, false);
}

/* ---------- Formatting ---------- */
function fmtPct(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}
function pctClass(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "";
  return v >= 0 ? "pos" : "neg";
}
function fmtNum(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Math.abs(v) >= 100 ? NF0.format(v) : NF.format(v);
}
function fmtPrice(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const d = Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 1 ? 2 : 4;
  return v.toLocaleString("it-IT", { minimumFractionDigits: d, maximumFractionDigits: d });
}
function ageHours(iso) {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? null : (Date.now() - t) / 3600000;
}
function fmtMcap(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return null;
  if (v >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toFixed(0)}`;
}
function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("it-IT", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
function fmtDay(t) {
  const d = new Date(t);
  return Number.isNaN(d.getTime()) ? t : d.toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "2-digit" });
}
function el(tag, className, text) {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text !== undefined) n.textContent = text;
  return n;
}

/* ---------- Ticker ---------- */
function renderTicker(market) {
  const root = document.getElementById("ticker");
  root.innerHTML = "";
  if (!market || !Array.isArray(market.series) || market.series.length === 0) { root.style.display = "none"; return; }
  market.series.forEach((s) => {
    const box = el("div", "tk");
    box.appendChild(el("div", "sym", s.name || s.symbol));
    box.appendChild(el("div", "val", fmtNum(s.last)));
    box.appendChild(el("div", `chg ${pctClass(s.change_pct)}`, `${fmtPct(s.change_pct)} · 1 anno`));
    root.appendChild(box);
  });
}

/* ---------- Hero chart ---------- */
let HERO = { series: [], active: 0, tf: "3m" };
const TIMEFRAMES = [["1m", "1 mese", 31], ["3m", "3 mesi", 92], ["6m", "6 mesi", 184], ["1y", "1 anno", 100000]];

function renderHero(market) {
  const chips = document.getElementById("hero-chips");
  chips.innerHTML = "";
  if (!market || !Array.isArray(market.series) || market.series.length === 0) {
    document.getElementById("hero-name").textContent = "Dati non disponibili";
    return;
  }
  HERO.series = market.series;
  HERO.active = 0;
  market.series.forEach((s, i) => {
    const chip = el("button", "chip" + (i === 0 ? " is-active" : ""), s.name || s.symbol);
    chip.addEventListener("click", () => {
      HERO.active = i;
      [...chips.children].forEach((c, j) => c.classList.toggle("is-active", j === i));
      drawHero();
    });
    chips.appendChild(chip);
  });

  const tfRow = document.getElementById("hero-tf");
  tfRow.innerHTML = "";
  TIMEFRAMES.forEach(([key, label]) => {
    const chip = el("button", "chip tf" + (key === HERO.tf ? " is-active" : ""), label);
    chip.addEventListener("click", () => {
      HERO.tf = key;
      [...tfRow.children].forEach((c) => c.classList.toggle("is-active", c.textContent === label));
      drawHero();
    });
    tfRow.appendChild(chip);
  });

  drawHero();
}

function drawHero() {
  const s = HERO.series[HERO.active];
  if (!s) return;
  const full = s.points || [];
  // slice to the selected timeframe by calendar days
  const tf = TIMEFRAMES.find((t) => t[0] === HERO.tf) || TIMEFRAMES[3];
  let pts = full;
  if (full.length > 1) {
    const lastT = new Date(full[full.length - 1].t).getTime();
    const cutoff = lastT - tf[2] * 86400000;
    pts = full.filter((p) => new Date(p.t).getTime() >= cutoff);
    if (pts.length < 2) pts = full.slice(-2);
  }
  const vals0 = pts.map((p) => p.v);
  const change = vals0.length > 1 && vals0[0] ? (vals0[vals0.length - 1] / vals0[0] - 1) * 100 : null;

  document.getElementById("hero-name").textContent = s.name || s.symbol;
  document.getElementById("hero-last").textContent = fmtNum(s.last);
  const chg = document.getElementById("hero-change");
  chg.textContent = `${fmtPct(change)} · ${tf[1]}`;
  chg.className = `hero-change ${pctClass(change)}`;

  const svg = document.getElementById("hero-chart");
  const W = 720, H = 240, padT = 16, padB = 24, padX = 6;
  const vals = pts.map((p) => p.v);
  const min = Math.min(...vals), max = Math.max(...vals);
  const span = max - min || 1;
  const x = (i) => padX + (i / Math.max(pts.length - 1, 1)) * (W - 2 * padX);
  const y = (v) => H - padB - ((v - min) / span) * (H - padT - padB);
  const down = (change ?? 0) < 0;
  const stroke = down ? "url(#gNeg)" : "url(#gPos)";
  const fill = down ? "url(#gNegFill)" : "url(#gPosFill)";

  let line = "";
  pts.forEach((p, i) => { line += `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.v).toFixed(1)} `; });
  const area = `${line}L${x(pts.length - 1).toFixed(1)},${H - padB} L${x(0).toFixed(1)},${H - padB} Z`;
  const lx = x(pts.length - 1).toFixed(1), ly = y(vals[vals.length - 1]).toFixed(1);

  svg.innerHTML = `
    <defs>
      <linearGradient id="gPos" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#5eead4"/><stop offset="1" stop-color="#7c8cff"/>
      </linearGradient>
      <linearGradient id="gNeg" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#ff8aa0"/><stop offset="1" stop-color="#ff6b81"/>
      </linearGradient>
      <linearGradient id="gPosFill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="rgba(94,234,212,0.28)"/><stop offset="1" stop-color="rgba(94,234,212,0)"/>
      </linearGradient>
      <linearGradient id="gNegFill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="rgba(255,107,129,0.26)"/><stop offset="1" stop-color="rgba(255,107,129,0)"/>
      </linearGradient>
    </defs>
    <path d="${area}" fill="${fill}" stroke="none"/>
    <path d="${line}" fill="none" stroke="${stroke}" stroke-width="2.4"
      stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>
    <circle cx="${lx}" cy="${ly}" r="4" fill="#fff"/>
    <circle cx="${lx}" cy="${ly}" r="8" fill="none" stroke="${stroke}" stroke-width="1.5" opacity="0.5"/>
  `;

  const foot = document.getElementById("hero-foot");
  foot.innerHTML = "";
  foot.appendChild(el("span", "", pts.length ? `${fmtDay(pts[0].t)} → ${fmtDay(pts[pts.length - 1].t)}` : ""));
  foot.appendChild(el("span", "", `min ${fmtNum(min)} · max ${fmtNum(max)}`));
}

/* ---------- Sparkline (cards) ---------- */
function sparklineSVG(values) {
  if (!Array.isArray(values) || values.length < 2) return "";
  const W = 200, H = 44, pad = 3;
  const min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
  const x = (i) => pad + (i / (values.length - 1)) * (W - 2 * pad);
  const y = (v) => H - pad - ((v - min) / span) * (H - 2 * pad);
  let d = "";
  values.forEach((v, i) => { d += `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)} `; });
  const down = values[values.length - 1] < values[0];
  const col = down ? "#ff6b81" : "#5eead4";
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">
    <path d="${d}" fill="none" stroke="${col}" stroke-width="1.8" stroke-linejoin="round"
      stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>`;
}

/* ---------- Rotation cards ---------- */
function statusPill(status) {
  const key = (status || "neutral").toLowerCase();
  return el("span", `status ${key}`, STATUS_LABEL[key] || status || "—");
}
function rotationCard(item, kind) {
  const card = el("div", "rotation-card");
  const row1 = el("div", "row1");
  const left = el("div");
  left.appendChild(el("div", "rank", `#${item.rank}`));
  left.appendChild(el("div", "name", item.name || "—"));
  if (kind === "equity" && item.ticker) left.appendChild(el("div", "ticker", item.ticker));
  row1.appendChild(left);
  row1.appendChild(statusPill(item.status));
  card.appendChild(row1);

  if (typeof item.strength === "number") {
    const wrap = el("div", "strength");
    const track = el("div", "track");
    const fill = el("div", "fill");
    fill.style.width = `${Math.round(item.strength * 100)}%`;
    track.appendChild(fill); wrap.appendChild(track);
    wrap.appendChild(el("span", "pct", `forza ${(item.strength * 100).toFixed(0)}`));
    card.appendChild(wrap);
  }

  if (typeof item.data_confidence === "number") {
    const cst = (item.confidence_status || "valid").toLowerCase();
    const wrap = el("div", "strength confidence");
    wrap.title = item.confidence_reason || "";
    const track = el("div", "track");
    const fill = el("div", `fill conf-${cst}`);
    fill.style.width = `${Math.round(item.data_confidence * 100)}%`;
    track.appendChild(fill); wrap.appendChild(track);
    wrap.appendChild(el("span", "pct", `dato ${(item.data_confidence * 100).toFixed(0)}`));
    card.appendChild(wrap);
  }

  const metrics = el("div", "metrics");
  if (kind === "crypto") {
    metrics.appendChild(metric("24 ore", item.change_24h));
    const mc = fmtMcap(item.market_cap);
    if (mc) metrics.appendChild(metricRaw("Capitalizzazione", mc));
  } else {
    metrics.appendChild(metric("5 giorni", item.change_5d));
    metrics.appendChild(metric("~1 mese", item.change_1m));
  }
  card.appendChild(metrics);

  if (kind === "equity" && Array.isArray(item.spark) && item.spark.length > 1) {
    const holder = el("div");
    holder.innerHTML = sparklineSVG(item.spark);
    card.appendChild(holder.firstElementChild);
  }
  if (kind === "crypto" && item.leader) {
    const lead = el("div", "leader");
    lead.appendChild(document.createTextNode("Leader: "));
    lead.appendChild(el("strong", "", item.leader));
    card.appendChild(lead);
  }
  return card;
}
function metric(label, value) {
  const m = el("div", "metric");
  m.appendChild(el("div", "label", label));
  m.appendChild(el("div", `value ${pctClass(value)}`, fmtPct(value)));
  return m;
}
function metricRaw(label, value) {
  const m = el("div", "metric");
  m.appendChild(el("div", "label", label));
  m.appendChild(el("div", "value", value));
  return m;
}

function renderCrypto(data) { setUpdated("crypto-updated", data); renderCards(document.getElementById("crypto-cards"), data, "crypto"); }
function renderEquity(data) { setUpdated("equity-updated", data); renderCards(document.getElementById("equity-cards"), data, "equity"); }
function renderCards(container, data, kind) {
  container.innerHTML = "";
  if (!data || !Array.isArray(data.items) || data.items.length === 0) {
    container.appendChild(el("p", "empty", "Dati non ancora disponibili. Verranno aggiornati al prossimo ciclo di raccolta."));
    return;
  }
  data.items.forEach((item) => container.appendChild(rotationCard(item, kind)));
}

/* ---------- Piano di accumulo ---------- */
// The pick is deliberately rendered *with* its own refutation: the backtest says
// the rule earns no return edge, only allocation discipline. Showing the choice
// without that evidence would read as a forecast, which it is not.
function renderDca(data) {
  const pickRoot = document.getElementById("dca-pick");
  const evidenceRoot = document.getElementById("dca-evidence");
  const candRoot = document.getElementById("dca-candidates");
  const caveatRoot = document.getElementById("dca-caveats");
  [pickRoot, evidenceRoot, candRoot, caveatRoot].forEach((n) => { if (n) n.innerHTML = ""; });
  if (!pickRoot) return;
  if (!data) {
    pickRoot.appendChild(el("p", "empty", "Dati non ancora disponibili. Verranno aggiornati al prossimo ciclo di raccolta."));
    return;
  }
  setUpdated("dca-updated", data);
  pickRoot.appendChild(dcaPickCard(data));
  if (data.evidence) evidenceRoot.appendChild(dcaEvidenceCard(data.evidence));
  if (Array.isArray(data.candidates) && data.candidates.length) {
    candRoot.appendChild(dcaCandidatesCard(data));
  }
  if (Array.isArray(data.caveats) && data.caveats.length) {
    caveatRoot.appendChild(dcaCaveatsCard(data.caveats));
  }
}

function dcaPickCard(data) {
  const card = el("div", "card dca-card");
  const budget = data.sleeve_eur == null ? "" : ` da ${EUR0.format(data.sleeve_eur)}`;
  // Not "buy this today" — "if you were making this month's purchase now, this
  // is the leg that is furthest below plan". The wording carries that.
  card.appendChild(el("p", "mini-title", `Quota${budget} — se comprassi oggi`));
  const top = (data.items || [])[0];
  const head = el("div", "dca-head");
  head.appendChild(el("p", "dca-pick-symbol", data.pick || "—"));
  if (top && top.reason_it) head.appendChild(el("p", "dca-pick-why", top.reason_it));
  card.appendChild(head);
  if (data.holdings_estimated && data.holdings_note) {
    card.appendChild(el("p", "dca-warn", data.holdings_note.replace(/\*\*/g, "").replace(/`/g, "")));
  }
  const list = el("ul", "ranklist dca-list");
  (data.items || []).forEach((item) => list.appendChild(dcaAssetRow(item, item.symbol === data.pick)));
  card.appendChild(list);
  return card;
}

function dcaAssetRow(item, isPick) {
  const li = el("li", isPick ? "dca-row is-pick" : "dca-row");
  li.appendChild(el("span", "ri-rank", String(item.rank)));
  li.appendChild(el("span", "ri-name", item.symbol));
  // Two bars: where the weight sits now against where the plan wants it.
  const bars = el("div", "dca-bars");
  bars.appendChild(weightBar(item.weight_now, item.weight_target));
  li.appendChild(bars);
  const gap = el("span", "dca-gap");
  if (item.gap_pp == null) {
    gap.textContent = "n/d";
  } else {
    gap.textContent = `${item.gap_pp > 0 ? "+" : ""}${NF2.format(item.gap_pp)} pp`;
    gap.classList.add(item.gap_pp > 0 ? "pos" : "neg");
  }
  gap.title = "Scarto dal peso obiettivo: positivo = sotto peso, quindi tocca a lui.";
  li.appendChild(gap);
  return li;
}

function weightBar(now, target) {
  const wrap = el("div", "wbar");
  const track = el("div", "wtrack");
  const fill = el("div", "wfill");
  const pct = now == null ? 0 : Math.max(0, Math.min(1, now));
  fill.style.width = `${(pct * 100).toFixed(1)}%`;
  track.appendChild(fill);
  if (target != null) {
    const mark = el("div", "wtarget");
    mark.style.left = `${(Math.max(0, Math.min(1, target)) * 100).toFixed(1)}%`;
    mark.title = `Obiettivo ${(target * 100).toFixed(1)}%`;
    track.appendChild(mark);
  }
  wrap.appendChild(track);
  wrap.appendChild(el("span", "wpct", now == null ? "n/d" : `${(now * 100).toFixed(1)}%`));
  return wrap;
}

function dcaEvidenceCard(ev) {
  const card = el("div", "card dca-card");
  card.appendChild(el("p", "mini-title", "Cosa dice la verifica storica"));
  const sub = ev.window
    ? `Backtest sui flussi reali (${ev.window}, ${ev.n_purchases} acquisti, commissioni ${ev.fee_pct}%).`
    : "";
  if (sub) card.appendChild(el("p", "dca-sub", sub));
  const grid = el("div", "dca-evidence");
  grid.appendChild(evidenceItem(
    "neg", "Rendimento: nessun vantaggio",
    `${ev.random_percentile}° percentile contro 200 estrazioni casuali. Rapporto con la divisione in parti uguali ${ev.vs_split_full} sul periodo, ma ${ev.vs_split_first_half} nella prima metà e ${ev.vs_split_second_half} nella seconda: si alterna, quindi è rumore.`,
  ));
  grid.appendChild(evidenceItem(
    "pos", "Allocazione: vantaggio reale",
    `Distanza finale dal target ${ev.weight_drift_pp_rule} pp contro ${ev.weight_drift_pp_split} pp della divisione fissa. Nella metà out-of-sample ${ev.weight_drift_pp_rule_oos} pp contro ${ev.weight_drift_pp_split_oos} pp.`,
  ));
  grid.appendChild(evidenceItem(
    "neg", "Comprare il più forte è la scelta peggiore",
    `Il momentum sta al ${ev.momentum_random_percentile}° percentile, sotto il caso: è l'istinto più comune ed è quello che ha reso meno.`,
  ));
  card.appendChild(grid);
  return card;
}

function evidenceItem(tone, title, body) {
  const item = el("div", `dca-ev dca-ev-${tone}`);
  item.appendChild(el("p", "dca-ev-title", title));
  item.appendChild(el("p", "dca-ev-body", body));
  return item;
}

function dcaCandidatesCard(data) {
  const card = el("div", "card dca-card");
  card.appendChild(el("p", "mini-title", "Progetti: cosa c'è dietro il token"));
  card.appendChild(el("p", "dca-sub", "Per ogni progetto: cosa fa, se e come il valore che produce arriva a chi tiene il token, quanta offerta deve ancora arrivare, e se qualcuno lo sta ancora sviluppando. Descrizione, non previsione."));
  // Grouped by verdict, not by rank: the reason a project sits where it does is
  // the information, and a flat leaderboard hides it.
  const order = Array.isArray(data.verdict_order) ? data.verdict_order : [];
  const present = [...new Set(data.candidates.map((c) => c.verdict))];
  const groups = [...order.filter((v) => present.includes(v)), ...present.filter((v) => !order.includes(v))];
  groups.forEach((verdict) => {
    const rows = data.candidates.filter((c) => c.verdict === verdict);
    if (!rows.length) return;
    card.appendChild(el("p", "dca-group", rows[0].verdict_it || verdict));
    const list = el("div", "dca-projects");
    rows.forEach((c) => list.appendChild(projectCard(c)));
    card.appendChild(list);
  });
  const summary = data.rejected_summary || {};
  const labels = data.rejected_labels || {};
  const parts = Object.keys(summary).map((k) => `${labels[k] || k}: ${summary[k]}`);
  if (parts.length) card.appendChild(el("p", "dca-sub dca-rejected", `Escluse prima ancora di guardare i fondamentali — ${parts.join(" · ")}.`));
  return card;
}

function projectCard(c) {
  const box = el("div", `dca-project v-${(c.verdict || "unresearched").replace(/_/g, "-")}`);
  const head = el("div", "dca-project-head");
  head.appendChild(el("span", "dca-project-sym", c.symbol));
  head.appendChild(el("span", "dca-project-name", c.name));
  box.appendChild(head);
  if (c.what_it_does) box.appendChild(el("p", "dca-project-what", c.what_it_does));

  const accrual = [c.accrual_it, c.accrual_note].filter(Boolean).join(". ");
  box.appendChild(projectLine("Cattura del valore", accrual));

  let supply = c.emission_it || "";
  if (c.fdv_ratio != null && c.fdv_ratio > 1.01) {
    supply += `${supply ? " — " : ""}valutazione diluita ${NF2.format(c.fdv_ratio)} volte la capitalizzazione`;
  }
  box.appendChild(projectLine("Offerta", supply));

  let dev = c.dev_status_it || "";
  if (c.commits_4w != null && c.dev_status !== "no_repo_data") {
    dev += ` (${NF0.format(c.commits_4w)} commit in 4 settimane)`;
  }
  box.appendChild(projectLine("Sviluppo", dev));

  if (c.age_years != null) {
    const qualifier = c.age_source === "atl_lower_bound" ? "almeno " : "";
    box.appendChild(projectLine("Età", `${qualifier}${NF1.format(c.age_years)} anni`));
  }
  if (c.confidence != null && c.confidence < 1) {
    box.appendChild(el("p", "dca-project-warn", `Scheda incompleta: nota solo per ${pctArticle(c.confidence * 100)} dei criteri.`));
  }
  return box;
}

// "l'80%" but "il 65%": Italian elides the article before a vowel sound.
function pctArticle(pct) {
  const n = Math.round(pct);
  const article = /^(8|11)/.test(String(n)) ? "l'" : "il ";
  return `${article}${n}%`;
}

function projectLine(label, value) {
  const row = el("p", "dca-project-line");
  row.appendChild(el("span", "dca-project-label", label));
  row.appendChild(el("span", "dca-project-value", value || "n/d"));
  return row;
}

function dcaCaveatsCard(caveats) {
  const card = el("div", "card dca-card");
  card.appendChild(el("p", "mini-title", "Limiti"));
  const ul = el("ul", "dca-caveats");
  caveats.forEach((c) => ul.appendChild(el("li", null, c)));
  card.appendChild(ul);
  return card;
}

/* ---------- Overview ranklists ---------- */
function renderOverview(crypto, equity) {
  fillRanklist("overview-crypto", crypto, "crypto");
  fillRanklist("overview-equity", equity, "equity");
}
function fillRanklist(id, data, kind) {
  const ul = document.getElementById(id);
  ul.innerHTML = "";
  if (!data || !Array.isArray(data.items) || data.items.length === 0) {
    ul.appendChild(el("li", "", "Dati non ancora disponibili.")); return;
  }
  data.items.slice(0, 5).forEach((item) => {
    const li = document.createElement("li");
    li.appendChild(el("span", "ri-rank", `${item.rank}`));
    li.appendChild(el("span", "ri-name", item.name || "—"));
    const change = kind === "crypto" ? item.change_24h : item.change_5d;
    li.appendChild(el("span", `ri-change ${pctClass(change)}`, fmtPct(change)));
    ul.appendChild(li);
  });
}

/* ---------- Data health (cross-source) ----------
   Two independent price sources agreeing to ~0% IS the healthy signal, so the
   dots and divergence barely move — which reads as "frozen". Show the price
   (changes daily) and the update time as proof of life, and flag the card if
   it stops updating (self-staleness), so a dead cron is finally visible. */
function renderHealth(data) {
  const card = document.getElementById("health-card");
  const grid = document.getElementById("health-grid");
  if (!card || !grid) return;
  if (!data || !Array.isArray(data.assets) || data.assets.length === 0) { card.hidden = true; return; }
  card.hidden = false;

  const age = ageHours(data.generated_at);
  const stale = age !== null && age > HEALTH_STALE_HOURS;
  card.classList.toggle("is-stale", stale);

  const head = card.querySelector(".health-head");
  const old = head && head.querySelector(".health-fresh");
  if (old) old.remove();
  if (head && data.generated_at) {
    const tag = el("span", "health-fresh" + (stale ? " stale" : ""),
      stale ? `⚠ non aggiornato da ${Math.round(age)}h` : `aggiornato ${fmtDate(data.generated_at)}`);
    head.appendChild(tag);
  }

  grid.innerHTML = "";
  data.assets.forEach((a) => {
    const st = (a.status || "single_source").toLowerCase();
    const item = el("div", "health-item");
    item.appendChild(el("span", `health-dot h-${st}${stale ? " h-stale" : ""}`));
    const txt = el("div", "health-txt");
    const top = el("div", "health-top");
    top.appendChild(el("span", "health-sym", a.symbol));
    if (typeof a.yahoo === "number") top.appendChild(el("span", "health-price", `$${fmtPrice(a.yahoo)}`));
    txt.appendChild(top);
    const div = typeof a.divergence_pct === "number" ? `Δ ${NF.format(a.divergence_pct)}%` : "—";
    txt.appendChild(el("div", "health-meta", `${HEALTH_LABEL[st] || st} · ${div}`));
    item.appendChild(txt);
    item.title = a.reason || "";
    grid.appendChild(item);
  });
}

/* ---------- Events (move attribution) ----------
   A chronological timeline (newest day first) with a filter row, instead of a
   wall of per-asset cards: with the v2 thresholds the raw list runs to 150+
   moves, unreadable without filtering. State lives in EVENTS_STATE; every
   control re-renders only the list. */
const EVENTS_STATE = { moves: [], universe: "all", severity: "major", etype: "all", asset: "all" };

function renderEvents(data) {
  setUpdated("events-updated", data);
  const root = document.getElementById("events-list");
  root.innerHTML = "";
  if (data && data.market_pulse) root.appendChild(pulseBar(data.market_pulse));
  if (!data || !Array.isArray(data.assets) || data.assets.every((a) => !a.moves || a.moves.length === 0)) {
    // With the pulse above, an empty list reads as "calm market", not "broken".
    root.appendChild(el("p", "empty", "Nessun movimento anomalo recente, o storico news ancora in accumulo."));
    return;
  }
  // Flatten to one row per move, carrying the asset identity on each card.
  EVENTS_STATE.moves = [];
  data.assets.forEach((a) => (a.moves || []).forEach((m) => EVENTS_STATE.moves.push({
    universe: a.universe || "crypto", symbol: a.symbol, name: a.name, ...m,
  })));
  root.appendChild(eventsFilterBar());
  const list = el("div", "events-timeline");
  list.id = "events-timeline";
  root.appendChild(list);
  renderEventsList();
}

function moveEventTypes(m) {
  return (m.events || []).map((e) => (e.event_type || "other").toLowerCase());
}

function filteredMoves() {
  const s = EVENTS_STATE;
  return s.moves.filter((m) =>
    (s.universe === "all" || m.universe === s.universe)
    && (s.severity === "all" || (m.severity || "major") === s.severity)
    && (s.asset === "all" || m.symbol === s.asset)
    && (s.etype === "all" || moveEventTypes(m).includes(s.etype))
  );
}

function eventsFilterBar() {
  const s = EVENTS_STATE;
  const bar = el("div", "efilters");

  const seg = (label, options, key) => {
    const group = el("div", "efilter-group");
    group.appendChild(el("span", "efilter-label", label));
    const row = el("div", "efilter-seg");
    options.forEach(([value, text]) => {
      const b = el("button", "chip" + (s[key] === value ? " is-active" : ""), text);
      b.addEventListener("click", () => {
        s[key] = value;
        [...row.children].forEach((c, i) => c.classList.toggle("is-active", options[i][0] === value));
        renderEventsList();
      });
      row.appendChild(b);
    });
    group.appendChild(row);
    return group;
  };

  const nMajor = s.moves.filter((m) => (m.severity || "major") === "major").length;
  const nNotable = s.moves.length - nMajor;
  bar.appendChild(seg("Universo", [["all", "Tutti"], ["crypto", "Crypto"], ["equity", "Azionario"]], "universe"));
  bar.appendChild(seg("Rilevanza", [
    ["major", `Major (${nMajor})`],
    ["notable", `Degni di nota (${nNotable})`],
    ["all", "Tutti"],
  ], "severity"));

  const sel = (label, options, key) => {
    const group = el("div", "efilter-group");
    group.appendChild(el("span", "efilter-label", label));
    const select = el("select", "efilter-select");
    options.forEach(([value, text]) => {
      const o = el("option", "", text);
      o.value = value;
      if (s[key] === value) o.selected = true;
      select.appendChild(o);
    });
    select.addEventListener("change", () => { s[key] = select.value; renderEventsList(); });
    group.appendChild(select);
    return group;
  };

  const assets = [...new Map(s.moves.map((m) => [m.symbol, m.name])).entries()]
    .sort((a, b) => a[0].localeCompare(b[0]));
  bar.appendChild(sel("Asset", [["all", "Tutti"], ...assets.map(([sym, name]) => [sym, `${sym} — ${name}`])], "asset"));

  const types = [...new Set(s.moves.flatMap(moveEventTypes))].filter((t) => t !== "other").sort();
  if (types.length > 0) {
    bar.appendChild(sel("Tipo evento", [["all", "Tutti"], ...types.map((t) => [t, EVENT_TYPE_LABEL[t] || t])], "etype"));
  }

  const meta = el("div", "efilter-meta");
  meta.id = "efilter-meta";
  bar.appendChild(meta);
  return bar;
}

function renderEventsList() {
  const list = document.getElementById("events-timeline");
  if (!list) return;
  list.innerHTML = "";
  const moves = filteredMoves().sort((a, b) =>
    b.date.localeCompare(a.date)
    || (a.severity === b.severity ? 0 : a.severity === "major" ? -1 : 1)
    || Math.abs(b.return_pct) - Math.abs(a.return_pct)
  );

  const meta = document.getElementById("efilter-meta");
  const days = new Set(moves.map((m) => m.date));
  if (meta) meta.textContent = moves.length
    ? `${moves.length} movimenti in ${days.size} giornate`
    : "";

  if (moves.length === 0) {
    list.appendChild(el("p", "empty", "Nessun movimento con questi filtri. Prova ad allargare la rilevanza o il periodo."));
    return;
  }

  let currentDay = null;
  moves.forEach((m) => {
    if (m.date !== currentDay) {
      currentDay = m.date;
      const dayMoves = moves.filter((x) => x.date === currentDay);
      const head = el("div", "day-head");
      head.appendChild(el("span", "day-date", fmtDayLong(currentDay)));
      head.appendChild(el("span", "day-count", `${dayMoves.length} ${dayMoves.length === 1 ? "movimento" : "movimenti"}`));
      list.appendChild(head);
    }
    list.appendChild(moveCard(m));
  });
}

function fmtDayLong(t) {
  const d = new Date(t);
  return Number.isNaN(d.getTime()) ? t
    : d.toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

function pulseBar(pulse) {
  const bar = el("div", "pulse-bar");
  const entries = [["crypto", pulse.crypto], ["equity", pulse.equity]].filter(([, p]) => p);
  entries.forEach(([, p]) => {
    const item = el("div", "pulse-item");
    item.appendChild(el("span", "pulse-bench", p.benchmark || ""));
    if (typeof p.return_pct === "number")
      item.appendChild(el("span", `move-chg ${pctClass(p.return_pct)}`, `oggi ${fmtPct(p.return_pct)}`));
    if (typeof p.max_abs_z_recent === "number")
      item.appendChild(el("span", "pulse-meta", `max |z| ${p.recent_days || 10}gg: ${p.max_abs_z_recent}`));
    if (typeof p.days_since_last_major === "number")
      item.appendChild(el("span", "pulse-meta",
        p.days_since_last_major === 0 ? "evento major oggi" : `ultimo evento major: ${p.days_since_last_major}gg fa`));
    bar.appendChild(item);
  });
  return bar;
}

function moveCard(m) {
  const notable = m.severity === "notable";
  const card = el("div", notable ? "move-card move-notable" : "move-card");
  const head = el("div", "move-head");
  if (m.symbol) {
    const chip = el("span", "move-asset");
    chip.appendChild(el("strong", "", m.symbol));
    if (m.name && m.name !== m.symbol) chip.appendChild(el("span", "move-asset-name", m.name));
    head.appendChild(chip);
  }
  head.appendChild(el("span", `move-chg ${pctClass(m.return_pct)}`, fmtPct(m.return_pct)));
  const cls = m.classification || "unknown";
  head.appendChild(el("span", `class-badge ${CLASS_CLASS[cls] || "unknown"}`, CLASS_LABEL[cls] || cls));
  if (notable) head.appendChild(el("span", "class-badge notable", "Degno di nota"));
  if (m.coverage && m.coverage.spike)
    head.appendChild(el("span", "class-badge coverage", `Picco copertura (${m.coverage.count} titoli)`));
  if (typeof m.market_return_pct === "number") head.appendChild(el("span", "move-mkt", `mercato ${fmtPct(m.market_return_pct)}`));
  card.appendChild(head);

  if (Array.isArray(m.events) && m.events.length > 0) {
    const ul = el("ul", "events-ul");
    m.events.forEach((e) => {
      const li = document.createElement("li");
      li.appendChild(sentimentDot(e.sentiment));
      const txt = el("div");
      const title = el("div", "event-title");
      if (e.url) {
        const a = document.createElement("a");
        a.href = e.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = e.title || "(senza titolo)";
        title.appendChild(a);
      } else { title.textContent = e.title || "(senza titolo)"; }
      txt.appendChild(title);
      const meta = el("div", "event-meta");
      const etype = (e.event_type || "other").toLowerCase();
      if (etype !== "other") meta.appendChild(el("span", `etag etag-${etype}`, EVENT_TYPE_LABEL[etype] || etype));
      meta.appendChild(el("span", "event-src", e.source || ""));
      txt.appendChild(meta);
      li.appendChild(txt);
      ul.appendChild(li);
    });
    card.appendChild(ul);
  } else {
    card.appendChild(el("p", "no-news", "Nessuna notizia nella finestra (possibile evento di leva/liquidazioni, o storico ancora in accumulo)."));
  }
  return card;
}

function sentimentDot(s) {
  const dot = el("span", "sent-dot");
  let color = "var(--neutral)";
  if (typeof s === "number") color = s > 0.05 ? "var(--pos)" : s < -0.05 ? "var(--neg)" : "var(--neutral)";
  dot.style.background = color;
  return dot;
}

/* ---------- Paper trading (Fase 6) ----------
   Portafogli VIRTUALI: la strategia difensiva di momentum eseguita in avanti,
   fuori campione, col modello di costi del progetto. I portafogli nascono al
   primo run del cron notturno; prima di allora la sezione lo dice invece di
   mostrare zeri. */
function fmtEur(v, cents) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return (cents ? EUR2 : EUR0).format(v);
}

function renderPaper(data) {
  setUpdated("paper-updated", data);
  const disc = document.getElementById("paper-disclaimer");
  if (disc) disc.textContent = (data && data.disclaimer) || "";
  const root = document.getElementById("paper-cards");
  root.innerHTML = "";
  if (!data || !Array.isArray(data.scenarios) || data.scenarios.length === 0) {
    root.appendChild(el("p", "empty",
      "I portafogli virtuali nascono al primo aggiornamento notturno (cron 00:40 UTC). Ancora nessun dato: torna dopo il primo ciclo."));
    return;
  }
  const grid = el("div", "paper-grid");
  data.scenarios.forEach((s) => grid.appendChild(paperCard(s)));
  root.appendChild(grid);
}

function paperStat(label, value, cls) {
  const m = el("div", "paper-stat");
  m.appendChild(el("div", "label", label));
  m.appendChild(el("div", `value ${cls || ""}`, value));
  return m;
}

function paperCard(s) {
  const card = el("div", "paper-card");

  const head = el("div", "paper-head");
  const left = el("div");
  left.appendChild(el("div", "paper-name", fmtEur(s.initial_cash)));
  left.appendChild(el("div", "paper-sub", s.last_processed ? `al ${fmtDay(s.last_processed)}` : "in attesa del primo run"));
  head.appendChild(left);
  const badge = el("div", `paper-return ${pctClass(s.return_pct)}`, fmtPct(s.return_pct));
  head.appendChild(badge);
  card.appendChild(head);

  const stats = el("div", "paper-stats");
  stats.appendChild(paperStat("Valore", fmtEur(s.equity, true)));
  stats.appendChild(paperStat("Liquidità", fmtEur(s.cash, true)));
  stats.appendChild(paperStat("P/L realizzato", fmtEur(s.realized_pnl, true), pctClass(s.realized_pnl)));
  stats.appendChild(paperStat("Commissioni", fmtEur(s.fees_paid, true)));
  card.appendChild(stats);

  if (s.fully_marked === false) {
    card.appendChild(el("p", "paper-note", "Valorizzazione parziale: prezzo non disponibile per alcuni asset."));
  }

  if (Array.isArray(s.curve) && s.curve.length > 1) {
    const holder = el("div", "paper-spark");
    holder.innerHTML = sparklineSVG(s.curve.map((p) => p.v));
    if (holder.firstElementChild) card.appendChild(holder);
  }

  if (s.metrics) {
    const m = s.metrics;
    const row = el("div", "paper-metrics");
    row.appendChild(paperMetric("Sharpe", m.sharpe === null || m.sharpe === undefined ? "—" : NF.format(m.sharpe)));
    row.appendChild(paperMetric("Max drawdown", m.max_drawdown_pct === null || m.max_drawdown_pct === undefined ? "—" : `${m.max_drawdown_pct.toFixed(1)}%`));
    row.appendChild(paperMetric("Tempo sott'acqua", m.time_underwater_pct === null || m.time_underwater_pct === undefined ? "—" : `${m.time_underwater_pct.toFixed(0)}%`));
    row.appendChild(paperMetric("Giorni", `${m.n_days}`));
    card.appendChild(row);
  } else {
    card.appendChild(el("p", "paper-note", "Metriche di rischio dopo qualche giorno di storico (servono ≥5 osservazioni)."));
  }

  card.appendChild(paperPositions(s.positions));

  const targets = s.targets && Object.keys(s.targets).length ? s.targets : null;
  if (targets) {
    const wrap = el("div", "paper-targets");
    wrap.appendChild(el("span", "paper-targets-label", "Target"));
    Object.entries(targets).sort((a, b) => a[0].localeCompare(b[0])).forEach(([sym, w]) => {
      wrap.appendChild(el("span", "chip", `${sym} ${(w * 100).toFixed(0)}%`));
    });
    card.appendChild(wrap);
  }

  if (Array.isArray(s.recent_orders) && s.recent_orders.length) {
    card.appendChild(paperOrders(s.recent_orders));
  }
  return card;
}

function paperMetric(label, value) {
  const m = el("div", "paper-metric");
  m.appendChild(el("div", "label", label));
  m.appendChild(el("div", "value", value));
  return m;
}

function paperPositions(positions) {
  const box = el("div", "paper-positions");
  box.appendChild(el("h4", "paper-subtitle", "Posizioni"));
  if (!Array.isArray(positions) || positions.length === 0) {
    box.appendChild(el("p", "paper-note", "Nessuna posizione aperta: interamente in liquidità (posizione difensiva)."));
    return box;
  }
  const table = el("table", "paper-table");
  const thead = el("tr");
  ["Asset", "Quantità", "Prezzo medio", "Prezzo", "Valore", "P/L"].forEach((h, i) => {
    thead.appendChild(el("th", i === 0 ? "" : "num", h));
  });
  const head = document.createElement("thead");
  head.appendChild(thead);
  table.appendChild(head);
  const body = document.createElement("tbody");
  positions.forEach((p) => {
    const tr = el("tr");
    tr.appendChild(el("td", "", p.symbol));
    tr.appendChild(el("td", "num", fmtNum(p.qty)));
    tr.appendChild(el("td", "num", fmtEur(p.avg_cost, true)));
    tr.appendChild(el("td", "num", p.price === null ? "—" : fmtEur(p.price, true)));
    tr.appendChild(el("td", "num", p.value === null ? "—" : fmtEur(p.value, true)));
    tr.appendChild(el("td", `num ${pctClass(p.pnl_pct)}`, p.pnl_pct === null ? "—" : fmtPct(p.pnl_pct)));
    body.appendChild(tr);
  });
  table.appendChild(body);
  const wrap = el("div", "paper-table-wrap");
  wrap.appendChild(table);
  box.appendChild(wrap);
  return box;
}

function paperOrders(orders) {
  const box = el("details", "paper-orders");
  const summary = document.createElement("summary");
  summary.textContent = `Ultimi ordini (${orders.length})`;
  box.appendChild(summary);
  const list = el("ul", "paper-order-list");
  [...orders].reverse().forEach((o) => {
    const li = el("li", `paper-order ${o.side === "buy" ? "buy" : "sell"}`);
    li.appendChild(el("span", "po-date", o.created_at));
    li.appendChild(el("span", "po-side", o.side === "buy" ? "Acquisto" : "Vendita"));
    li.appendChild(el("span", "po-sym", o.symbol));
    li.appendChild(el("span", "po-qty", fmtNum(o.qty)));
    li.appendChild(el("span", `po-status st-${o.status}`, ORDER_STATUS_LABEL[o.status] || o.status));
    list.appendChild(li);
  });
  box.appendChild(list);
  return box;
}

/* ---------- Paper replay (historical, in-sample) ----------
   Backward-looking illustration of the SAME strategy through the SAME broker.
   Kept visually distinct from the forward live scenarios and labelled as
   in-sample so it can't be mistaken for the forward track record. */
function renderReplay(data) {
  const root = document.getElementById("paper-replay");
  if (!root) return;
  root.innerHTML = "";
  if (!data || !data.scenario) return;  // absent until the first cron run
  const s = data.scenario;

  const head = el("div", "replay-head");
  const title = el("div");
  title.appendChild(el("h3", "replay-title", data.title || "Replay storico"));
  title.appendChild(el("p", "replay-sub",
    "Stessa strategia, stesso broker (costi + fill a t+1), eseguita sullo storico. "
    + "Backward-looking e in-sample: mostra il comportamento passato, non è il track record forward."));
  head.appendChild(title);
  head.appendChild(el("div", `paper-return ${pctClass(s.return_pct)}`, fmtPct(s.return_pct)));

  const card = el("div", "replay-card");
  card.appendChild(head);

  const curve = Array.isArray(s.curve) ? s.curve : [];
  if (curve.length > 1) {
    const first = curve[0], last = curve[curve.length - 1];
    const meta = el("div", "replay-meta");
    meta.appendChild(el("span", "", `dal ${fmtDay(first.t)} al ${fmtDay(last.t)}`));
    meta.appendChild(el("span", "", `${curve.length} giorni`));
    if (typeof data.lookback === "number") meta.appendChild(el("span", "", `lookback ${data.lookback}g`));
    if (Array.isArray(data.symbols) && data.symbols.length) meta.appendChild(el("span", "", data.symbols.join(" · ")));
    card.appendChild(meta);

    const chart = el("div", "replay-chart");
    chart.innerHTML = sparklineSVG(curve.map((p) => p.v));
    if (chart.firstElementChild) card.appendChild(chart);
  }

  if (s.metrics) {
    const m = s.metrics;
    const row = el("div", "paper-metrics");
    row.appendChild(paperMetric("Sharpe", m.sharpe === null || m.sharpe === undefined ? "—" : NF.format(m.sharpe)));
    row.appendChild(paperMetric("Max drawdown", m.max_drawdown_pct === null || m.max_drawdown_pct === undefined ? "—" : `${m.max_drawdown_pct.toFixed(1)}%`));
    row.appendChild(paperMetric("Tempo sott'acqua", m.time_underwater_pct === null || m.time_underwater_pct === undefined ? "—" : `${m.time_underwater_pct.toFixed(0)}%`));
    row.appendChild(paperMetric("Giorni", `${m.n_days}`));
    card.appendChild(row);
  }

  root.appendChild(card);
}

/* ---------- Education ---------- */
function renderEducation(data) {
  const root = document.getElementById("education");
  root.innerHTML = "";
  if (!data || !Array.isArray(data.levels) || data.levels.length === 0) {
    root.appendChild(el("p", "empty", "Lezioni non disponibili.")); return;
  }
  data.levels.forEach((level) => {
    const block = el("div", "edu-level");
    const head = el("div", "edu-level-head");
    head.appendChild(el("span", "edu-badge", level.id));
    head.appendChild(el("h3", "", level.name));
    head.appendChild(el("span", "sub", level.subtitle || ""));
    block.appendChild(head);
    if (Array.isArray(level.chapters) && level.chapters.length > 0) {
      level.chapters.forEach((ch) => block.appendChild(chapterFromHtml(ch.title || ch.slug || "Capitolo", ch.html || "")));
    } else if (level.intro_html) {
      block.appendChild(chapterFromHtml("Panoramica del livello", level.intro_html));
      block.appendChild(el("p", "edu-empty", "Altri capitoli in arrivo."));
    } else {
      block.appendChild(el("p", "edu-empty", "Capitoli in arrivo."));
    }
    root.appendChild(block);
  });
}
function chapterFromHtml(title, html) {
  const details = el("details", "chapter");
  const summary = document.createElement("summary");
  summary.textContent = title;
  details.appendChild(summary);
  const body = el("div", "chapter-body");
  body.innerHTML = html; // trusted: built at build time from our own repo
  details.appendChild(body);
  return details;
}

/* ---------- Opportunità: classifica descrittiva degli ETF settoriali (WP5) ----------
   The payload declares `predictive: false` and ships every forecast field as
   null (ADR-036). This renderer is built around that fact: no probability
   column exists, the non-predictive notice is rendered as a permanent banner
   (never a tooltip), and the "Modello" section below carries the numbers that
   justify the omission. Sorting and row expansion are the only interactions. */

const RANKING_STATE = { report: null, sort: { key: "rank", dir: "asc" }, open: new Set() };
const MODEL_STATE = { model: null, backtest: null, horizon: 20, curve: "logistic" };

const REGIME_LABEL = {
  bull_low_vol: "rialzista, volatilità bassa",
  bull_high_vol: "rialzista, volatilità alta",
  bear_low_vol: "ribassista, volatilità bassa",
  bear_high_vol: "ribassista, volatilità alta",
  unknown: "non determinato",
};
const FACTOR_LABEL = {
  rel_ret_60: "rendimento relativo a 60 sedute contro SPY",
  rel_ret_20: "rendimento relativo a 20 sedute contro SPY",
  rel_ret_126: "rendimento relativo a 126 sedute contro SPY",
};
const FACTOR_DIRECTION = { positive: "sopra il benchmark", negative: "sotto il benchmark" };
const MODEL_LABEL = {
  momentum: "Momentum rel. 60g",
  logistic: "Logistica",
  ridge: "Ridge",
  random: "Ranker casuale",
  climatology: "Climatologia",
};
const CONFIDENCE_LABEL = {
  not_applicable: "non applicabile",
  low: "bassa",
  medium: "media",
  high: "alta",
};
// Data older than this many days means the weekly run has been looking at a
// frozen feed: worth flagging in the row even when the payload is "ok".
const RANK_STALE_DAYS = 8;

const RANK_COLUMNS = [
  { key: "rank", label: "#", cls: "num", type: "num" },
  { key: "name", label: "ETF", cls: "", type: "str" },
  { key: "selection_score", label: "Momentum rel. 60g", cls: "num", type: "num" },
  { key: "selection_rank_pct", label: "Percentile", cls: "num", type: "num" },
  { key: "realized_vol_60", label: "Vol. 60g", cls: "num", type: "num" },
  { key: "close", label: "Prezzo", cls: "num", type: "num" },
  { key: "freshness_days", label: "Dati", cls: "num", type: "num" },
  { key: "target_weight", label: "Peso", cls: "num", type: "num" },
];

function fmtSignedPct(v, digits) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const n = v * 100;
  return `${n > 0 ? "+" : ""}${(digits === 1 ? NF1 : NF2).format(n)}%`;
}
function fmtPlainPct(v, digits) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${(digits === 0 ? NF0 : digits === 1 ? NF1 : NF2).format(v * 100)}%`;
}
function fmtDays(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${NF1.format(v)} g`;
}
function fmtRatio(v, digits) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toLocaleString("it-IT", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
function regimeLabel(code) {
  return REGIME_LABEL[code] || REGIME_LABEL.unknown;
}

function renderRanking(report) {
  RANKING_STATE.report = report;
  RANKING_STATE.open = new Set();
  setUpdated("ranking-updated", report);

  const banners = document.getElementById("ranking-banners");
  const meta = document.getElementById("ranking-meta");
  const table = document.getElementById("ranking-table");
  const past = document.getElementById("ranking-past");
  const foot = document.getElementById("ranking-disclaimer");
  if (!banners || !meta || !table || !past || !foot) return;
  [banners, meta, table, past, foot].forEach((n) => { n.innerHTML = ""; });

  // Payload assente: stato vuoto esplicito, mai una pagina rotta.
  if (!report) {
    banners.appendChild(el("p", "empty",
      "Dati non ancora disponibili: la classifica viene emessa dal ciclo settimanale (lunedì mattina). Torna dopo il primo aggiornamento."));
    return;
  }

  banners.appendChild(nonPredictiveBanner(report));
  if (report.status && report.status !== "ok") banners.appendChild(staleBanner(report));

  meta.appendChild(rankingMeta(report));

  const items = Array.isArray(report.items) ? report.items : [];
  if (items.length === 0) {
    table.appendChild(el("p", "empty", report.status && report.status !== "ok"
      ? "Nessuna classifica emessa in questo ciclo: i dati di prezzo non erano abbastanza recenti per calcolarla."
      : "Nessun ETF classificabile in questo ciclo."));
  } else {
    table.appendChild(rankingTable());
  }

  past.appendChild(pastPredictionsBlock(report));
  foot.appendChild(el("p", "rk-fineprint", report.disclaimer || ""));
}

function nonPredictiveBanner(report) {
  const box = el("div", "rk-banner rk-banner-notice");
  box.setAttribute("role", "note");
  box.appendChild(el("p", "rk-banner-title", "Classifica descrittiva, non una previsione"));
  if (report.non_predictive_notice) box.appendChild(el("p", "rk-banner-text", report.non_predictive_notice));
  if (report.non_predictive_reason) box.appendChild(el("p", "rk-banner-text muted", report.non_predictive_reason));
  return box;
}

function staleBanner(report) {
  const box = el("div", "rk-banner rk-banner-stale");
  box.setAttribute("role", "alert");
  box.appendChild(el("p", "rk-banner-title", "Dati non aggiornati, nessun nuovo ranking emesso"));
  box.appendChild(el("p", "rk-banner-text",
    report.stale_notice || "Dati non aggiornati: nessun nuovo ranking è stato emesso e il portafoglio non è stato ribilanciato."));
  if (report.status_reason) box.appendChild(el("p", "rk-banner-text muted", report.status_reason));
  return box;
}

function metaItem(label, value, note) {
  const cell = el("div", "rk-meta-item");
  cell.appendChild(el("span", "rk-meta-label", label));
  cell.appendChild(el("span", "rk-meta-value", value));
  if (note) cell.appendChild(el("span", "rk-meta-note", note));
  return cell;
}

function rankingMeta(report) {
  const card = el("div", "card rk-meta");
  const grid = el("div", "rk-meta-grid");
  grid.appendChild(metaItem("Regola", report.rule_version || "—", report.rule_description || ""));
  grid.appendChild(metaItem("Dati al", report.as_of ? fmtDay(report.as_of) : "—",
    report.benchmark ? `benchmark ${report.benchmark}` : ""));
  grid.appendChild(metaItem("Regime di mercato", regimeLabel(report.regime),
    "classificato dai soli prezzi (trend × volatilità)"));
  const notScoreable = Array.isArray(report.not_scoreable) ? report.not_scoreable : [];
  grid.appendChild(metaItem("Universo", `${report.universe_size ?? 0} ETF`,
    !report.universe_size ? "nessun ETF classificato in questo ciclo"
      : notScoreable.length ? `non classificabili: ${notScoreable.join(", ")}` : "tutti classificabili"));
  grid.appendChild(metaItem("Liquidità del paper portfolio",
    report.cash_weight === null || report.cash_weight === undefined ? "—" : fmtPlainPct(report.cash_weight, 0),
    "portafoglio virtuale, nessun denaro reale"));
  grid.appendChild(metaItem("Probabilità stimata", "non disponibile",
    report.confidence_threshold_note || "nessuna probabilità calibrata sotto questa regola"));
  card.appendChild(grid);
  return card;
}

function sortedItems() {
  const items = [...(RANKING_STATE.report.items || [])];
  const { key, dir } = RANKING_STATE.sort;
  const col = RANK_COLUMNS.find((c) => c.key === key) || RANK_COLUMNS[0];
  const sign = dir === "asc" ? 1 : -1;
  items.sort((a, b) => {
    const x = a[col.key], y = b[col.key];
    // I valori mancanti restano in fondo in entrambi i versi: un "—" in cima
    // sembrerebbe un primo posto.
    const xNull = x === null || x === undefined, yNull = y === null || y === undefined;
    if (xNull && yNull) return (a.rank || 0) - (b.rank || 0);
    if (xNull) return 1;
    if (yNull) return -1;
    if (col.type === "str") return sign * String(x).localeCompare(String(y), "it");
    return sign * (Number(x) - Number(y));
  });
  return items;
}

function rankingTable() {
  const wrap = el("div", "card rk-table-card");
  const scroller = el("div", "rk-table-wrap");
  const table = el("table", "rk-table");

  const thead = document.createElement("thead");
  const hrow = el("tr");
  RANK_COLUMNS.forEach((col) => {
    const th = el("th", col.cls);
    const active = RANKING_STATE.sort.key === col.key;
    const btn = el("button", `rk-sort${active ? " is-active" : ""}`, col.label);
    btn.type = "button";
    btn.setAttribute("aria-label", `Ordina per ${col.label}`);
    if (active) btn.appendChild(el("span", "rk-sort-arrow", RANKING_STATE.sort.dir === "asc" ? "▲" : "▼"));
    btn.addEventListener("click", () => {
      const s = RANKING_STATE.sort;
      if (s.key === col.key) s.dir = s.dir === "asc" ? "desc" : "asc";
      else { s.key = col.key; s.dir = col.key === "rank" || col.key === "name" ? "asc" : "desc"; }
      const root = document.getElementById("ranking-table");
      root.innerHTML = "";
      root.appendChild(rankingTable());
    });
    th.appendChild(btn);
    hrow.appendChild(th);
  });
  thead.appendChild(hrow);
  table.appendChild(thead);

  const body = document.createElement("tbody");
  sortedItems().forEach((item) => {
    body.appendChild(rankingRow(item));
    body.appendChild(rankingDetailRow(item));
  });
  table.appendChild(body);

  scroller.appendChild(table);
  wrap.appendChild(scroller);
  wrap.appendChild(el("p", "rk-fineprint",
    "Clicca su una riga per aprire i dati osservati e gli esiti passati di quell'ETF. Le intestazioni ordinano la tabella."));
  return wrap;
}

function rankingRow(item) {
  const key = item.asset;
  const tr = el("tr", `rk-row${item.selected ? " is-selected" : ""}`);
  tr.tabIndex = 0;
  tr.setAttribute("role", "button");
  tr.setAttribute("aria-expanded", RANKING_STATE.open.has(key) ? "true" : "false");

  const rank = el("td", "num rk-rank");
  rank.appendChild(el("span", "rk-caret", RANKING_STATE.open.has(key) ? "▾" : "▸"));
  rank.appendChild(el("span", "", `${item.rank ?? "—"}`));
  tr.appendChild(rank);

  const name = el("td", "rk-name");
  name.appendChild(el("span", "rk-name-main", item.name || item.asset));
  if (item.ticker) name.appendChild(el("span", "rk-ticker", item.ticker));
  if (item.selected) name.appendChild(el("span", "rk-tag", "in portafoglio virtuale"));
  tr.appendChild(name);

  tr.appendChild(el("td", `num ${pctClass(item.selection_score)}`, fmtSignedPct(item.selection_score, 1)));
  tr.appendChild(el("td", "num", item.selection_rank_pct === null || item.selection_rank_pct === undefined
    ? "—" : `${NF0.format(item.selection_rank_pct * 100)}°`));
  tr.appendChild(el("td", "num", fmtPlainPct(item.realized_vol_60, 1)));
  tr.appendChild(el("td", "num", fmtRatio(item.close, 2)));

  const fresh = el("td", "num");
  const days = item.freshness_days;
  const stale = days !== null && days !== undefined && days > RANK_STALE_DAYS;
  fresh.appendChild(el("span", stale ? "rk-fresh-warn" : "", fmtDays(days)));
  tr.appendChild(fresh);

  tr.appendChild(el("td", "num", item.target_weight ? fmtPlainPct(item.target_weight, 0) : "—"));

  const toggle = () => toggleRankingRow(key);
  tr.addEventListener("click", toggle);
  tr.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); toggle(); }
  });
  return tr;
}

function toggleRankingRow(key) {
  if (RANKING_STATE.open.has(key)) RANKING_STATE.open.delete(key);
  else RANKING_STATE.open.add(key);
  const root = document.getElementById("ranking-table");
  root.innerHTML = "";
  root.appendChild(rankingTable());
}

function rankingDetailRow(item) {
  const tr = el("tr", "rk-detail-row");
  if (!RANKING_STATE.open.has(item.asset)) tr.hidden = true;
  const td = el("td", "rk-detail-cell");
  td.colSpan = RANK_COLUMNS.length;
  td.appendChild(rankingDetail(item));
  tr.appendChild(td);
  return tr;
}

function detailFact(label, value) {
  const row = el("div", "rk-fact");
  row.appendChild(el("span", "rk-fact-label", label));
  row.appendChild(el("span", "rk-fact-value", value));
  return row;
}

function rankingDetail(item) {
  const box = el("div", "rk-detail");

  const forecast = el("div", "rk-detail-block rk-detail-forecast");
  forecast.appendChild(el("h4", "rk-detail-title", "Probabilità e attese"));
  forecast.appendChild(detailFact("Probabilità stimata di battere il benchmark", "non disponibile"));
  forecast.appendChild(detailFact("Rendimento in eccesso atteso", "non disponibile"));
  forecast.appendChild(detailFact("Volatilità attesa", "non disponibile"));
  forecast.appendChild(detailFact("Confidenza", CONFIDENCE_LABEL[item.confidence] || "non applicabile"));
  forecast.appendChild(el("p", "rk-fineprint",
    "Non è un dato mancante per un errore: la validazione fuori campione non ha prodotto probabilità affidabili, quindi non ne viene pubblicata nessuna (ADR-034/036). Non è sufficiente per un segnale."));
  box.appendChild(forecast);

  const observed = el("div", "rk-detail-block");
  observed.appendChild(el("h4", "rk-detail-title", "Stato osservato oggi"));
  observed.appendChild(detailFact("Momentum relativo a 60 sedute", fmtSignedPct(item.selection_score, 2)));
  observed.appendChild(detailFact("Posizione nella classifica",
    `${item.rank ?? "—"} su ${RANKING_STATE.report.universe_size ?? "—"}`));
  observed.appendChild(detailFact("Percentile cross-sezionale",
    item.selection_rank_pct === null || item.selection_rank_pct === undefined
      ? "—" : `${NF0.format(item.selection_rank_pct * 100)}°`));
  observed.appendChild(detailFact("Volatilità realizzata a 60 sedute", fmtPlainPct(item.realized_vol_60, 1)));
  observed.appendChild(detailFact("Ultima chiusura", fmtRatio(item.close, 2)));
  observed.appendChild(detailFact("Regime di mercato", regimeLabel(item.regime)));
  observed.appendChild(detailFact("Età del dato di prezzo", fmtDays(item.freshness_days)));
  observed.appendChild(detailFact("Peso nel portafoglio virtuale",
    item.target_weight ? fmtPlainPct(item.target_weight, 0) : "nessuno"));
  const factors = Array.isArray(item.top_factors) ? item.top_factors : [];
  if (factors.length) {
    observed.appendChild(detailFact("Fattori che determinano la posizione", factors
      .map((f) => `${FACTOR_LABEL[f.name] || f.name} (${FACTOR_DIRECTION[f.direction] || f.direction})`)
      .join("; ")));
  }
  box.appendChild(observed);

  box.appendChild(assetOutcomes(item.asset));

  const caveat = el("div", "rk-detail-block rk-detail-caveat");
  caveat.appendChild(el("h4", "rk-detail-title", "Cosa tenere a mente"));
  const list = el("ul", "rk-caveats");
  [
    "La stessa regola, misurata fuori campione su 14 950 osservazioni, si è comportata come il caso: essere in cima a questa tabella non ha mostrato alcun vantaggio storico ripetibile.",
    "Storicamente, in condizioni simili, il settore mediano ha battuto SPY meno di una volta su due (0,489 a 20 sedute): la classifica non sposta questa frequenza di base.",
    "L'ordinamento cambia ogni settimana; inseguirlo genera costi di transazione che il backtest ha misurato come sufficienti a mangiare lo spread lordo.",
  ].forEach((t) => list.appendChild(el("li", "", t)));
  caveat.appendChild(list);
  box.appendChild(caveat);

  return box;
}

function assetOutcomes(asset) {
  const box = el("div", "rk-detail-block");
  box.appendChild(el("h4", "rk-detail-title", "Classifiche passate di questo ETF, con esito"));
  const rows = (RANKING_STATE.report.past_predictions || []).filter((r) => r.asset === asset);
  if (!rows.length) {
    box.appendChild(el("p", "rk-fineprint",
      "Nessun esito ancora risolto: ogni riga emessa si chiude solo dopo l'orizzonte (20 o 60 sedute). Il track record forward parte da qui e resterà visibile anche quando sarà sfavorevole."));
    return box;
  }
  const table = el("table", "rk-mini-table");
  const head = document.createElement("thead");
  const hr = el("tr");
  ["Emessa il", "Orizzonte", "Posizione", "Rendimento in eccesso", "Esito"].forEach((h, i) => {
    hr.appendChild(el("th", i === 0 ? "" : "num", h));
  });
  head.appendChild(hr);
  table.appendChild(head);
  const body = document.createElement("tbody");
  rows.slice(0, 12).forEach((r) => {
    const tr = el("tr");
    tr.appendChild(el("td", "", fmtDay(r.emitted_at)));
    tr.appendChild(el("td", "num", `${r.horizon_days} sedute`));
    tr.appendChild(el("td", "num", r.selection_rank ? `${r.selection_rank}°` : "—"));
    tr.appendChild(el("td", `num ${pctClass(r.excess_return)}`, fmtSignedPct(r.excess_return, 2)));
    tr.appendChild(el("td", "num", r.outperformed === null || r.outperformed === undefined
      ? "—" : (r.outperformed ? "sopra il benchmark" : "sotto il benchmark")));
    body.appendChild(tr);
  });
  table.appendChild(body);
  const wrap = el("div", "rk-table-wrap");
  wrap.appendChild(table);
  box.appendChild(wrap);
  return box;
}

function pastPredictionsBlock(report) {
  const card = el("div", "card rk-past");
  card.appendChild(el("h3", "rk-h3", "Esiti delle classifiche già emesse"));
  const rows = Array.isArray(report.past_predictions) ? report.past_predictions : [];
  if (!rows.length) {
    card.appendChild(el("p", "rk-fineprint",
      "Nessuna riga risolta finora. Ogni settimana il sistema registra la classifica emessa e la chiude a 20 e 60 sedute: gli esiti compariranno qui man mano, favorevoli o meno."));
    return card;
  }
  const hits = rows.filter((r) => r.outperformed === true).length;
  card.appendChild(el("p", "rk-fineprint",
    `${rows.length} righe risolte, di cui ${hits} sopra il benchmark. Conteggi grezzi su un campione piccolo: non sono un verdetto.`));
  const table = el("table", "rk-mini-table");
  const head = document.createElement("thead");
  const hr = el("tr");
  ["Emessa il", "ETF", "Orizzonte", "Posizione", "In portafoglio", "Rendimento in eccesso", "Esito"].forEach((h, i) => {
    hr.appendChild(el("th", i <= 1 ? "" : "num", h));
  });
  head.appendChild(hr);
  table.appendChild(head);
  const body = document.createElement("tbody");
  rows.slice(0, 30).forEach((r) => {
    const tr = el("tr");
    tr.appendChild(el("td", "", fmtDay(r.emitted_at)));
    tr.appendChild(el("td", "", r.asset));
    tr.appendChild(el("td", "num", `${r.horizon_days}`));
    tr.appendChild(el("td", "num", r.selection_rank ? `${r.selection_rank}°` : "—"));
    tr.appendChild(el("td", "num", r.selected ? "sì" : "no"));
    tr.appendChild(el("td", `num ${pctClass(r.excess_return)}`, fmtSignedPct(r.excess_return, 2)));
    tr.appendChild(el("td", "num", r.outperformed === null || r.outperformed === undefined
      ? "—" : (r.outperformed ? "sopra" : "sotto")));
    body.appendChild(tr);
  });
  table.appendChild(body);
  const wrap = el("div", "rk-table-wrap");
  wrap.appendChild(table);
  card.appendChild(wrap);
  return card;
}

/* ---------- Modello: cosa è stato validato e cosa ha fallito (WP5) ---------- */

function renderRankingModel(model, backtest) {
  MODEL_STATE.model = model;
  MODEL_STATE.backtest = backtest;
  setUpdated("model-updated", model);

  const verdict = document.getElementById("model-verdict");
  const training = document.getElementById("model-training");
  const metrics = document.getElementById("model-metrics");
  const reliability = document.getElementById("model-reliability");
  const forward = document.getElementById("model-forward");
  if (!verdict || !training || !metrics || !reliability || !forward) return;
  [verdict, training, metrics, reliability, forward].forEach((n) => { n.innerHTML = ""; });

  if (!model && !backtest) {
    verdict.appendChild(el("p", "empty",
      "Stato della validazione non ancora disponibile: comparirà dopo il primo ciclo settimanale."));
    return;
  }

  if (model) {
    if (model.status && model.status !== "ok") verdict.appendChild(staleBanner({
      stale_notice: "Dati non aggiornati: nessun nuovo ranking è stato emesso e le metriche qui sotto restano quelle dell'ultimo ciclo valido.",
      status_reason: model.status_reason,
    }));
    verdict.appendChild(verdictCard(model));
    training.appendChild(trainingCard(model, backtest));
  }
  if (backtest) {
    metrics.appendChild(metricsCard());
    reliability.appendChild(reliabilityCard());
  } else {
    metrics.appendChild(el("p", "rk-fineprint",
      "Il report completo della validazione (metriche per modello e reliability) non è disponibile in questo momento; il verdetto qui sopra viene dal payload del ciclo settimanale."));
  }
  if (model) forward.appendChild(forwardCard(model));
}

function verdictCard(model) {
  const card = el("div", "card rk-verdict");
  const bar = model.adoption_bar || {};
  const head = el("div", "rk-verdict-head");
  head.appendChild(el("h3", "rk-h3", `Verdetto ${bar.reference || "ADR-034"}: barra di adozione non superata`));
  head.appendChild(el("span", "rk-verdict-pill", bar.passed ? "superata" : "non superata"));
  card.appendChild(head);

  const grid = el("div", "rk-verdict-grid");
  const req = el("div", "rk-verdict-block");
  req.appendChild(el("h4", "rk-detail-title", "Cosa serviva per adottare il modello"));
  req.appendChild(el("p", "rk-verdict-text", bar.requirement || "—"));
  grid.appendChild(req);
  const out = el("div", "rk-verdict-block");
  out.appendChild(el("h4", "rk-detail-title", "Cosa è successo"));
  out.appendChild(el("p", "rk-verdict-text", bar.outcome || "—"));
  grid.appendChild(out);
  const cal = el("div", "rk-verdict-block");
  cal.appendChild(el("h4", "rk-detail-title", "Calibrazione delle probabilità"));
  const calibration = model.calibration || {};
  cal.appendChild(el("p", "rk-verdict-text",
    `${calibration.available ? "Disponibile" : "Non disponibile"} — metodo: ${calibration.method || "—"}. ${calibration.reason || ""}`));
  grid.appendChild(cal);
  const thr = el("div", "rk-verdict-block");
  thr.appendChild(el("h4", "rk-detail-title", "Soglia di confidenza"));
  thr.appendChild(el("p", "rk-verdict-text", model.confidence_threshold_note || "—"));
  grid.appendChild(thr);
  card.appendChild(grid);

  if (model.non_predictive_reason) {
    card.appendChild(el("p", "rk-fineprint", model.non_predictive_reason));
  }
  return card;
}

function trainingCard(model, backtest) {
  const card = el("div", "card rk-meta");
  const grid = el("div", "rk-meta-grid");
  const validation = model.validation || {};
  const folds = firstResultFolds(backtest);
  const trainStart = folds.length ? folds[0].train_start : null;
  const testEnd = folds.length ? folds[folds.length - 1].test_end : null;

  grid.appendChild(metaItem("Periodo coperto dalla validazione",
    trainStart && testEnd ? `${trainStart} → ${testEnd}` : "—",
    folds.length ? `${folds.length} fold walk-forward con embargo` : "walk-forward con embargo"));
  grid.appendChild(metaItem("Finestra di addestramento",
    validation.train_weeks ? `${validation.train_weeks} settimane` : "—",
    validation.test_weeks ? `test fuori campione: ${validation.test_weeks} settimane per fold` : ""));
  grid.appendChild(metaItem("Ultimo ricalcolo della validazione",
    validation.generated_at ? fmtDate(validation.generated_at) : (backtest && backtest.generated_at ? fmtDate(backtest.generated_at) : "—"),
    validation.age_days === null || validation.age_days === undefined ? "" : `${fmtDays(validation.age_days)} fa`));
  grid.appendChild(metaItem("Modello adottato",
    model.model_adopted || "nessuno",
    model.rule_version ? `in produzione gira la regola ${model.rule_version}` : ""));
  grid.appendChild(metaItem("Versione del dataset", model.dataset_version || "—",
    backtest && backtest.panel_rows ? `${NF0.format(backtest.panel_rows)} righe di panel, ${NF0.format(backtest.weekly_rows)} settimanali` : ""));
  grid.appendChild(metaItem("Feature disponibili",
    backtest && Array.isArray(backtest.features) ? `${backtest.features.length}` : "—",
    "tutte causali: calcolate solo con dati disponibili alla data"));
  card.appendChild(grid);
  return card;
}

function firstResultFolds(backtest) {
  if (!backtest || !Array.isArray(backtest.results) || !backtest.results.length) return [];
  const r = backtest.results.find((x) => Array.isArray(x.folds) && x.folds.length);
  return r ? r.folds : [];
}

function horizonChips(current, onPick) {
  const row = el("div", "chips rk-chips");
  [20, 60].forEach((h) => {
    const chip = el("button", `chip${h === current ? " is-active" : ""}`, `${h} sedute`);
    chip.type = "button";
    chip.addEventListener("click", () => onPick(h));
    row.appendChild(chip);
  });
  return row;
}

function resultsFor(horizon) {
  const bt = MODEL_STATE.backtest;
  if (!bt || !Array.isArray(bt.results)) return [];
  return bt.results.filter((r) => Number(r.horizon) === Number(horizon));
}

function metricsCard() {
  const card = el("div", "card rk-model-card");
  const head = el("div", "rk-card-head");
  head.appendChild(el("h3", "rk-h3", "Metriche fuori campione"));
  head.appendChild(horizonChips(MODEL_STATE.horizon, (h) => {
    MODEL_STATE.horizon = h;
    const root = document.getElementById("model-metrics");
    root.innerHTML = ""; root.appendChild(metricsCard());
    const rel = document.getElementById("model-reliability");
    rel.innerHTML = ""; rel.appendChild(reliabilityCard());
  }));
  card.appendChild(head);
  card.appendChild(el("p", "rk-fineprint",
    "Ogni riga è un modello messo alla prova su dati mai visti in addestramento, con embargo fra train e test. L'IC di Spearman misura quanto l'ordinamento assomiglia a quello realizzato; il Brier misura l'errore delle probabilità (più basso è meglio) e va confrontato con la climatologia, cioè la frequenza storica di base."));

  const rows = resultsFor(MODEL_STATE.horizon);
  if (!rows.length) {
    card.appendChild(el("p", "rk-fineprint", "Nessun risultato per questo orizzonte."));
    return card;
  }
  const table = el("table", "rk-table rk-metrics-table");
  const head2 = document.createElement("thead");
  const hr = el("tr");
  ["Modello", "IC Spearman", "t", "IC 1ª metà", "IC 2ª metà", "Brier", "Δ vs climatologia", "Hit rate", "Spread top−bottom netto"]
    .forEach((h, i) => hr.appendChild(el("th", i === 0 ? "" : "num", h)));
  head2.appendChild(hr);
  table.appendChild(head2);
  const body = document.createElement("tbody");
  const climatology = rows.find((r) => r.model === "climatology");
  const climBrier = climatology ? climatology.overall.brier : null;
  rows.forEach((r) => {
    const o = r.overall || {};
    const tr = el("tr", r.model === "momentum" ? "is-live" : "");
    const name = el("td", "");
    name.appendChild(el("span", "", MODEL_LABEL[r.model] || r.model));
    if (r.model === "momentum") name.appendChild(el("span", "rk-tag", "regola in produzione"));
    tr.appendChild(name);
    tr.appendChild(el("td", "num", fmtRatio(o.ic_spearman, 4)));
    tr.appendChild(el("td", "num", fmtRatio(o.ic_t, 2)));
    tr.appendChild(el("td", "num", fmtRatio(r.first_half ? r.first_half.ic_spearman : null, 4)));
    tr.appendChild(el("td", "num", fmtRatio(r.second_half ? r.second_half.ic_spearman : null, 4)));
    tr.appendChild(el("td", "num", fmtRatio(o.brier, 4)));
    const delta = climBrier === null || o.brier === undefined ? null : o.brier - climBrier;
    tr.appendChild(el("td", `num ${delta === null ? "" : (delta <= 0 ? "pos" : "neg")}`,
      delta === null ? "—" : `${delta > 0 ? "+" : ""}${fmtRatio(delta, 4)}`));
    tr.appendChild(el("td", "num", fmtPlainPct(o.hit_rate, 1)));
    tr.appendChild(el("td", `num ${pctClass(o.tmb_net_mean)}`, fmtSignedPct(o.tmb_net_mean, 2)));
    body.appendChild(tr);
  });
  table.appendChild(body);
  const wrap = el("div", "rk-table-wrap");
  wrap.appendChild(table);
  card.appendChild(wrap);

  const first = rows[0] || {};
  card.appendChild(el("p", "rk-fineprint",
    `${NF0.format(first.n_predictions || 0)} osservazioni fuori campione per modello, su ${first.n_folds || 0} fold, con embargo di ${first.embargo_weeks || 0} settimane fra addestramento e test. Un Δ positivo rispetto alla climatologia significa: peggio di una costante.`));
  return card;
}

function reliabilityCard() {
  const card = el("div", "card rk-model-card");
  const head = el("div", "rk-card-head");
  head.appendChild(el("h3", "rk-h3", "Affidabilità delle probabilità (reliability)"));
  const rows = resultsFor(MODEL_STATE.horizon);
  const available = rows.map((r) => r.model).filter((m) => m !== "random");
  if (!available.includes(MODEL_STATE.curve)) MODEL_STATE.curve = available[0];
  const chips = el("div", "chips rk-chips");
  available.forEach((m) => {
    const chip = el("button", `chip${m === MODEL_STATE.curve ? " is-active" : ""}`, MODEL_LABEL[m] || m);
    chip.type = "button";
    chip.addEventListener("click", () => {
      MODEL_STATE.curve = m;
      const root = document.getElementById("model-reliability");
      root.innerHTML = ""; root.appendChild(reliabilityCard());
    });
    chips.appendChild(chip);
  });
  head.appendChild(chips);
  card.appendChild(head);
  card.appendChild(el("p", "rk-fineprint",
    "Ogni banda raccoglie le stime di probabilità del modello e le confronta con la frequenza realmente osservata. Se le stime fossero affidabili i punti starebbero sulla diagonale: questo grafico è il motivo per cui la dashboard non pubblica probabilità."));

  const row = rows.find((r) => r.model === MODEL_STATE.curve);
  const bins = row && Array.isArray(row.reliability) ? row.reliability.filter((b) => b.n > 0) : [];
  if (!bins.length) {
    card.appendChild(el("p", "rk-fineprint", "Nessuna banda disponibile per questo modello."));
    return card;
  }
  const chart = el("div", "rk-reliability-chart");
  chart.innerHTML = reliabilitySVG(bins);
  card.appendChild(chart);

  const worst = bins.reduce((a, b) => (Math.abs(b.gap) > Math.abs(a.gap) ? b : a), bins[0]);
  card.appendChild(el("p", "rk-reliability-callout",
    `Banda più lontana dalla realtà: dove ${MODEL_LABEL[MODEL_STATE.curve] || MODEL_STATE.curve} stimava in media ${fmtRatio(worst.mean_predicted, 2)}, l'evento si è verificato ${fmtRatio(worst.observed_frequency, 2)} delle volte (${NF0.format(worst.n)} osservazioni). Una probabilità del genere non è un'informazione: è un errore con due decimali.`));

  const table = el("table", "rk-table rk-metrics-table rk-rel-table");
  const thead = document.createElement("thead");
  const hr = el("tr");
  ["Banda", "Osservazioni", "Probabilità stimata (media)", "Frequenza osservata", "Scarto"]
    .forEach((h, i) => hr.appendChild(el("th", i === 0 ? "" : "num", h)));
  thead.appendChild(hr);
  table.appendChild(thead);
  const body = document.createElement("tbody");
  bins.forEach((b) => {
    const tr = el("tr", b === worst ? "is-worst" : "");
    tr.appendChild(el("td", "", `${fmtRatio(b.lower, 2)} – ${fmtRatio(b.upper, 2)}`));
    tr.appendChild(el("td", "num", NF0.format(b.n)));
    tr.appendChild(el("td", "num", fmtRatio(b.mean_predicted, 3)));
    tr.appendChild(el("td", "num", fmtRatio(b.observed_frequency, 3)));
    tr.appendChild(el("td", `num ${Math.abs(b.gap) >= 0.1 ? "neg" : ""}`,
      `${b.gap > 0 ? "+" : ""}${fmtRatio(b.gap, 3)}`));
    body.appendChild(tr);
  });
  table.appendChild(body);
  const wrap = el("div", "rk-table-wrap");
  wrap.appendChild(table);
  card.appendChild(wrap);
  return card;
}

function reliabilitySVG(bins) {
  const W = 460, H = 300, pad = 52;
  const x = (v) => pad + v * (W - pad - 14);
  const y = (v) => H - pad - v * (H - pad - 14);
  const parts = [];
  parts.push(`<svg viewBox="0 0 ${W} ${H}" class="rk-svg" role="img" aria-label="Grafico di affidabilità: probabilità stimata contro frequenza osservata">`);
  // Griglia + assi
  for (let g = 0; g <= 4; g += 1) {
    const v = g / 4;
    parts.push(`<line x1="${x(0).toFixed(1)}" y1="${y(v).toFixed(1)}" x2="${x(1).toFixed(1)}" y2="${y(v).toFixed(1)}" class="rk-grid" />`);
    parts.push(`<text x="${(pad - 8).toFixed(1)}" y="${(y(v) + 4).toFixed(1)}" class="rk-axis" text-anchor="end">${fmtRatio(v, 2)}</text>`);
    parts.push(`<text x="${x(v).toFixed(1)}" y="${(H - pad + 18).toFixed(1)}" class="rk-axis" text-anchor="middle">${fmtRatio(v, 2)}</text>`);
  }
  parts.push(`<line x1="${x(0)}" y1="${y(0)}" x2="${x(1)}" y2="${y(1)}" class="rk-diagonal" />`);
  parts.push(`<text x="${x(0.62).toFixed(1)}" y="${(y(0.62) - 8).toFixed(1)}" class="rk-axis rk-axis-hint">stime affidabili</text>`);
  const maxN = Math.max(...bins.map((b) => b.n), 1);
  const points = bins.map((b) => `${x(b.mean_predicted).toFixed(1)},${y(b.observed_frequency).toFixed(1)}`).join(" ");
  parts.push(`<polyline points="${points}" class="rk-curve" />`);
  bins.forEach((b) => {
    const r = 3 + 6 * Math.sqrt(b.n / maxN);
    parts.push(`<circle cx="${x(b.mean_predicted).toFixed(1)}" cy="${y(b.observed_frequency).toFixed(1)}" r="${r.toFixed(1)}" class="rk-dot"><title>banda ${fmtRatio(b.lower, 2)}–${fmtRatio(b.upper, 2)}: stimato ${fmtRatio(b.mean_predicted, 3)}, osservato ${fmtRatio(b.observed_frequency, 3)} su ${b.n} osservazioni</title></circle>`);
  });
  parts.push(`<text x="${x(0.5).toFixed(1)}" y="${(H - 6).toFixed(1)}" class="rk-axis rk-axis-title" text-anchor="middle">probabilità stimata dal modello</text>`);
  parts.push(`<text x="12" y="${y(0.5).toFixed(1)}" class="rk-axis rk-axis-title" text-anchor="middle" transform="rotate(-90 12 ${y(0.5).toFixed(1)})">frequenza osservata</text>`);
  parts.push("</svg>");
  return parts.join("");
}

function forwardCard(model) {
  const card = el("div", "card rk-model-card");
  card.appendChild(el("h3", "rk-h3", "Backtest e portafoglio virtuale: due cose diverse"));
  card.appendChild(el("p", "rk-verdict-text",
    "Le metriche qui sopra vengono da una simulazione storica su dati mai visti in addestramento. Il portafoglio virtuale qui sotto è invece un track record in avanti: parte dalla data di attivazione, gira una volta a settimana e registra ogni riga prima di conoscerne l'esito. Il primo è già chiuso e dice che la regola non ha edge; il secondo serve a verificare che l'infrastruttura di misura funzioni, non a smentirlo."));

  const board = el("div", "rk-score-grid");
  (model.scoreboard || []).forEach((s) => {
    const box = el("div", "rk-score");
    box.appendChild(el("h4", "rk-detail-title", `Orizzonte ${s.horizon_days} sedute`));
    box.appendChild(detailFact("Righe risolte", `${s.n_resolved}`));
    box.appendChild(detailFact("Righe ancora aperte", `${s.n_pending}`));
    box.appendChild(detailFact("Hit rate selezionati",
      s.selected && s.selected.hit_rate !== null && s.selected.hit_rate !== undefined
        ? `${fmtPlainPct(s.selected.hit_rate, 1)} su ${s.selected.n}` : "non ancora calcolabile"));
    box.appendChild(detailFact("Hit rate universo",
      s.universe && s.universe.hit_rate !== null && s.universe.hit_rate !== undefined
        ? `${fmtPlainPct(s.universe.hit_rate, 1)} su ${s.universe.n}` : "non ancora calcolabile"));
    box.appendChild(el("p", "rk-fineprint", s.caveat || ""));
    board.appendChild(box);
  });
  if (board.childElementCount) card.appendChild(board);

  const scenario = model.scenario;
  const bench = model.benchmarks || {};
  if (scenario) {
    const grid = el("div", "rk-meta-grid");
    grid.appendChild(metaItem("Portafoglio virtuale", fmtEur(scenario.equity, true),
      `capitale iniziale ${fmtEur(scenario.initial_cash, true)} · ${fmtPct(scenario.return_pct)}`));
    grid.appendChild(metaItem("Liquidità", fmtEur(scenario.cash, true),
      `commissioni pagate ${fmtEur(scenario.fees_paid, true)}`));
    grid.appendChild(metaItem("Ultimo ciclo elaborato",
      scenario.last_processed ? fmtDay(scenario.last_processed) : "—",
      scenario.started_at ? `attivo dal ${fmtDay(scenario.started_at)}` : ""));
    grid.appendChild(metaItem("SPY comprato e tenuto",
      bench.spy_buy_and_hold ? fmtEur(bench.spy_buy_and_hold.equity, true) : "finestra troppo corta",
      bench.spy_buy_and_hold ? `${fmtPct(bench.spy_buy_and_hold.return_pct)} sulla stessa finestra` : "servono almeno due sedute"));
    grid.appendChild(metaItem("Universo equipesato",
      bench.equal_weight ? fmtEur(bench.equal_weight.equity, true) : "finestra troppo corta",
      bench.equal_weight ? `${fmtPct(bench.equal_weight.return_pct)} sulla stessa finestra` : "servono almeno due sedute"));
    const fresh = Array.isArray(model.freshness) ? model.freshness : [];
    const staleFeeds = fresh.filter((f) => f.is_fresh === false);
    grid.appendChild(metaItem("Fonti dati controllate", `${fresh.length}`,
      staleFeeds.length ? `non aggiornate: ${staleFeeds.map((f) => f.name).join(", ")}` : "tutte entro la soglia di freschezza"));
    card.appendChild(grid);
  }
  if (model.ledger) {
    card.appendChild(el("p", "rk-fineprint",
      `Registro delle classifiche emesse: ${NF0.format(model.ledger.rows || 0)} righe in ${model.ledger.path}. Ogni riga è scritta prima di conoscerne l'esito e non viene mai riscritta.`));
  }
  card.appendChild(el("p", "rk-fineprint", model.disclaimer || ""));
  return card;
}

/* ---------- Footer ---------- */
function setUpdated(id, data) {
  const node = document.getElementById(id);
  if (node && data && data.generated_at) node.textContent = `Aggiornato il ${fmtDate(data.generated_at)}`;
}
function renderFooter(crypto, equity, market) {
  const latest = mostRecent([crypto, equity, market]);
  const node = document.getElementById("footer-updated");
  if (node && latest) node.textContent = `Ultimo aggiornamento dati: ${fmtDate(latest)}.`;
}
function mostRecent(datasets) {
  const dates = datasets.filter((d) => d && d.generated_at)
    .map((d) => new Date(d.generated_at).getTime()).filter((t) => !Number.isNaN(t));
  return dates.length ? new Date(Math.max(...dates)).toISOString() : null;
}
