"use strict";

// Data sources (relative -> works locally via http.server and on any static host).
const SOURCES = {
  crypto: "data/crypto_report.json",
  equity: "data/equity_report.json",
  education: "data/education.json",
};

// Italian, novice-friendly status labels (no emoji).
const STATUS_LABEL = {
  hot: "In forza",
  warm: "In rafforzamento",
  neutral: "Neutrale",
  weak: "In calo",
  risk: "Rischio",
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  setupTabs();
  const [crypto, equity, education] = await Promise.all([
    fetchJSON(SOURCES.crypto),
    fetchJSON(SOURCES.equity),
    fetchJSON(SOURCES.education),
  ]);
  renderCrypto(crypto);
  renderEquity(equity);
  renderOverview(crypto, equity);
  renderEducation(education);
  renderFooter(crypto, equity);
}

async function fetchJSON(path) {
  try {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch (_e) {
    return null;
  }
}

/* ---------- Tabs ---------- */

function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".panel");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("is-active"));
      panels.forEach((p) => p.classList.remove("is-active"));
      tab.classList.add("is-active");
      const target = document.getElementById(tab.dataset.tab);
      if (target) target.classList.add("is-active");
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
}

/* ---------- Formatting helpers ---------- */

function fmtPct(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}%`;
}

function pctClass(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "";
  return v >= 0 ? "pos" : "neg";
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
  return d.toLocaleString("it-IT", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function statusPill(status) {
  const key = (status || "neutral").toLowerCase();
  const label = STATUS_LABEL[key] || status || "—";
  const span = el("span", `status ${key}`, label);
  return span;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/* ---------- Rotation cards ---------- */

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

  // strength bar
  if (typeof item.strength === "number") {
    const wrap = el("div", "strength");
    const track = el("div", "track");
    const fill = el("div", "fill");
    fill.style.width = `${Math.round(item.strength * 100)}%`;
    track.appendChild(fill);
    wrap.appendChild(track);
    wrap.appendChild(el("span", "pct", `forza ${(item.strength * 100).toFixed(0)}`));
    card.appendChild(wrap);
  }

  // metrics
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

  if (kind === "crypto" && item.leader) {
    const lead = el("div", "leader");
    lead.innerHTML = `Leader: <strong></strong>`;
    lead.querySelector("strong").textContent = item.leader;
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

function renderCrypto(data) {
  const container = document.getElementById("crypto-cards");
  setUpdated("crypto-updated", data);
  renderCards(container, data, "crypto");
}

function renderEquity(data) {
  const container = document.getElementById("equity-cards");
  setUpdated("equity-updated", data);
  renderCards(container, data, "equity");
}

function renderCards(container, data, kind) {
  container.innerHTML = "";
  if (!data || !Array.isArray(data.items) || data.items.length === 0) {
    container.appendChild(el("p", "empty", "Dati non ancora disponibili. Verranno aggiornati al prossimo ciclo di raccolta."));
    return;
  }
  data.items.forEach((item) => container.appendChild(rotationCard(item, kind)));
}

/* ---------- Overview ---------- */

function renderOverview(crypto, equity) {
  fillRanklist("overview-crypto", crypto, "crypto");
  fillRanklist("overview-equity", equity, "equity");
  const latest = mostRecent([crypto, equity]);
  const node = document.getElementById("overview-updated");
  if (node && latest) node.textContent = `Aggiornato il ${fmtDate(latest)}`;
}

function fillRanklist(id, data, kind) {
  const ul = document.getElementById(id);
  ul.innerHTML = "";
  if (!data || !Array.isArray(data.items) || data.items.length === 0) {
    ul.appendChild(el("li", "", "Dati non ancora disponibili."));
    return;
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

/* ---------- Education ---------- */

function renderEducation(data) {
  const root = document.getElementById("education");
  root.innerHTML = "";
  if (!data || !Array.isArray(data.levels) || data.levels.length === 0) {
    root.appendChild(el("p", "empty", "Lezioni non disponibili."));
    return;
  }
  data.levels.forEach((level) => {
    const block = el("div", "edu-level");
    const head = el("div", "edu-level-head");
    head.appendChild(el("span", "edu-badge", level.id));
    head.appendChild(el("h3", "", level.name));
    head.appendChild(el("span", "sub", level.subtitle || ""));
    block.appendChild(head);

    if (Array.isArray(level.chapters) && level.chapters.length > 0) {
      level.chapters.forEach((ch) => block.appendChild(chapter(ch)));
    } else if (level.intro_html) {
      block.appendChild(chapterFromHtml("Panoramica del livello", level.intro_html));
      block.appendChild(el("p", "edu-empty", "Altri capitoli in arrivo."));
    } else {
      block.appendChild(el("p", "edu-empty", "Capitoli in arrivo."));
    }
    root.appendChild(block);
  });
}

function chapter(ch) {
  return chapterFromHtml(ch.title || ch.slug || "Capitolo", ch.html || "");
}

function chapterFromHtml(title, html) {
  const details = el("details", "chapter");
  const summary = document.createElement("summary");
  summary.textContent = title;
  details.appendChild(summary);
  const body = el("div", "chapter-body");
  body.innerHTML = html; // trusted: rendered at build time from our own repo
  details.appendChild(body);
  return details;
}

/* ---------- Footer / shared ---------- */

function setUpdated(id, data) {
  const node = document.getElementById(id);
  if (node && data && data.generated_at) node.textContent = `Aggiornato il ${fmtDate(data.generated_at)}`;
}

function renderFooter(crypto, equity) {
  const latest = mostRecent([crypto, equity]);
  const node = document.getElementById("footer-updated");
  if (node && latest) node.textContent = `Ultimo aggiornamento dati: ${fmtDate(latest)}.`;
}

function mostRecent(datasets) {
  const dates = datasets
    .filter((d) => d && d.generated_at)
    .map((d) => new Date(d.generated_at).getTime())
    .filter((t) => !Number.isNaN(t));
  if (dates.length === 0) return null;
  return new Date(Math.max(...dates)).toISOString();
}
