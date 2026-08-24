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
  const [crypto, equity, education, market, events, health, paper, replay, dca] = await Promise.all([
    fetchJSON(SOURCES.crypto), fetchJSON(SOURCES.equity),
    fetchJSON(SOURCES.education), fetchJSON(SOURCES.market), fetchJSON(SOURCES.events),
    fetchJSON(SOURCES.health), fetchJSON(SOURCES.paper), fetchJSON(SOURCES.replay),
    fetchJSON(SOURCES.dca),
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
  card.appendChild(el("p", "mini-title", "Candidate per un accumulo a lungo termine"));
  card.appendChild(el("p", "dca-sub", "Monete che superano i filtri meccanici: dimensione, liquidità reale, età minima dimostrabile. Nessun giudizio su tecnologia o prospettive — sono i nomi da studiare, non da comprare al buio."));
  const list = el("ul", "ranklist");
  data.candidates.forEach((c) => list.appendChild(candidateRow(c)));
  card.appendChild(list);
  const summary = data.rejected_summary || {};
  const labels = data.rejected_labels || {};
  const parts = Object.keys(summary).map((k) => `${labels[k] || k}: ${summary[k]}`);
  if (parts.length) card.appendChild(el("p", "dca-sub dca-rejected", `Escluse dal filtro — ${parts.join(" · ")}.`));
  return card;
}

function candidateRow(c) {
  const li = el("li", "dca-cand");
  li.appendChild(el("span", "ri-rank", String(c.rank)));
  const nameWrap = el("div", "dca-cand-name");
  nameWrap.appendChild(el("span", "ri-name", `${c.symbol} · ${c.name}`));
  const tags = el("div", "dca-tags");
  if (c.flags_it) c.flags_it.split(",").forEach((f) => tags.appendChild(el("span", "dca-tag", f.trim())));
  if (c.diversifying) tags.appendChild(el("span", "dca-tag is-div", "diversifica"));
  if (tags.childNodes.length) nameWrap.appendChild(tags);
  li.appendChild(nameWrap);
  li.appendChild(metricRaw("Cap.", fmtMcap(c.market_cap)));
  li.appendChild(metricRaw("Liquidità", c.turnover == null ? "n/d" : `${(c.turnover * 100).toFixed(1)}%`));
  li.appendChild(metricRaw("Età min.", c.min_age_years == null ? "n/d" : `${NF1.format(c.min_age_years)} anni`));
  li.appendChild(metric("Da max", c.ath_change_pct));
  return li;
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
