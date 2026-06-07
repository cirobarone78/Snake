"use strict";

const SOURCES = {
  crypto: "data/crypto_report.json",
  equity: "data/equity_report.json",
  education: "data/education.json",
  market: "data/market_series.json",
  events: "data/events.json",
};

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

document.addEventListener("DOMContentLoaded", init);

async function init() {
  setupTabs();
  const [crypto, equity, education, market, events] = await Promise.all([
    fetchJSON(SOURCES.crypto), fetchJSON(SOURCES.equity),
    fetchJSON(SOURCES.education), fetchJSON(SOURCES.market), fetchJSON(SOURCES.events),
  ]);
  renderTicker(market);
  renderHero(market);
  renderCrypto(crypto);
  renderEquity(equity);
  renderEvents(events);
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
  tabs.forEach((tab) => tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("is-active"));
    panels.forEach((p) => p.classList.remove("is-active"));
    tab.classList.add("is-active");
    const target = document.getElementById(tab.dataset.tab);
    if (target) target.classList.add("is-active");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }));
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
let HERO = { series: [], active: 0 };

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
  drawHero();
}

function drawHero() {
  const s = HERO.series[HERO.active];
  if (!s) return;
  const pts = s.points || [];
  document.getElementById("hero-name").textContent = s.name || s.symbol;
  document.getElementById("hero-last").textContent = fmtNum(s.last);
  const chg = document.getElementById("hero-change");
  chg.textContent = `${fmtPct(s.change_pct)} · 1 anno`;
  chg.className = `hero-change ${pctClass(s.change_pct)}`;

  const svg = document.getElementById("hero-chart");
  const W = 720, H = 240, padT = 16, padB = 24, padX = 6;
  const vals = pts.map((p) => p.v);
  const min = Math.min(...vals), max = Math.max(...vals);
  const span = max - min || 1;
  const x = (i) => padX + (i / Math.max(pts.length - 1, 1)) * (W - 2 * padX);
  const y = (v) => H - padB - ((v - min) / span) * (H - padT - padB);
  const down = (s.change_pct ?? 0) < 0;
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

/* ---------- Events (move attribution) ---------- */
function renderEvents(data) {
  setUpdated("events-updated", data);
  const root = document.getElementById("events-list");
  root.innerHTML = "";
  if (!data || !Array.isArray(data.assets) || data.assets.every((a) => !a.moves || a.moves.length === 0)) {
    root.appendChild(el("p", "empty", "Nessun movimento anomalo recente, o storico news ancora in accumulo."));
    return;
  }
  data.assets.forEach((asset) => {
    if (!asset.moves || asset.moves.length === 0) return;
    const block = el("div", "event-asset");
    const head = el("div", "event-asset-head");
    head.appendChild(el("span", "sym", asset.symbol));
    head.appendChild(el("h3", "", asset.name));
    block.appendChild(head);
    asset.moves.forEach((m) => block.appendChild(moveCard(m)));
    root.appendChild(block);
  });
}

function moveCard(m) {
  const card = el("div", "move-card");
  const head = el("div", "move-head");
  head.appendChild(el("span", "move-date", fmtDay(m.date)));
  head.appendChild(el("span", `move-chg ${pctClass(m.return_pct)}`, fmtPct(m.return_pct)));
  const cls = m.classification || "unknown";
  head.appendChild(el("span", `class-badge ${CLASS_CLASS[cls] || "unknown"}`, CLASS_LABEL[cls] || cls));
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
