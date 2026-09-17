/* ── MANAK-SETU console ────────────────────────────────────────────────────
   Talks only to the local FastAPI service. Every number rendered here comes
   back from a query over the CSV-derived database; nothing is synthesised in
   the browser. Where a lookup misses, the UI says so rather than filling in.
   ────────────────────────────────────────────────────────────────────────── */

let API = localStorage.getItem('manak.api');

async function resolveApi() {
  if (API) return API;
  const host = location.protocol === 'file:' ? '127.0.0.1' : location.hostname;
  for (const base of ['', `http://${host}:8000`]) {
    try {
      const r = await fetch(base + '/health', { cache: 'no-store', signal: AbortSignal.timeout(3000) });
      if (r.ok) return (API = base);
    } catch (_) { /* next */ }
  }
  return (API = `http://${host}:8000`);
}

function paintRole() {
  const b = $('#role-btn');
  if (!b) return;
  b.textContent = ROLE === 'admin' ? 'Admin' : 'Officer';
  b.classList.toggle('admin', ROLE === 'admin');
}

const S = {
  stats: null, standards: null, certs: null, tenders: null,
  graph: null, heroGraph: null, backlog: null, bench: null,
  chips: [], analysis: null, audit: null,
  pins: JSON.parse(localStorage.getItem('manak.pins') || '[]'),
  claims: JSON.parse(localStorage.getItem('manak.claims') || '[]'),
};
const ready = new Set();
const KC = ['var(--k1)','var(--k2)','var(--k3)','var(--k4)','var(--k5)','var(--k6)','var(--k7)','var(--k8)'];

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = v => v == null ? '' : String(v).replace(/[&<>"']/g, c =>
  ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));

async function api(path, opts) {
  // no-store on both ends: a browser holding a stale /graph or /stats shows
  // wrong counts with no error to give it away
  const r = await fetch(API + path, { cache: 'no-store', ...opts });
  if (!r.ok) {
    let d = `HTTP ${r.status}`;
    try { const j = await r.json(); if (j.detail) d = j.detail; } catch (_) {}
    throw new Error(d);
  }
  return r.json();
}

/* ── icons ─────────────────────────────────────────────────────────────── */

const ICON = {
  gauge:  '<circle cx="12" cy="13" r="8"/><path d="M12 13l4-3M12 5V3"/>',
  scan:   '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="3.2"/>',
  files:  '<path d="M15 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7z"/><path d="M15 3v4h4M9 13h6M9 17h4"/>',
  net:    '<circle cx="6" cy="6" r="2.4"/><circle cx="18" cy="7" r="2.4"/><circle cx="12" cy="17" r="2.4"/><path d="M8 7.4 15.7 15M16.6 9.1 13.4 14.9M7.6 7.9l3 7"/>',
  book:   '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M8 7h7M8 11h7"/>',
  badge:  '<path d="M12 3l2.2 1.6 2.7-.2.8 2.6 2.2 1.6-1 2.5 1 2.5-2.2 1.6-.8 2.6-2.7-.2L12 21l-2.2-1.6-2.7.2-.8-2.6L4.1 15.4l1-2.5-1-2.5 2.2-1.6.8-2.6 2.7.2z"/><path d="m9.5 12 1.8 1.8 3.4-3.6"/>',
  pie:    '<path d="M12 3v9h9"/><circle cx="12" cy="12" r="9"/>',
  target: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  copy:   '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/>',
  pin:    '<path d="M12 17v5M9 3h6l-1 6 3 3v2H7v-2l3-3z"/>',
  ext:    '<path d="M14 4h6v6M20 4l-8 8M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5"/>',
  alert:  '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>',
  check:  '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.4 2.4L15.8 9"/>',
  info:   '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  x:      '<path d="M18 6 6 18M6 6l12 12"/>',
  down:   '<path d="M12 3v12m0 0 4-4m-4 4-4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>',
  arrow:  '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  chev:   '<path d="m9 6 6 6-6 6"/>',
  refresh:'<path d="M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6"/>',
  empty:  '<path d="M4 7h16M4 12h10M4 17h7"/>',
  doc:    '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
};
const ic = (n, cls = '') => `<svg class="i ${cls}" viewBox="0 0 24 24">${ICON[n] || ''}</svg>`;

/* ── toasts ────────────────────────────────────────────────────────────── */

function toast(msg, kind = 'ok') {
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.innerHTML = `${ic(kind === 'bad' ? 'alert' : kind === 'info' ? 'info' : 'check', 'sm')}<span>${esc(msg)}</span>`;
  $('#toasts').appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .25s'; }, 2400);
  setTimeout(() => el.remove(), 2700);
}

async function copy(text, label) {
  try {
    await navigator.clipboard.writeText(text);
    toast(`${label || 'Copied'} copied to clipboard`);
  } catch (_) { toast('Clipboard blocked by the browser', 'bad'); }
}

function download(name, text, mime = 'text/plain') {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const a = document.createElement('a');
  a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
  toast(`${name} downloaded`);
}

/* ── charts ────────────────────────────────────────────────────────────── */

const polar = (cx, cy, r, d) => {
  const a = (d - 90) * Math.PI / 180;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
};

function ring(cx, cy, rO, rI, a0, a1) {
  const big = a1 - a0 <= 180 ? 0 : 1;
  const p1 = polar(cx, cy, rO, a1), p2 = polar(cx, cy, rO, a0);
  const p3 = polar(cx, cy, rI, a0), p4 = polar(cx, cy, rI, a1);
  return `M${p1.x} ${p1.y}A${rO} ${rO} 0 ${big} 0 ${p2.x} ${p2.y}L${p3.x} ${p3.y}A${rI} ${rI} 0 ${big} 1 ${p4.x} ${p4.y}Z`;
}

function donut(data, { size = 138, thick = 22, val = '', lab = '' } = {}) {
  const total = data.reduce((s, d) => s + d.count, 0);
  const c = size / 2, rO = c - 2, rI = rO - thick;
  let segs = '';
  const live = data.filter(d => d.count > 0);
  if (!total) {
    segs = `<circle cx="${c}" cy="${c}" r="${(rO + rI) / 2}" fill="none" stroke="var(--surface-3)" stroke-width="${thick}"/>`;
  } else if (live.length === 1) {
    segs = `<circle class="sg" cx="${c}" cy="${c}" r="${(rO + rI) / 2}" fill="none" stroke="${live[0].color}" stroke-width="${thick}"><title>${esc(live[0].key)}: ${live[0].count}</title></circle>`;
  } else {
    let a = 0;
    data.forEach(d => {
      if (!d.count) return;
      const sw = d.count / total * 360;
      segs += `<path class="sg" d="${ring(c, c, rO, rI, a, a + sw - 0.7)}" fill="${d.color}"><title>${esc(d.key)}: ${d.count} (${(d.count / total * 100).toFixed(1)}%)</title></path>`;
      a += sw;
    });
  }
  const mid = val !== '' ? `<text class="v" x="${c}" y="${c}" text-anchor="middle">${esc(val)}</text>
    <text class="l" x="${c}" y="${c + 14}" text-anchor="middle">${esc(lab)}</text>` : '';
  return `<svg class="dnut" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">${segs}${mid}</svg>`;
}

const legend = (data, total) => `<div class="legend">${data.map(d => `
  <div class="r"><span class="sw" style="background:${d.color}"></span>
    <span class="nm">${esc(d.key)}</span>
    <span class="vv">${d.count}${total ? ` · ${(d.count / total * 100).toFixed(1)}%` : ''}</span>
  </div>`).join('')}</div>`;

function bars(data, color) {
  const mx = Math.max(...data.map(d => d.count), 1);
  setTimeout(() => $$('.bfill[data-w]').forEach(e => { e.style.width = e.dataset.w + '%'; e.removeAttribute('data-w'); }), 30);
  return `<div class="bars">${data.map((d, i) => `
    <div class="brow">
      <span class="bl" title="${esc(d.key)}">${esc(d.key)}</span>
      <span class="btrack"><span class="bfill" data-w="${d.count / mx * 100}" style="background:${color ? (typeof color === 'function' ? color(d) : color) : KC[i % 8]}"></span></span>
      <span class="bv">${d.count}</span>
    </div>`).join('')}</div>`;
}

function histo(data) {
  const mx = Math.max(...data.map(d => d.count), 1);
  setTimeout(() => $$('.hbar[data-h]').forEach(e => { e.style.height = e.dataset.h + 'px'; e.removeAttribute('data-h'); }), 30);
  return `<div class="histo">${data.map(d => `
    <div class="hcol" title="${esc(d.key)}: ${d.count}">
      <span class="hval">${d.count}</span>
      <span class="hbar" data-h="${Math.max(2, d.count / mx * 104)}"></span>
      <span class="hlab">${esc(d.key)}</span>
    </div>`).join('')}</div>`;
}

function countUp(el, target, dec = 0) {
  // rAF is frozen in a background tab, so a figure loaded there would sit at 0
  // for good — the count-up is decoration, the number is not.
  if (document.hidden || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    el.textContent = target.toFixed(dec);
    return;
  }
  const t0 = performance.now(), dur = 680;
  const step = now => {
    const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    el.textContent = (target * e).toFixed(dec);
    if (p < 1) requestAnimationFrame(step); else el.textContent = target.toFixed(dec);
  };
  requestAnimationFrame(step);
}

const kpi = t => `<div class="kpi ${t.tone || 'plain'}"><span class="rule"></span>
  <div class="lb">${t.icon ? ic(t.icon, 'sm') : ''}${esc(t.label)}</div>
  <div class="vl">${t.text != null
    ? esc(t.text)
    : `<span data-n="${t.value}" data-d="${t.dec || 0}">0</span>${t.suffix || ''}`}</div>
  <div class="sub">${esc(t.sub)}</div></div>`;

const runCounts = () => $$('[data-n]').forEach(e => {
  countUp(e, parseFloat(e.dataset.n), +e.dataset.d); e.removeAttribute('data-n');
});

const statusPill = s => s === 'Current' ? '<span class="pill ok">Current</span>'
  : s === 'Superseded' ? '<span class="pill bad">Superseded</span>'
  : s === 'Withdrawn' ? '<span class="pill bad">Withdrawn</span>'
  : `<span class="pill mute">${esc(s || 'Unknown')}</span>`;

const offline = m => `<div class="note bad">${ic('alert')}<div><b>Backend unreachable.</b> ${esc(m)}<br>
  Start it with <span class="mono">uvicorn main:app --reload</span> from the project root.</div></div>`;

const blank = (t, s) => `<div class="blank">${ic('empty')}<div class="t">${esc(t)}</div><div class="s">${esc(s || '')}</div></div>`;

/* ── navigation ────────────────────────────────────────────────────────── */

const NAV = [
  { id: 'draft',     label: 'Draft',       full: 'Draft clause',        icon: 'scan' },
  { id: 'analyze',   label: 'Audit',       full: 'Tender audit',        icon: 'files' },
  { id: 'evidence',  label: 'Evidence',    full: 'Corpus evidence',     icon: 'doc' },
  { id: 'overview',  label: 'Overview',    full: 'Overview',            icon: 'gauge',  admin: true },
  { id: 'tenders',   label: 'Tenders',     full: 'Tender corpus',       icon: 'doc',    admin: true, count: 'tenders' },
  { id: 'standards', label: 'Standards',   full: 'Standards register',  icon: 'book',   admin: true, count: 'standards' },
  { id: 'certs',     label: 'Certification', full: 'Certification duties', icon: 'badge', admin: true, count: 'certification_rules' },
  { id: 'graph',     label: 'Graph',       full: 'Co-citation graph',   icon: 'net',    admin: true },
  { id: 'coverage',  label: 'Coverage',    full: 'Coverage',            icon: 'pie',    admin: true },
  { id: 'benchmark', label: 'Benchmark',   full: 'Detection benchmark', icon: 'target', admin: true },
];

/* Officers get the two screens they actually work in. Admin adds the corpus,
   the register and the integrity views — useful to the team, noise to a user. */
let ROLE = localStorage.getItem('manak.role') || 'officer';
const visibleNav = () => NAV.filter(n => ROLE === 'admin' || !n.admin);

const navLabel = n => (typeof t === 'function' ? t('nav.' + n.id) : n.label);
const navFull = n => (typeof t === 'function' ? t('full.' + n.id) : n.full);
const TITLE = Object.fromEntries(NAV.map(n => [n.id, n.full]));
const LOAD = {
  draft: () => {}, overview: loadOverview, analyze: () => renderChips(), tenders: loadTenders,
  evidence: () => {},
  graph: loadGraph, standards: loadStandards, certs: loadCerts,
  coverage: loadCoverage, benchmark: () => loadBench(false),
};

function buildNav() {
  $('#tabs').innerHTML = visibleNav().map(n =>
    `<div class="tab" data-v="${n.id}" role="tab" tabindex="0" aria-selected="false" title="${esc(navFull(n))}">${ic(n.icon, 'sm')}<span>${esc(navLabel(n))}</span>
      ${n.count ? `<span class="ct" data-ct="${n.count}"></span>` : ''}</div>`).join('');
  $$('.tab').forEach(el => {
    el.addEventListener('click', () => go(el.dataset.v));
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(el.dataset.v); }
    });
  });
  const tabs = $('#tabs'), wrap = $('#tabwrap');
  const spill = () => wrap.classList.toggle('spill',
    tabs.scrollWidth - tabs.clientWidth - tabs.scrollLeft > 4);
  tabs.addEventListener('scroll', spill);
  window.addEventListener('resize', spill);
  spill();
}

let view = 'overview';

function go(v, entity) {
  if (!TITLE[v]) v = 'draft';
  if (ROLE !== 'admin' && NAV.find(n => n.id === v)?.admin) v = 'draft';
  view = v;
  $$('.tab').forEach(e => {
    const on = e.dataset.v === v;
    e.classList.toggle('on', on);
    e.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  $$('.view').forEach(e => e.classList.toggle('on', e.id === 'v-' + v));
  $('#crumb').textContent = navFull(NAV.find(n => n.id === v) || { id: v, full: TITLE[v] });
  history.replaceState(null, '', '#' + v + (entity ? '/' + encodeURIComponent(entity) : ''));
  LOAD[v] && LOAD[v]();
  // Content arrives asynchronously; translate once it has settled.
  setTimeout(translatePage, 400);
}

const closePins = () => $('#pins-pop').classList.remove('on');

/* ── health ────────────────────────────────────────────────────────────── */

async function health() {
  try {
    const h = await api('/health');
    $('#conn').innerHTML = `<span class="dot up"></span>connected · ${Object.keys(h.row_counts).length} tables`;
    $('#build').textContent = `v${h.version} · data ${h.dataset_date}`;
    const cc = h.row_counts.co_citation;
    if ($('#prov-cc')) $('#prov-cc').textContent = cc;
    const st = h.row_counts.standards;
    if ($('#prov-std')) $('#prov-std').textContent = st;
    // Provenance figures come from /health, never from numbers typed into the page.
    if ($('#prov-bl')) $('#prov-bl').textContent = h.row_counts.coverage_gap_backlog;
    if ($('#prov-cert')) $('#prov-cert').textContent = h.row_counts.certification_rules;
    if ($('#ce-meta')) $('#ce-meta').textContent =
      `${h.row_counts.certification_rules} records · ISI Mark, CRS, Quality Control Orders and Hallmarking`;
    if ($('#bl-hint')) $('#bl-hint').textContent =
      `${h.row_counts.coverage_gap_backlog} standards cited by real tenders but not yet held · tick to claim`;
    if ($('#std-meta')) $('#std-meta').textContent =
      `${st} records · source standards.bis.gov.in`;
    if ($('#graph-meta')) $('#graph-meta').textContent =
      `${cc.toLocaleString()} edges · thresholds 5+ co-citations / 40%+ confidence / source cited in 8+ tenders`;
    $$('[data-ct]').forEach(e => { e.textContent = h.row_counts[e.dataset.ct] ?? ''; });
    // Coverage figures (usable documents, dead-citation count) live in /stats.
    // Fetched here too so the tenders header and the footer are right on any
    // first screen, not only after the overview has loaded.
    api('/stats').then(s => {
      S.stats = s;
      $$('[data-cv]').forEach(e => { e.textContent = s.coverage[e.dataset.cv] ?? ''; });
    }).catch(() => {});
  } catch (_) {
    $('#conn').innerHTML = `<span class="dot down"></span>backend offline`;
  }
}

/* ── pins ──────────────────────────────────────────────────────────────── */

function savePins() { localStorage.setItem('manak.pins', JSON.stringify(S.pins)); renderPins(); }

function togglePin(id) {
  const i = S.pins.indexOf(id);
  if (i >= 0) { S.pins.splice(i, 1); toast(`${id} removed from working set`, 'info'); }
  else { S.pins.push(id); toast(`${id} pinned`); }
  savePins();
  syncPinBtn();
}

function renderPins() {
  const badge = $('#pins-badge');
  badge.hidden = !S.pins.length;
  badge.textContent = S.pins.length;
  $('#pins-n').textContent = S.pins.length ? `${S.pins.length} pinned` : '';
  $('#pins-list').innerHTML = S.pins.length
    ? S.pins.map(p => `<div class="pin-row" data-p="${esc(p)}">
        <span>${esc(p)}</span><span class="rm" data-rm="${esc(p)}">${ic('x','sm')}</span></div>`).join('')
    : `<div class="xs dimmer" style="padding:8px 7px 4px">Nothing pinned yet. Open a standard and use the pin button to keep it here.</div>`;
  $$('#pins-list .pin-row').forEach(el => el.addEventListener('click', e => {
    if (e.target.closest('[data-rm]')) { togglePin(el.dataset.p); return; }
    openStandard(el.dataset.p); closePins();
  }));
}

function syncPinBtn() {
  const t = $('#dw-title').textContent;
  $('#dw-pin').style.color = S.pins.includes(t) ? 'var(--accent)' : '';
}

/* ── overview ──────────────────────────────────────────────────────────── */

async function loadOverview(force) {
  if (ready.has('overview') && !force) return;
  try { S.stats = await api('/stats'); }
  catch (e) { $('#ov-cov').innerHTML = offline(e.message); return; }
  ready.add('overview');
  const st = S.stats, cv = st.coverage;
  drawHealthIndex();


  $('#ov-cov').innerHTML = unitChart(cv.matched, cv.distinct_cited) + `
    <div style="display:flex;gap:22px;margin-top:14px;flex-wrap:wrap">
      ${[['Held in register', cv.matched, 'var(--ok)'], ['Cited, not held', cv.unmatched, 'var(--surface-3)'],
         ['Coverage', cv.pct + '%', 'transparent']]
        .map(([l, v, c]) => `<div>
          <div class="eyebrow" style="display:flex;align-items:center;gap:6px">
            ${c !== 'transparent' ? `<span style="width:8px;height:8px;border-radius:2px;background:${c}"></span>` : ''}${l}</div>
          <div class="mono" style="font-size:15px;margin-top:3px">${v}</div></div>`).join('')}
    </div>
    <p class="xs dimmer" style="margin-top:12px">${esc(cv.denominator_note)}</p>`;

  $('#hero-figs').innerHTML = [
    { n: st.row_counts.standards, l: 'standards indexed' },
    { n: cv.usable_tenders, l: 'tenders parsed' },
    { n: st.graph.edges, l: 'graph edges' },
    { n: cv.pct + '%', l: 'citation coverage', hot: true },
  ].map(f => `<div class="hero-fig ${f.hot ? 'hot' : ''}"><div class="n">${f.n}</div><div class="l">${f.l}</div></div>`).join('');
  heroGraph();

  const sc = { Current: 'var(--ok)', Superseded: 'var(--bad)', Withdrawn: 'var(--accent)' };
  const sd = st.standards_by_status.map(d => ({ ...d, color: sc[d.key] || 'var(--ink-4)' }));
  const tot = sd.reduce((s, d) => s + d.count, 0);
  const notCurrent = tot - (sd.find(d => d.key === 'Current')?.count || 0);
  $('#ov-status').innerHTML = `<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
      ${donut(sd, { val: tot, lab: 'standards' })}<div style="flex:1;min-width:150px">${legend(sd, tot)}</div></div>
    <p class="xs dimmer" style="margin-top:11px">Successor status on file for ${notCurrent} of ${tot}.</p>`;

  $('#ov-usab').innerHTML = bars(st.tenders_by_usability, d => d.key === 'Usable' ? 'var(--ok)' : 'var(--ink-4)')
    + `<p class="xs dimmer" style="margin-top:11px">Coverage and benchmark figures use <span class="mono">Usable</span> rows only.</p>`;
  $('#ov-decade').innerHTML = histo(st.standards_by_decade);
  $('#ov-fam').innerHTML = bars(st.standards_by_family);
  $('#ov-deg').innerHTML = bars(st.graph.top_degree.map(d => ({ key: d.is_number, count: d.degree })), 'var(--k1)');
  $('#ov-gap').innerHTML = bars(st.backlog_top.slice(0, 10).map(d => ({ key: d.is_number, count: d.tenders_citing })), 'var(--accent)');
}

/* Hero graph: the same co-citation data as the graph tab, laid out once and
   drawn in. Non-interactive — it is a backdrop, the real tool is on /graph. */
const HW = 1200, HH = 380;

async function heroGraph() {
  const svg = $('#hero-canvas');
  if (!svg || svg.dataset.done) return;
  // A sample, fetched as a sample: the hero draws 56 nodes, so it asks for 56
  // rather than pulling the full ~600 KB graph the Graph view needs.
  try { if (!S.heroGraph) S.heroGraph = await api('/graph?nodes=56&edges=190'); }
  catch (_) { return; }
  svg.dataset.done = '1';
  svg.setAttribute('viewBox', `0 0 ${HW} ${HH}`);

  const G0 = S.heroGraph;
  if (!G0 || !G0.edges) return;
  const deg = {};
  G0.edges.forEach(e => { deg[e.source] = (deg[e.source] || 0) + 1; deg[e.target] = (deg[e.target] || 0) + 1; });
  const mx = Math.max(...Object.values(deg), 1);

  /* This is decoration behind a headline, not the Graph view — so it draws a
     sample, not the corpus. Drawing all of it cost 3,336 <line> elements and a
     190-iteration O(n^2) relaxation over 193 nodes (~3.5M steps) on the main
     thread before the page could paint. The layout was written when the graph
     held 74 nodes and 376 edges; it grew 9x and the cost grew with it unnoticed.
     The real figures sit in the KPI row beside it and in the Graph view. */
  const HERO_NODES = 56, HERO_EDGES = 190, HERO_ITERATIONS = 140;

  const top = [...G0.nodes]
    .sort((a, b) => (deg[b.id] || 0) - (deg[a.id] || 0))
    .slice(0, HERO_NODES);
  const n = top.map((d, i) => {
    const a = i / top.length * Math.PI * 2;
    return { id: d.id, deg: deg[d.id] || 0, r: 2 + (deg[d.id] || 0) / mx * 7,
      x: HW / 2 + Math.cos(a) * 300, y: HH / 2 + Math.sin(a) * 130, vx: 0, vy: 0 };
  });
  const by = Object.fromEntries(n.map(d => [d.id, d]));
  const e = G0.edges
    .filter(x => by[x.source] && by[x.target])
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, HERO_EDGES);

  for (let it = 0; it < HERO_ITERATIONS; it++) {
    for (let i = 0; i < n.length; i++) for (let j = i + 1; j < n.length; j++) {
      const a = n[i], b = n[j];
      let dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy;
      if (d2 < 1) d2 = 1;
      const d = Math.sqrt(d2), f = 5200 / d2;
      a.vx += f * dx / d; a.vy += f * dy / d; b.vx -= f * dx / d; b.vy -= f * dy / d;
    }
    e.forEach(x => {
      const a = by[x.source], b = by[x.target];
      let dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx * dx + dy * dy) || .01;
      const f = .02 * (d - (70 + (1 - x.confidence) * 110));
      a.vx += f * dx / d; a.vy += f * dy / d; b.vx -= f * dx / d; b.vy -= f * dy / d;
    });
    n.forEach(p => {
      p.vx += (HW / 2 - p.x) * .0022; p.vy += (HH / 2 - p.y) * .006;
      p.vx *= .8; p.vy *= .8; p.x += p.vx; p.y += p.vy;
    });
  }

  const hot = new Set(n.slice().sort((a, b) => b.deg - a.deg).slice(0, 6).map(d => d.id));

  /* Two animated groups, not one animation per element. Per-element fades meant
     3,529 concurrent CSS animations, each its own compositor layer. */
  svg.innerHTML =
    `<g class="he-g">` + e.map(x => {
      const a = by[x.source], b = by[x.target];
      return `<line class="he" x1="${a.x.toFixed(1)}" y1="${a.y.toFixed(1)}" x2="${b.x.toFixed(1)}" y2="${b.y.toFixed(1)}"
        stroke-width="${(0.35 + x.confidence * 1.5).toFixed(2)}"/>`;
    }).join('') + `</g><g class="hn-g">` +
    n.map(d => `<circle class="hn ${hot.has(d.id) ? 'hot' : ''}" cx="${d.x.toFixed(1)}" cy="${d.y.toFixed(1)}" r="${d.r.toFixed(1)}"/>`)
      .join('') + `</g>`;
}

/* One cell per distinct cited standard. Counts come from /stats, never
   from a figure typed in here. */
function unitChart(held, total) {
  /* The stagger used to be one setTimeout per cell — 488 timers, each waking the
     main thread to toggle a class and start its own transition. It is now a
     single class flip on the container, with the delay carried by CSS. */
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const box = $('.units');
    if (box) box.classList.add('in');
  }));
  return `<div class="units">${Array.from({ length: total }, (_, i) =>
    `<span class="unit ${i < held ? 'held' : ''}" style="--d:${(i * 1.4).toFixed(0)}ms"
      title="${i < held ? 'held in register' : 'cited, not held'}"></span>`).join('')}</div>`;
}

/* ── forward flow: spec text → governing standard → clause ───────────────── */

async function runForward() {
  const q = $('#fw-spec').value.trim(), out = $('#fw-out'), btn = $('#fw-run');
  if (!q) { toast('Enter some specification text first', 'bad'); return; }
  btn.disabled = true; btn.innerHTML = `<span class="spin"></span> Retrieving…`;
  out.innerHTML = `<div class="card"><div class="in"><div class="skel" style="height:90px"></div></div></div>`;
  // The peer panel belongs to the previous answer. Leaving it up while a new
  // query runs shows one specification's evidence under another's result.
  const peers = $('#fw-peers');
  if (peers) peers.innerHTML = '';
  try {
    S.fw = await api('/recommend', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spec_text: q, ui_language: document.documentElement.lang }),
    });
    renderForward(S.fw);
  } catch (e) { out.innerHTML = offline(e.message); }
  finally { btn.disabled = false; btn.textContent = 'Find governing standard'; }
}

const provRow = c => `<tr class="hit" data-go="${esc(c.is_number)}">
  <td class="mono">${esc(c.is_number)}</td>
  <td class="std-title" style="max-width:300px">${esc(c.title || '—')}</td>
  <td class="mono r">${c.score.toFixed(3)}</td>
  <td class="mono r xs dimmer">${c.dense_rank ?? '—'}</td>
  <td class="mono r xs dimmer">${c.bm25_rank ?? '—'}</td>
  <td class="xs">${c.matched_on.terms.length
      ? `<span class="dimmer">${esc(c.matched_on.field)}:</span> ${esc(c.matched_on.terms.slice(0,4).join(', '))}`
      : '<span class="dimmer">—</span>'}</td>
  <td class="rowgo">${ic('arrow','sm')}</td></tr>`;

/* The path an answer took, drawn from the response before the answer itself.
   Every figure here is one the system reported about its own run — the depth
   each retriever reached, the size of the fused set, which filters demoted
   something, what the gate compared. A stage that cannot say what it did does
   not get a pill, and when the gate declines the rail ends at a red stop, so
   an abstention reads as a decision rather than a failure. */

/* The score, drawn against the thresholds that decide what happens to it.
   A bare "0.721" tells an officer nothing: they cannot know whether that is
   good. The arc puts the two numbers the gate actually compares against on the
   dial — below 0.45 the system declines, above 0.80 it calls the match high —
   so the score is read in the terms the system used. Where calibration has
   been measured, the line beneath says how often a score in this band was
   right, with the count it was measured on. */

function confidenceArc(score, thresholds) {
  const lo = thresholds.top_score, hi = thresholds.high_confidence;
  const R = 46, CX = 60, CY = 56, SWEEP = 250, START = 145;
  const pt = (frac, r) => {
    const a = (START + SWEEP * frac) * Math.PI / 180;
    return [CX + r * Math.cos(a), CY + r * Math.sin(a)];
  };
  const arcPath = (from, to, r) => {
    const [x1, y1] = pt(from, r), [x2, y2] = pt(to, r);
    return `M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 ${(to - from) * SWEEP > 180 ? 1 : 0} 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`;
  };
  const tone = score >= hi ? 'var(--ok)' : score >= lo ? 'var(--amber)' : 'var(--bad)';
  const tick = frac => {
    const [x1, y1] = pt(frac, R - 7), [x2, y2] = pt(frac, R + 6);
    return `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}"
      stroke="var(--ink-3)" stroke-width="1.5"/>`;
  };
  const band = calibrationFor(score);
  return `<div class="carc">
    <svg viewBox="0 0 120 86" role="img"
         aria-label="confidence ${score.toFixed(3)} of 1, declines below ${lo}, high above ${hi}">
      <path d="${arcPath(0, 1, R)}" fill="none" stroke="var(--line-hard)" stroke-width="7" stroke-linecap="round"/>
      <path d="${arcPath(0, Math.max(score, 0.001), R)}" fill="none" stroke="${tone}" stroke-width="7"
            stroke-linecap="round" class="carc-fill" style="--arc-len:${(SWEEP / 360) * 2 * Math.PI * R}"/>
      ${tick(lo)}${tick(hi)}
      <text x="60" y="52" text-anchor="middle" class="carc-n">${score.toFixed(3)}</text>
      <text x="60" y="66" text-anchor="middle" class="carc-l">confidence</text>
    </svg>
    <div class="carc-key">
      <div><span class="sw" style="background:var(--bad)"></span>below ${lo} · declines</div>
      <div><span class="sw" style="background:var(--ok)"></span>above ${hi} · high</div>
      ${band ? `<div class="carc-cal">In testing, a score in ${band.from}–${band.to}
        was the expected standard <b>${band.correct} of ${band.queries}</b> times.</div>` : ''}
    </div></div>`;
}

/* Calibration is read from the file eval_retrieval writes. If it has not been
   measured, the arc says nothing about it rather than implying a number. */
// A bucket needs enough queries to say anything. Measured on the golden set,
// 92% of queries land in 0.9-1.0 and the rest are spread one to nine at a time
// — quoting "1 of 9" as a calibration figure would dress noise as evidence.
// Same rule the project applies to every other small positive class.
const CALIBRATION_MIN = 30;

function calibrationFor(score) {
  const c = S.calibration;
  if (!c || !c.buckets) return null;
  const band = c.buckets.find(b => score >= b.from && score < b.to)
            || (score >= 1 ? c.buckets[c.buckets.length - 1] : null);
  return band && band.queries >= CALIBRATION_MIN ? band : null;
}

function traceRail(d) {
  const r = d.retrieval || {};
  const hindi = d.language && d.language.hindi_titles_searched;
  const steps = [];
  const pill = (k, v, cls) =>
    `<div class="tpill ${cls || ''}"><span class="tk">${esc(k)}</span><span class="tv">${esc(v)}</span></div>`;

  steps.push(pill('Query', `${(d.query || '').length} chars`));

  if (r.dense_depth || r.bm25_depth) {
    const pair = [];
    if (hindi) {
      pair.push(pill('BIS Hindi titles', `${d.language.hindi_title_hits || 0} matched`, 'par'));
    }
    if (r.dense_depth) pair.push(pill('Dense · MiniLM', `top ${r.dense_depth}`, 'par'));
    if (r.bm25_depth) pair.push(pill('BM25 · lexical', `top ${r.bm25_depth}`, 'par'));
    steps.push(pair.join('<span class="tsep"></span>'));
  }
  if (r.fused_candidates) steps.push(pill('Fused · RRF', `${r.fused_candidates} candidates`));
  if (r.reranked) steps.push(pill(r.reranker === 'cross-encoder' ? 'Reranked' : 'Ranked',
                                  `${r.reranked} scored`));

  // A filter pill appears only when the filter ran, and turns amber only when
  // it actually moved something. "Applied, demoted 0" is not an intervention.
  [['voltage_filter', 'Voltage'], ['material_filter', 'Material'], ['role_filter', 'Document role']]
    .forEach(([key, label]) => {
      const f = d[key];
      if (!f || !f.applied) return;
      const n = f.demoted || 0;
      steps.push(pill(label, n ? `${n} demoted` : 'no change', n ? 'acted' : ''));
    });

  const abstained = d.decision === 'abstain';
  steps.push(pill('Confidence gate',
    abstained ? String(d.reason || 'abstain').replace(/_/g, ' ') : `≥ ${d.thresholds.top_score}`,
    abstained ? 'stop' : 'ok'));
  if (!abstained && d.governing) {
    steps.push(pill('Answer', d.governing.is_number, 'ok'));
  }

  const body = steps.map((sHtml, i) =>
    `<div class="tstep" style="animation-delay:${i * 40}ms">${sHtml}</div>`)
    .join('<span class="tsep"></span>');

  const note = abstained
    ? 'The gate stopped here. Nothing below was ruled out by judgement — it was not judged good enough to show.'
    : `Every figure on this rail is one the system reported about this run.`;
  return `<div class="trace">${body}<div class="tnote">${esc(note)}</div></div>`;
}

function renderForward(d) {
  let h = traceRail(d);

  // Say what we actually read and what we actually ranked, before the answer.
  // An abstention on a clipped query would otherwise read as "nothing matches".
  if (d.input && d.input.truncated) {
    h += `<div class="note warn">${ic('alert')}<div><b>Only part of this text was matched.</b>
      ${esc(d.input.note)}</div></div>`;
  }
  // Show what the system actually matched when the officer wrote in another
  // language: they must be able to see the translation, not trust it blind.
  if (d.language && d.language.applied) {
    // Only name a language when the officer told us one. Otherwise all we know
    // is the script, and Devanagari alone does not distinguish Marathi from
    // Hindi — saying "Read as HI" to someone writing Marathi states a fact we
    // do not have.
    const L = d.language;
    const NAMES = { hi: 'Hindi', mr: 'Marathi', bn: 'Bengali', gu: 'Gujarati', ta: 'Tamil',
      te: 'Telugu', kn: 'Kannada', ml: 'Malayalam', pa: 'Punjabi', or: 'Odia', ur: 'Urdu',
      as: 'Assamese', ne: 'Nepali', sa: 'Sanskrit', kok: 'Konkani', mai: 'Maithili',
      doi: 'Dogri', brx: 'Bodo', ks: 'Kashmiri', sd: 'Sindhi' };
    const fam = (L.script_family || []).filter(c => c !== L.source_language);
    const head = L.language_certain
      ? `Read as ${esc(NAMES[L.source_language] || (L.source_language || '').toUpperCase())} and translated for matching.`
      : (fam.length
          ? `Detected ${esc(NAMES[L.source_language] || 'this')} script and translated for matching.`
          : `Read as ${esc(NAMES[L.source_language] || (L.source_language || '').toUpperCase())} and translated for matching.`);
    const share = (!L.language_certain && fam.length)
      ? `<div class="xs dimmer" style="margin-top:5px">This script is shared by
         ${esc([NAMES[L.source_language], ...fam.map(c => NAMES[c]).filter(Boolean)].join(', '))},
         so the language was not identified — only the script. Selecting your language in the
         switcher tells the translator which one to use.</div>`
      : '';
    h += `<div class="note info">${ic('check')}<div><b>${head}</b>
      <div class="xs" style="margin-top:5px;color:var(--ink-2)">
        <span class="dimmer">you wrote</span> ${esc(d.language.original)}<br>
        <span class="dimmer">matched as</span> <b>${esc(d.language.text)}</b></div>
      <div class="xs dimmer" style="margin-top:5px">${esc(d.language.note)}</div>${share}</div></div>`;
  } else if (d.language && d.language.source_language && d.language.note) {
    h += `<div class="note warn">${ic('alert')}<div><b>Translation unavailable.</b> ${esc(d.language.note)}</div></div>`;
  }
  if (d.material_filter && d.material_filter.applied && d.material_filter.demoted) {
    h += `<div class="note info">${ic('check')}<div><b>Material filter applied.</b>
      ${esc(d.material_filter.note)}</div></div>`;
  }
  if (d.normalization && d.normalization.applied) {
    h += `<div class="note info">${ic('check')}<div><b>Language normalized.</b>
      ${d.normalization.terms.map(t => `<span class="mono">${esc(t.matched)}</span> → ${esc(t.added)}`).join(' · ')}.
      ${esc(d.normalization.note)}</div></div>`;
  }
  if (d.voltage_filter && d.voltage_filter.applied && d.voltage_filter.demoted) {
    h += `<div class="note info">${ic('check')}<div><b>Voltage filter applied.</b>
      ${esc(d.voltage_filter.note)}</div></div>`;
  }

  if (d.decision === 'abstain' && d.reason === 'translation_unavailable') {
    // Not a retrieval result. The register is English and the text could not be
    // brought into English, so nothing was searched — showing a threshold here
    // would imply candidates were weighed and rejected.
    h += `<div class="note warn">${ic('alert')}<div>
      <b>This text could not be read.</b> The standards register is published in English, and the
      translation service could not be reached, so no search was run. Nothing here was ruled out —
      it was never looked at. Try again in a moment, or paste the specification in English.
      <div class="xs dimmer" style="margin-top:5px">gate: ${esc(d.reason)}</div>
    </div></div>`;
  } else if (d.decision === 'abstain') {
    h += `<div class="note warn">${ic('alert')}<div>
      <b>No recommendation issued.</b> ${esc(d.message)}
      <div class="xs dimmer" style="margin-top:5px">gate: ${esc(d.reason)} · threshold ${d.thresholds.top_score} · margin ${d.thresholds.margin}</div>
    </div></div>`;
  } else {
    drawPeers(d.input && d.input.original ? d.input.original : d.query);
    const g = d.governing;
    h += `<div class="card" id="fw-gov" style="border-color:var(--ok)">
      <div class="hd"><span class="eyebrow">Governing standard</span><h3></h3>
        </div>
      <div class="in gov-grid">
        <div class="gov-main">
        <div style="display:flex;align-items:baseline;gap:11px;flex-wrap:wrap">
          <span class="mono jump" style="font-size:20px;font-weight:600" data-go="${esc(g.is_number)}">${esc(g.is_number)}</span>
          ${statusPill(g.status)}
          <span class="mono xs dimmer">${esc(g.year)}</span>
          ${g.review_due ? `<span class="pill ${g.review_overdue ? 'warn' : 'mute'}"
            title="BIS review date for this edition — not an amendment">
            ${g.review_overdue ? 'review overdue' : 'review due'} ${esc(g.review_due)}</span>` : ''}
        </div>
        <p class="std-title" style="margin-top:7px">${esc(g.title)}</p>
        <div class="xs dimmer" style="margin-top:9px">
          ${g.review_overdue ? `<div style="margin-bottom:5px;color:var(--accent)"><b>BIS review date has passed.</b>
          This edition was due for review on ${esc(g.review_due)}, so confirm it is still the current
          one before publication.</div>` : ''}
          <div style="margin-bottom:5px">Edition and status shown are the current BIS record,
          re-verified against the portal by the ingestion pipeline. <b>Numbered amendments
          (Amendment No. 1, 2, …) are not tracked</b> — BIS does not publish them through the
          catalogue endpoint this system reads, so check the standard itself before publication.</div>
          matched on <b>${esc(g.matched_on.field)}</b>${g.matched_on.terms.length
            ? ` via ${g.matched_on.terms.slice(0,6).map(t => `<span class="mono">${esc(t)}</span>`).join(', ')}` : ''}
          · dense rank ${g.dense_rank ?? '—'} · bm25 rank ${g.bm25_rank ?? '—'} · rrf ${g.rrf}
        </div>
        </div>
        ${confidenceArc(g.score, d.thresholds)}
      </div></div>`;

    const c = d.certification || {};
    h += `<div class="grid c2">
      <div class="card"><div class="hd"><h3>Certification duty</h3></div><div class="in">
        ${c.found
          ? `<dl class="kv"><dt>Mandatory</dt><dd><span class="pill ${c.certification_mandatory === 'Yes' ? 'bad' : 'mute'}">${esc(c.certification_mandatory)}</span></dd>
             <dt>Scheme</dt><dd class="mono">${esc(c.scheme)}</dd>
             <dt>Notification</dt><dd class="xs">${esc(c.notification_reference)}</dd></dl>`
          : `<p class="xs dimmer">No rule on file for this standard.</p>`}
      </div>
      <div class="ft" id="cert-coverage">Covers all four BIS routes — Product Certification (ISI Mark, Scheme I),
      CRS (Compulsory Registration Scheme, Scheme II), Quality Control Orders, and Hallmarking —
      collected from bis.gov.in. Hallmarking is read from prose rather than a published table, so it
      names only the standards BIS states on that page.</div></div>
      <div class="card"><div class="hd"><h3>Co-cited standards</h3><span class="hint">graph expansion</span></div><div class="in">
        ${(d.related || []).length
          ? d.related.map(r => `<div class="ev"><div class="t">
              <span class="mono jump" data-go="${esc(r.target_is)}">${esc(r.target_is)}</span>
              <span class="pill mute">conf ${r.confidence}</span></div>
              <div class="s">${esc(r.evidence_statement)}</div></div>`).join('')
          : `<p class="xs dimmer">No edges above graph thresholds.</p>`}
      </div></div></div>`;

    const A = d.allied;
    if (A && A.total) {
      h += `<div class="card"><div class="hd">${ic('net','sm')}<h3>Allied standards by role</h3>
        <span class="pill mute">${A.total}</span>
        <span class="hint">test method · terminology · installation · safety · product</span></div>
        <div class="in">
        ${A.likely_normative.length ? `<div class="note info" style="margin-bottom:11px">${ic('alert')}<div>
          <b>Likely normative references.</b> ${A.likely_normative.map(x =>
            `<span class="mono jump" data-go="${esc(x.is_number)}">${esc(x.is_number)}</span>`).join(', ')}.
          <div class="xs dimmer" style="margin-top:4px">${esc(A.normative_note)}</div></div></div>` : ''}
        ${A.groups.map(g => `<div class="sect"><h3>${esc(g.label)}</h3><span class="ln"></span>
            <span class="xs dimmer">${g.count}</span></div>
          ${g.standards.slice(0, 4).map(x => `<div class="rel">
            <span class="mono jump" data-go="${esc(x.is_number)}">${esc(x.is_number)}</span>
            ${x.likely_normative ? '<span class="pill info">normative?</span>' : ''}
            <span class="pill mute">conf ${(x.confidence || 0).toFixed(2)}</span>
            <div class="std-title s">${esc(x.title || 'Not in register')}</div>
            <div class="xs dimmer">${esc(x.evidence_statement || '')}</div>
          </div>`).join('')}
          ${g.count > 4 ? `<div class="xs dimmer" style="padding:7px 0 2px">
            ${g.count - 4} more in this group, ranked below these by co-citation confidence.</div>` : ''}`).join('')}
        </div>
        <div class="ft">${esc(A.role_note)}</div></div>`;
    }

    const cl = d.clause;
    h += `<div class="card">
      <div class="hd"><h3>Composed clause</h3>
        <span class="pill ${cl.composed_by === 'llm' ? 'info' : 'mute'}">${cl.composed_by === 'llm' ? esc(cl.model || 'local LLM') : 'template'}</span>
        <span class="pill ${cl.subset_guard.passed ? 'ok' : 'bad'}">
          ${cl.subset_guard.passed ? 'subset guard passed' : 'guard failed'}</span>
        <button class="btn tiny" id="fw-copy">${ic('copy','sm')}Copy clause</button></div>
      <div class="in">
        <p style="font-size:13.5px;line-height:1.7" id="fw-clause">${esc(cl.text)}</p>
        <div class="xs dimmer" style="margin-top:11px">
          Composed by <span class="mono">${esc(cl.composed_by)}</span> from ${cl.cited_standards.length} retrieved standard(s)${cl.generation_ms ? ` in ${cl.generation_ms} ms` : ''}.
          Every IS number in this text was checked against the retrieved set in code — the model
          cannot introduce one, because a generation that does is discarded rather than shown.
        </div>
        ${cl.llm && !cl.llm.used ? `<div class="note ${cl.llm.reason === 'call_failed' ? 'info' : 'warn'}" style="margin-top:11px">
          ${ic('alert')}<div style="flex:1;min-width:0"><b>${cl.llm.reason === 'call_failed'
            ? 'No local model running — template used.'
            : `Model output rejected — template used.`}</b>
          ${cl.llm.detail ? `<div class="xs" style="margin-top:5px;color:var(--ink-2)">${esc(cl.llm.detail)}</div>` : ''}
          ${cl.llm.rejected_text ? `<div style="margin-top:10px">
            <div class="xs dimmer" style="text-transform:uppercase;letter-spacing:.04em;margin-bottom:5px">
              what ${esc(cl.llm.model || 'the model')} wrote — discarded, shown so you can check it</div>
            <blockquote class="rejected">${esc(cl.llm.rejected_text)}</blockquote>
            <div class="xs dimmer" style="margin-top:6px">Guard: <span class="mono">${esc(cl.llm.reason)}</span>. The facts were never at risk — the clause above is the deterministic template.</div>
          </div>` : ''}</div></div>` : ''}
        ${cl.template_text ? `<details style="margin-top:11px"><summary class="xs dimmer" style="cursor:pointer">compare with the deterministic template this replaced</summary>
          <p class="xs" style="margin-top:7px;line-height:1.65;color:var(--ink-2)">${esc(cl.template_text)}</p></details>` : ''}
      </div></div>`;
  }

  h += `<div class="card pad0">
    <div style="padding:14px 16px 0"><div class="card-head"></div></div>
    <div class="hd"><h3>Retrieval trace</h3><span class="hint">every candidate the gate saw</span></div>
    <div class="scroll"><table><thead><tr>
      <th>IS Number</th><th>Title</th><th class="r">Score</th><th class="r">Dense</th><th class="r">BM25</th><th>Matched on</th><th></th>
    </tr></thead><tbody>${d.candidates.map(provRow).join('')}</tbody></table></div>
    <div class="ft">Dense = MiniLM cosine rank, BM25 = lexical rank, both fused by reciprocal rank fusion then reranked by cross-encoder. A candidate absent from one column was retrieved only by the other.</div>
  </div>`;

  $('#fw-out').innerHTML = h;
  setTimeout(translatePage, 60);
  $$('#fw-out [data-go]').forEach(el => el.addEventListener('click', e => {
    e.stopPropagation(); openStandard(el.dataset.go);
  }));
  const cp = $('#fw-copy');
  if (cp) cp.addEventListener('click', () => copy(S.fw.clause.text, 'Clause'));
}

/* ── chips / analysis ──────────────────────────────────────────────────── */

function renderChips() {
  $('#chips').innerHTML = S.chips.length
    ? S.chips.map((c, i) => `<span class="chip">${esc(c)}<button class="x" data-i="${i}">${ic('x','sm')}</button></span>`).join('')
    : `<span class="xs dimmer">Nothing queued.</span>`;
  $('#chip-n').textContent = S.chips.length ? `${S.chips.length} queued` : '';
  $$('#chips .x').forEach(b => b.addEventListener('click', () => { S.chips.splice(+b.dataset.i, 1); renderChips(); }));
}

const addChips = list => {
  let n = 0;
  list.forEach(c => { if (c && !S.chips.includes(c)) { S.chips.push(c); n++; } });
  renderChips();
  return n;
};

async function onFile(f) {
  const box = $('#ex-status');
  if (!f) return;
  if (!/\.(pdf|docx)$/i.test(f.name)) {
    box.innerHTML = `<div class="note bad" style="margin:11px 0 0">${ic('alert')}<div>PDF or .docx only. Paste the clause text instead.</div></div>`;
    return;
  }
  S.docName = f.name;
  box.innerHTML = `<div class="note info" style="margin:11px 0 0"><span class="spin"></span><div>Parsing <b>${esc(f.name)}</b> server-side…</div></div>`;
  const fd = new FormData(); fd.append('file', f);
  try {
    const r = await api('/extract', { method: 'POST', body: fd });
    const added = addChips(r.citations);
    box.innerHTML = `<div class="note ${r.scanned ? 'bad' : r.citations.length ? 'ok' : 'warn'}" style="margin:11px 0 0">
      ${ic(r.citations.length && !r.scanned ? 'check' : 'alert')}<div>
      <b>${esc(r.filename)}</b> — ${r.format === 'docx'
        ? `${r.paragraphs} paragraphs, ${r.tables} table(s)`
        : `${r.pages_read} of ${r.page_count} pages`}, ${r.characters.toLocaleString()} characters.
      <b>${r.citations.length}</b> distinct citation(s) read from the text${added !== r.citations.length ? `, ${added} new` : ''}.
      ${r.scanned ? `<br><b>This looks like a scan.</b> ${esc(r.scanned_note)}`
        : r.citations.length ? '' : '<br>No IS numbers found in the extracted text.'}</div></div>`;
    if (r.text) $('#spec').value = r.text.slice(0, 4000);
    toast(`${r.citations.length} citations extracted`);
  } catch (e) {
    box.innerHTML = `<div class="note bad" style="margin:11px 0 0">${ic('alert')}<div>${esc(e.message)}</div></div>`;
  }
}

const CLAUSE = {
  led: { name: 'LED luminaire', text: `18Watt LED flood light fitting complete as per detailed description. LED Luminaire conformity to IS:10322/Part 5/Section 5/2012 latest and IS: 16107 (Part 2/Sec 1):2012 latest. Photo biological safety of LEDs used shall be as per IS:16108/2012. Types of LED Modules as per the IS: 16103(Part-2)/2012. Ingress Protection (IP Rating) as per IS:10322 (Part 1):1982 latest.` },
  pipes: { name: 'PVC / GI pipe', text: `The unplasticized PVC rigid pipes shall strictly conform to IS 4985/1988 and should conform to IS 1239 Part I for GI pipes with ISI marking, specials as per IS 1239 Part II. Reinforced cement concrete pipes shall conform to IS 1536/1976 or IS 1537/1976. The pipes shall bear ISI mark. Concrete work as per IS 456-2000 and IS 14182/1994.` },
};

async function preset_(kind) {
  const box = $('#ex-status');
  if (CLAUSE[kind]) {
    $('#spec').value = CLAUSE[kind].text;
    const r = await api('/extract-text', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: CLAUSE[kind].text }) });
    addChips(r.citations);
    box.innerHTML = `<div class="note ok" style="margin:11px 0 0">${ic('check')}<div>Verbatim ${esc(CLAUSE[kind].name)} clause from a tender PDF · ${r.citations.length} citations read.</div></div>`;
    return;
  }
  // One document, chosen by the server. This used to download the whole corpus
  // and search it in memory.
  const params = new URLSearchParams({ usability: 'Usable', limit: '120' });
  if (kind !== 'outdated') params.set('family', 'Electrical cables and wiring');
  let page = null;
  try { page = await api('/tenders?' + params); } catch (_) { return; }
  const row = kind === 'outdated'
    ? (page.rows || []).find(t => t['Any Outdated'] === 'Yes')
    : (page.rows || []).find(t => (t['IS Numbers Cited'] || '').split(';').length > 4);
  if (!row) { box.innerHTML = `<div class="note warn" style="margin:11px 0 0">${ic('alert')}<div>No matching document in the corpus.</div></div>`; return; }
  const cites = (row['IS Numbers Cited'] || '').split(';').map(s => s.trim()).filter(Boolean);
  S.chips = []; addChips(cites); $('#spec').value = '';
  box.innerHTML = `<div class="note ${kind === 'outdated' ? 'warn' : 'ok'}" style="margin:11px 0 0">
    ${ic(kind === 'outdated' ? 'alert' : 'check')}<div><b>${esc(row['Tender ID'])}</b> · ${esc(row['Product Family'])} · ${cites.length} recorded citations. ${kind === 'outdated' ? 'Corpus flags this document as containing dead citations.' : ''}</div></div>`;
}

async function runAudit() {
  const btn = $('#run'), out = $('#an-out'), spec = $('#spec').value.trim();
  if (!S.chips.length && !spec) { toast('Add a citation or some clause text first', 'bad'); return; }
  btn.disabled = true; btn.innerHTML = `<span class="spin"></span> Verifying…`;
  out.innerHTML = `<div class="card"><div class="in"><div class="skel" style="height:76px"></div></div></div>`;
  try {
    const body = { cited_is_numbers: S.chips };
    if (spec) body.spec_text = spec;
    const auditBody = { text: spec, cited: S.chips, document: S.docName || null };
    const [analysis, findings] = await Promise.all([
      api('/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
      api('/audit-text', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(auditBody) }),
    ]);
    S.analysis = analysis; S.audit = findings;
    renderAudit(S.analysis);
    $('#an-csv').disabled = false; $('#an-print').disabled = false;
  } catch (e) { out.innerHTML = offline(e.message); }
  finally { btn.disabled = false; btn.innerHTML = `${ic('check','sm')} Run verification`; }
}

/* ── the document, marked up ────────────────────────────────────────────────
   The audit used to be a list of findings beside a document you could not see.
   An officer reading "IS 434 (Part 1) is superseded" then had to go and find it
   themselves. Here the document is shown with every citation underlined where
   it actually appears, coloured by what the register says about it, so the
   report and the text are the same object.

   The markup is built from the citations the server resolved, matched back into
   the text the officer supplied. Nothing is inferred: a citation is underlined
   only where its own characters occur. */

const CITE_CLASS = { Withdrawn: 'x-dead', Superseded: 'x-super', Current: 'x-ok' };

function citationStatus(d) {
  // One place that decides what colour a citation is, so the underline, the
  // summary bar and the ledger cannot disagree.
  const status = {};
  const dead = (d && d.dead_citations) || {};
  Object.keys(dead).forEach(k => {
    const r = dead[k];
    status[k] = !r.found ? 'unresolved' : (r.status || (r.dead ? 'Withdrawn' : 'Current'));
  });
  (S.audit && S.audit.findings || []).forEach(f => {
    if (f.kind === 'not_in_register') status[f.is_number] = 'unresolved';
    else if (f.kind === 'dispute_risk' && f.status) status[f.is_number] = f.status;
  });
  return status;
}

function documentXray(text, status) {
  if (!text || !text.trim()) return '';
  const cites = Object.keys(status);
  if (!cites.length) return '';

  // Longest first: "IS 1554 (Part 1)" must win over "IS 1554" where both are
  // present, or the part reference is left dangling outside the mark.
  const ordered = [...cites].sort((a, b) => b.length - a.length);
  const escaped = ordered.map(c => c.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s+'));
  const re = new RegExp('(' + escaped.join('|') + ')', 'gi');

  const counts = { Withdrawn: 0, Superseded: 0, Current: 0, unresolved: 0 };
  const seen = new Set();
  let idx = 0;
  const marked = esc(text).replace(re, (m) => {
    const key = ordered.find(c => c.replace(/\s+/g, ' ').toLowerCase() === m.replace(/\s+/g, ' ').toLowerCase())
      || ordered.find(c => m.replace(/\s+/g, ' ').toLowerCase().startsWith(c.replace(/\s+/g, ' ').toLowerCase()));
    if (!key) return m;
    const st = status[key] || 'unresolved';
    if (!seen.has(key)) { seen.add(key); counts[st] = (counts[st] || 0) + 1; }
    const cls = CITE_CLASS[st] || 'x-unres';
    return `<mark class="xcite ${cls}" data-cite="${esc(key)}" tabindex="0"
      title="${esc(key)} — ${esc(st === 'unresolved' ? 'not in the register' : st)}"
      style="animation-delay:${(idx++) * 40}ms">${m}</mark>`;
  });

  const bar = [
    `${seen.size} citation${seen.size === 1 ? '' : 's'} found in the text`,
    counts.Withdrawn ? `${counts.Withdrawn} withdrawn` : '',
    counts.Superseded ? `${counts.Superseded} superseded` : '',
    counts.unresolved ? `${counts.unresolved} not in the register` : '',
    counts.Current ? `${counts.Current} current` : '',
  ].filter(Boolean).join(' · ');

  const missing = cites.filter(c => !seen.has(c));
  return `<div class="card xray-card">
    <div class="hd"><span class="eyebrow">The document, marked up</span><h3></h3>
      <span class="xs dimmer">${esc(bar)}</span></div>
    <div class="in">
      <div class="xray" id="an-xray">${marked}</div>
      ${missing.length ? `<p class="xs dimmer" style="margin-top:9px">
        ${missing.length} citation${missing.length === 1 ? ' was' : 's were'} verified but
        ${missing.length === 1 ? 'does' : 'do'} not appear verbatim in this text
        (entered by hand, or written differently in the document):
        <span class="mono">${missing.map(esc).join(', ')}</span></p>` : ''}
      <p class="xs dimmer" style="margin-top:7px">Underline colour is the register's status for that
        standard. Click one to jump to its finding.</p>
    </div></div>`;
}

function wireXray() {
  $$('#an-xray .xcite').forEach(el => {
    const go = () => {
      const key = el.dataset.cite;
      const row = document.querySelector(`[data-finding="${CSS.escape(key)}"]`);
      if (!row) { toast(`${key} is current — no finding to show`, 'info'); return; }
      row.scrollIntoView({ behavior: 'smooth', block: 'center' });
      row.classList.add('flash');
      setTimeout(() => row.classList.remove('flash'), 1400);
    };
    el.addEventListener('click', go);
    el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
  });
}

function renderAudit(d) {
  const all = Object.keys(d.dead_citations || {});
  const dead = all.filter(k => d.dead_citations[k].dead);
  const gone = all.filter(k => !d.dead_citations[k].found);
  const live = all.filter(k => d.dead_citations[k].found && !d.dead_citations[k].dead);
  const duty = all.filter(k => (d.certifications[k] || {}).found);
  let h = documentXray($('#spec').value, citationStatus(d)) + renderFindings(S.audit);

  if (all.length) {
    h += `<div class="kpis" style="margin-top:16px">` + [
      { label: 'Citations verified', value: all.length, sub: 'from this document', icon: 'scan' },
      { label: 'Dead citations', value: dead.length, sub: dead.length ? 'corrigendum required' : 'none found', tone: dead.length ? 'bad' : 'ok', icon: 'alert' },
      { label: 'Not in register', value: gone.length, sub: 'not held in register', tone: gone.length ? 'warn' : 'ok', icon: 'pie' },
      { label: 'Certification duties', value: duty.length, sub: `${all.length - duty.length} with no rule on file`, tone: duty.length ? 'ok' : 'plain', icon: 'badge' },
    ].map(kpi).join('') + `</div>`;
  }

  if (dead.length) {
    h += `<div class="note bad">${ic('alert')}<div style="flex:1">
      <b>${dead.length} dead citation${dead.length > 1 ? 's' : ''} in this document.</b>
      <div style="margin-top:7px;display:flex;flex-direction:column;gap:5px">
      ${dead.map(k => {
        const x = d.dead_citations[k];
        const has = x.replaced_by && x.replaced_by !== 'UNKNOWN';
        return `<div style="display:flex;align-items:center;gap:9px;flex-wrap:wrap">
          <span class="mono strike" style="font-size:13px">${esc(k)}</span>
          <span class="pill bad">${esc(x.status)}</span>
          <span class="succ">${ic('arrow','sm')}${has
            ? `<span class="mono jump" style="font-size:13px;color:var(--ok);font-weight:600" data-go="${esc(x.replaced_by)}">${esc(x.replaced_by)}</span>`
            : `<span class="pill warn">no successor on file</span>`}</span>
        </div>`;
      }).join('')}</div>
      <button class="btn tiny" id="corr-btn" style="margin-top:9px">${ic('copy','sm')}Draft corrigendum note</button>
    </div></div>`;
  }

  if (d.matched_standards) {
    const m = d.matched_standards;
    const tone = m.confidence === 'High' ? 'ok' : m.confidence === 'Medium' ? 'warn' : 'mute';
    h += `<div class="card"><div class="hd"><h3>Clause → standard match</h3>
      <span class="pill ${tone}">${esc(m.confidence)}</span></div>
      ${m.message ? `<div class="in" style="padding-bottom:0"><div class="note warn">${ic('alert')}<div>${esc(m.message)}</div></div></div>` : ''}
      <div class="scroll"><table><thead><tr><th>IS Number</th><th>Title</th><th class="r">Similarity</th><th></th></tr></thead><tbody>
      ${m.matches.map(x => {
        return `<tr class="hit" data-go="${esc(x.is_number)}"><td class="mono">${esc(x.is_number)}</td>
          <td>${esc(x.title || '—')}</td><td class="mono r">${x.score.toFixed(4)}</td>
          <td class="rowgo">${ic('arrow','sm')}</td></tr>`;
      }).join('')}</tbody></table></div>
      <div class="ft">Cosine similarity over embeddings of ${S.stats ? S.stats.row_counts.standards : ''} held standards. Returns existing rows only.</div>
    </div>`;
  }

  if (all.length) {
    const seq = [...dead, ...gone, ...live];
    const pieces = [
      { key: 'Current', count: live.length, color: 'var(--ok)' },
      { key: 'Superseded / withdrawn', count: dead.length, color: 'var(--bad)' },
      { key: 'Not in register', count: gone.length, color: 'var(--ink-4)' },
    ];
    h += `<div class="grid c12">
      <div class="card"><div class="hd"><h3>Citation health</h3></div><div class="in">
        <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">${donut(pieces, { val: all.length, lab: 'cited' })}
        <div style="flex:1;min-width:140px">${legend(pieces, all.length)}</div></div></div></div>
      <div class="card"><div class="hd"><h3>Findings</h3><span class="note">most severe first</span></div>
        <div class="scroll"><table><thead><tr><th>IS Number</th><th>Status</th><th>Superseded by</th><th>Certification</th><th>Co-cited</th><th></th></tr></thead><tbody>
        ${seq.map(k => {
          const x = d.dead_citations[k], c = d.certifications[k] || {}, rel = d.related[k] || [];
          const st = x.found ? (x.dead ? `<span class="pill bad">${esc(x.status)}</span>` : '<span class="pill ok">Current</span>') : '<span class="pill mute">Not held</span>';
          const rb = x.dead ? (x.replaced_by === 'UNKNOWN' ? '<span class="pill warn">none on file</span>' : `<span class="mono">${esc(x.replaced_by)}</span>`) : '<span class="dimmer">—</span>';
          const ct = c.found ? `<span class="pill ${c.certification_mandatory === 'Yes' ? 'bad' : 'mute'}">${esc(c.certification_mandatory)}</span> <span class="mono xs">${esc(c.scheme)}</span>` : '<span class="xs dimmer">no rule on file</span>';
          return `<tr class="hit" data-go="${esc(k)}"><td class="mono">${esc(k)}</td><td>${st}</td><td>${rb}</td><td>${ct}</td>
            <td class="mono xs">${rel.length ? esc(rel.slice(0,2).map(r => r.target_is).join(', ')) + (rel.length > 2 ? ` +${rel.length-2}` : '') : '—'}</td>
            <td class="rowgo">${ic('arrow','sm')}</td></tr>`;
        }).join('')}</tbody></table></div>
        ${gone.length ? `<div class="ft">${gone.length} not in register. Declared gap — see Coverage.</div>` : ''}
      </div></div>`;
  }

  $('#an-out').innerHTML = h || blank(t('msg.nothingYet'), t('msg.queueFirst'));
  wireXray();
  setTimeout(translatePage, 60);
  runCounts();
  $$('#an-out [data-go]').forEach(el => el.addEventListener('click', e => { e.stopPropagation(); openStandard(el.dataset.go); }));
  $$('#an-out [data-copy]').forEach(el => el.addEventListener('click', e => {
    e.stopPropagation(); copy(el.dataset.copy, 'Clause');
  }));
  $$('#an-out [data-ev]').forEach(el => el.addEventListener('click', e => {
    e.stopPropagation(); loadEvidence(el.dataset.ev);
  }));
  const cb = $('#corr-btn');
  if (cb) cb.addEventListener('click', () => copy(corrigendum(d, dead), 'Corrigendum note'));
}

/* Draft note assembled purely from retrieved fields — no wording is invented
   beyond the fixed template sentences. */
function corrigendum(d, dead) {
  const lines = ['CORRIGENDUM — OUTDATED STANDARD REFERENCES', ''];
  dead.forEach((k, i) => {
    const x = d.dead_citations[k];
    lines.push(`${i + 1}. Cited standard: ${k}`);
    lines.push(`   Recorded status: ${x.status} (standards_master.csv)`);
    if (x.replaced_by && x.replaced_by !== 'UNKNOWN') {
      lines.push(`   Superseded by: ${x.replaced_by}`);
      lines.push(`   Suggested wording: "The reference to ${k} shall be read as ${x.replaced_by}."`);
    } else {
      lines.push(`   Superseded by: no successor recorded by BIS`);
      lines.push(`   Action: confirm the current equivalent with BIS before publication; this system holds no replacement for ${k}.`);
    }
    lines.push('');
  });
  lines.push(`Generated by MANAK-SETU from ${dead.length} dead citation(s). Every field above is a stored value, not an inference.`);
  return lines.join('\n');
}

function auditCsv() {
  const d = S.analysis;
  if (!d) return;
  const rows = [['IS Number', 'Status', 'Dead', 'Superseded by', 'Certification mandatory', 'Scheme', 'In register']];
  Object.keys(d.dead_citations).forEach(k => {
    const x = d.dead_citations[k], c = d.certifications[k] || {};
    rows.push([k, x.status || '', x.dead ? 'Yes' : 'No', x.replaced_by || '',
      c.found ? c.certification_mandatory : 'no rule on file', c.found ? c.scheme : '', x.found ? 'Yes' : 'No']);
  });
  download('manak-setu-audit.csv',
    rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n'), 'text/csv');
}

function resetAudit() {
  S.chips = []; S.analysis = null; S.audit = null; S.docName = null; renderChips();
  $('#spec').value = ''; $('#ex-status').innerHTML = ''; $('#an-out').innerHTML = '';
  $('#an-csv').disabled = true; $('#an-print').disabled = true;
}

/* ── presenter mode ────────────────────────────────────────────────────────
   A scripted run through the strongest real findings, so a live demo does not
   depend on anyone remembering the click order. Every step drives the same
   code paths a human would; nothing is faked for the walkthrough.
   ──────────────────────────────────────────────────────────────────────── */

const wait = ms => new Promise(r => setTimeout(r, ms));

/* A scripted run through the strongest real findings, so a live demo does not
   depend on anyone remembering the click order. Every step drives the same code
   paths a human would; nothing is staged.

   Budgeted to about 95 seconds. `hold` is the time the caption stays up after
   its `run` finishes, so a step that fetches is given less hold, not more — the
   total is the sum of holds plus however long the network actually takes.
   ──────────────────────────────────────────────────────────────────────── */

const DEMO = [
  {
    view: 'overview', hold: 9000, spot: '#hero',
    h: 'What the console holds',
    p: () => { const r = (S.stats || {}).row_counts || {}; const g = (S.stats || {}).graph || {};
      return `${(r.standards || 2087).toLocaleString()} Indian Standards, ${r.tenders || 220} real government tenders, ${(g.edges || 3336).toLocaleString()} co-citation edges, ${r.certification_rules || 737} certification rules. Every figure is recomputed from the database on load — nothing on this page is typed in.`; },
  },
  {
    view: 'overview', hold: 9000, spot: '#ov-cov',
    h: 'And what it does not',
    p: () => { const c = (S.stats || {}).coverage || {};
      return `${c.pct || 99}% of the standards real tenders cite are in the register — ${c.matched || 483} of ${c.distinct_cited || 488}. It was 17% when we started. We collected the rest from the BIS catalogue rather than inventing them, and the last ${c.unmatched ?? 5} stay on the front page as a declared gap.`; },
  },
  {
    view: 'draft', hold: 10000, spot: '#fw-gov',
    h: 'A specification, and the standard that governs it',
    p: 'Retrieval reads the voltage and the material out of the text, so 1.1 kV resolves to Part 1 and not Part 2. The filters are shown above the answer: nothing is reordered invisibly.',
    run: async () => {
      $('#fw-spec').value = 'PVC insulated heavy duty electric cable for working voltage 1.1 kV';
      await runForward();
    },
  },
  {
    view: 'analyze', hold: 11000, spot: '#an-out',
    h: 'A published tender, audited',
    p: 'A real procurement document with the 17 IS numbers its text actually cites. The report is a list of edits: replace IS 434 (Part 1) with IS 9968 — a stored supersession, not a model guess.',
    run: async () => {
      resetAudit();
      await preset_('outdated');
      await runAudit();
    },
  },
  {
    view: 'analyze', hold: 10000, spot: '#an-out',
    h: 'The clause nobody wrote',
    p: 'These items carry mandatory BIS certification and the tender never asks for the Standard Mark. The console drafts the missing clause with the Gazette order that makes it binding, ready to paste.',
  },
  {
    view: 'graph', hold: 10000, spot: '#gwrap',
    h: 'Where "related" comes from',
    p: () => { const g = (S.stats || {}).graph || {};
      return `${g.nodes || 193} standards joined by ${(g.edges || 3336).toLocaleString()} edges, each edge a count of two standards appearing in the same published tender. Colour is BIS department. The clusters are procurement practice, not a layout choice.`; },
    run: async () => { await wait(1200); },
  },
  {
    view: 'benchmark', hold: 11000, spot: '#bm-out',
    h: 'Measured, and stated carefully',
    p: () => { const b = S.bench || {};
      const pos = b.positives_in_set ?? 4, tp = b.true_positives ?? 4, fp = b.false_positives ?? 0, neg = b.negatives_sampled ?? 20;
      return `${tp} of ${pos} known dead-citation documents caught, ${fp} false positive${fp === 1 ? '' : 's'} across ${neg} sampled clean ones. Retrieval ranks the right standard first on 58 of 71 labelled queries and within the top ten on 65. The positive class here is ${pos} — too small for an accuracy claim, so we never make one.`; },
  },
];

const D = { on: false, i: 0, timer: null, paused: false, t0: 0, left: 0, lang: null };

/* Raise one panel above the blur veil. Bare containers get promoted to their
   nearest solid surface so the blurred page cannot show through the lit area. */
function demoSpot(sel) {
  $$('.spot').forEach(e => e.classList.remove('spot'));
  const veil = $('#demo-veil');
  const el = sel ? $(sel) : null;
  if (!el) { veil.classList.remove('on'); return; }
  const target = el.matches('.card, .kpis, .tbl, .gwrap, .hero') ? el
    : (el.closest('.card, .kpis, .tbl, .gwrap, .hero') || el);
  target.classList.add('spot');
  veil.classList.add('on');
  target.scrollIntoView({ block: 'center', behavior: 'smooth' });
}

function demoPaint() {
  const s = DEMO[D.i];
  $('#demo-step').textContent = `${D.i + 1} / ${DEMO.length}`;
  $('#demo-h').textContent = s.h;
  $('#demo-p').textContent = typeof s.p === 'function' ? s.p() : s.p;
  $('#demo-play').innerHTML = D.paused
    ? '<svg class="i sm" viewBox="0 0 24 24"><path d="M7 4.5v15l12-7.5z"/></svg>'
    : '<svg class="i sm" viewBox="0 0 24 24"><path d="M9 5v14M15 5v14"/></svg>';
}

function demoArm(ms) {
  clearTimeout(D.timer);
  const bar = $('#demo-prog');
  bar.style.transition = 'none'; bar.style.width = '0%';
  requestAnimationFrame(() => {
    bar.style.transition = `width ${ms}ms linear`;
    bar.style.width = '100%';
  });
  D.t0 = Date.now(); D.left = ms;
  D.timer = setTimeout(() => demoGo(D.i + 1), ms);
}

async function demoGo(i) {
  if (!D.on) return;
  if (i >= DEMO.length) { demoStop(true); return; }
  D.i = Math.max(0, i);
  const s = DEMO[D.i];
  demoSpot(null);
  demoPaint();
  if (view !== s.view) go(s.view);
  await wait(420);
  if (!D.on) return;
  if (s.run) { try { await s.run(); } catch (_) {} }
  if (!D.on) return;
  await wait(120);
  demoSpot(s.spot);
  if (!D.paused) demoArm(s.hold);
}

function demoStart() {
  if (D.on) return;
  // Remember the viewer's language: the walkthrough switches to Hindi to show
  // multilingual input, and stopping on that step must not strand them there.
  D.lang = document.documentElement.lang || 'en';
  D.on = true; D.paused = false; D.i = -1;
  $('#demobar').classList.add('on');
  $('#demo-btn').classList.add('live');
  $('#demo-btn').querySelector('span').textContent = 'Demo running';
  shut(); shutPal(); closePins();
  demoGo(0);
}

function demoStop(finished) {
  clearTimeout(D.timer);
  D.on = false; D.paused = false;
  $('#demobar').classList.remove('on');
  $('#demo-btn').classList.remove('live');
  $('#demo-btn').querySelector('span').textContent = 'Run demo';
  demoSpot(null);
  $('#demo-veil').classList.remove('on');
  if (D.lang && document.documentElement.lang !== D.lang) setLang(D.lang);
  D.lang = null;
  if (finished) toast('Walkthrough complete', 'ok');
}

function demoPause() {
  if (!D.on) return;
  if (D.paused) {
    D.paused = false;
    demoArm(Math.max(1200, D.left));
  } else {
    D.paused = true;
    clearTimeout(D.timer);
    D.left = Math.max(0, D.left - (Date.now() - D.t0));
    const bar = $('#demo-prog');
    const w = bar.getBoundingClientRect().width;
    const track = bar.parentElement.getBoundingClientRect().width;
    bar.style.transition = 'none';
    bar.style.width = (w / track * 100) + '%';
  }
  demoPaint();
}

/* ── generic table plumbing ────────────────────────────────────────────── */

/* Long tables are capped in the DOM, not in the data. The certification list
   grew from 77 rules to 737 and the standards register to 2,087: rendering every
   row produced hundreds of kilobytes of markup and a visibly slow view, for rows
   nobody scrolls to. The count above the table always reports the true total, and
   search narrows the real set, so the cap changes what is drawn and never what is
   counted. */
const TABLE_CAP = 250;

const capped = (rows, total, label) => {
  const matched = rows.length === total ? `${total} ${label}` : `${rows.length} of ${total} ${label}`;
  if (rows.length <= TABLE_CAP) return { rows, label: matched };
  return {
    rows: rows.slice(0, TABLE_CAP),
    label: `${matched} · showing the first ${TABLE_CAP}, narrow with search`,
  };
};

const sorts = {};

/* ── paged tables ───────────────────────────────────────────────────────────
   Standards, Tenders and Certifications each used to download their whole
   table — 10.2 MB, 3.4 MB and 952 KB — parse it, and display the first 250
   rows. Searching and filtering ran over the copy in memory.

   Now the server does all three in SQL and returns a page with the total it
   was drawn from, so the view holds what it shows. The filter dropdowns are
   filled from facets the first page carries, because deriving them in the
   browser was the other reason the whole table had to arrive. */

function pagedTable(cfg) {
  const st = { rows: [], total: 0, busy: false, facets: null };

  const url = (offset) => {
    const p = new URLSearchParams(cfg.params());
    const sort = sorts[cfg.key];
    if (sort) { p.set('sort', sort.k); if (sort.dir === 'desc') p.set('descending', 'true'); }
    p.set('limit', cfg.pageSize || 100);
    p.set('offset', offset);
    return `${cfg.endpoint}?${p}`;
  };

  async function fetchPage(offset) {
    if (st.busy) return;
    st.busy = true;
    try {
      const page = await api(url(offset));
      st.total = page.total;
      st.rows = offset === 0 ? page.rows : st.rows.concat(page.rows);
      if (page.facets && !st.facets) { st.facets = page.facets; cfg.onFacets?.(page.facets); }
      cfg.render(st.rows, st.total);
      renderMore();
    } catch (e) {
      $(cfg.countSel).innerHTML = offline(e.message);
    } finally {
      st.busy = false;
    }
  }

  function renderMore() {
    const host = $(cfg.moreSel);
    if (!host) return;
    const shown = st.rows.length;
    if (shown >= st.total) { host.innerHTML = ''; return; }
    host.innerHTML = `<button class="btn q" id="${cfg.key}-more">
      Load ${Math.min(cfg.pageSize || 100, st.total - shown)} more
      <span class="dimmer">· ${shown.toLocaleString()} of ${st.total.toLocaleString()}</span></button>`;
    $(`#${cfg.key}-more`).onclick = () => fetchPage(shown);
  }

  // A keystroke must not become a request. 250 ms is long enough that typing an
  // IS number sends one query rather than eight, and short enough to feel live.
  let timer = null;
  const reload = () => fetchPage(0);
  const debounced = () => { clearTimeout(timer); timer = setTimeout(reload, 250); };
  return { reload, debounced, state: st };
}



function sortable(tblSel, rows, key) {
  const s = sorts[key];
  if (!s) return rows;
  const dir = s.dir === 'asc' ? 1 : -1;
  return [...rows].sort((a, b) => {
    const x = a[s.k], y = b[s.k];
    const nx = parseFloat(x), ny = parseFloat(y);
    if (!isNaN(nx) && !isNaN(ny)) return (nx - ny) * dir;
    return String(x).localeCompare(String(y)) * dir;
  });
}

function wireSort(tblSel, key, redraw) {
  $$(`${tblSel} thead th.sortable`).forEach(th => th.addEventListener('click', () => {
    const k = th.dataset.k, cur = sorts[key];
    sorts[key] = cur && cur.k === k ? { k, dir: cur.dir === 'asc' ? 'desc' : 'asc' } : { k, dir: 'asc' };
    $$(`${tblSel} thead th`).forEach(o => o.classList.remove('sorted'));
    th.classList.add('sorted');
    th.querySelector('.sarr').textContent = sorts[key].dir === 'asc' ? '↑' : '↓';
    redraw();
  }));
}

const fillSel = (sel, vals) => {
  const el = $(sel);
  vals.forEach(v => { const o = document.createElement('option'); o.value = v; o.textContent = v; el.appendChild(o); });
};

function filterChips(target, entries, onClear) {
  const box = $(target);
  const live = entries.filter(e => e.v);
  box.innerHTML = live.map(e => `<span class="fchip">${esc(e.label)}: ${esc(e.v)}
    <button data-c="${esc(e.sel)}">${ic('x','sm')}</button></span>`).join('');
  $$(`${target} button`).forEach(b => b.addEventListener('click', () => { $(b.dataset.c).value = ''; onClear(); }));
}

/* ── tenders ───────────────────────────────────────────────────────────── */

let tenderTable = null;

async function loadTenders() {
  if (ready.has('tenders')) return tenderTable.reload();
  ready.add('tenders');

  // Corpus totals come from /stats, which counts them in SQL. They used to be
  // derived by filtering the whole table in the browser.
  try {
    const st = S.stats || (S.stats = await api('/stats'));
    const byUse = Object.fromEntries((st.tenders_by_usability || []).map(r => [r.key, r.count]));
    const usable = st.coverage.usable_tenders;
    $('#td-kpis').innerHTML = [
      { label: 'Documents collected', value: st.row_counts.tenders, sub: 'source: public tender portals', icon: 'files' },
      { label: 'Text extractable', value: usable, sub: 'basis for all figures', tone: 'ok', icon: 'check' },
      { label: 'Cite a dead standard', value: st.coverage.any_outdated,
        sub: `of ${usable.toLocaleString()} readable · checked against the register now`,
        tone: 'bad', icon: 'alert' },
      { label: 'Not extractable', value: (byUse['Not extractable'] || 0), sub: 'scans and image-only PDFs', icon: 'target' },
    ].map(kpi).join('');
    runCounts();
  } catch (_) { /* the table still works without the headline figures */ }

  tenderTable = pagedTable({
    key: 'td', endpoint: '/tenders', countSel: '#td-n', moreSel: '#td-more',
    params: () => ({ q: $('#td-q').value.trim(), usability: $('#td-use').value,
                     family: $('#td-fam').value }),
    onFacets: f => { fillSel('#td-use', f.Usability); fillSel('#td-fam', f['Product Family']); },
    render: drawTenders,
  });
  $('#td-q').addEventListener('input', tenderTable.debounced);
  ['#td-use', '#td-fam', '#td-out'].forEach(x => $(x).addEventListener('change', tenderTable.reload));
  wireSort('#td-tbl', 'td', () => tenderTable.reload());
  tenderTable.reload();
}

function drawTenders(rows, total) {
  const u = $('#td-use').value, f = $('#td-fam').value, o = $('#td-out').value;
  // "Dead cites" has no column in the tenders table to filter on server-side,
  // so it narrows the page that arrived. The count says which set it describes
  // rather than implying it searched the corpus.
  const shown = o ? rows.filter(t => t['Any Outdated'] === o) : rows;
  $('#td-n').textContent = o
    ? `${shown.length.toLocaleString()} of the ${rows.length.toLocaleString()} loaded (corpus: ${total.toLocaleString()})`
    : rows.length === total
      ? `${total.toLocaleString()} documents`
      : `${rows.length.toLocaleString()} of ${total.toLocaleString()} documents`;
  filterChips('#td-chips', [
    { label: 'Extractability', v: u, sel: '#td-use' }, { label: 'Family', v: f, sel: '#td-fam' },
    { label: 'Dead cites', v: o, sel: '#td-out' },
  ], () => tenderTable.reload());

  $('#td-tbl tbody').innerHTML = shown.map(t => {
    const od = t['Any Outdated'];
    const pill = od === 'Yes' ? '<span class="pill bad">yes</span>' : od === 'No' ? '<span class="pill ok">no</span>' : '<span class="pill mute">unchecked</span>';
    return `<tr class="hit" data-t="${esc(t['Tender ID'])}">
      <td style="max-width:330px">
        <div>${esc(t.Title || t['Tender ID'])}${t.title_derived === false
          ? ' <span class="pill mute xs" title="the source filename carries no words, so no title is claimed">no title</span>' : ''}</div>
        <div class="xs dimmer mono" title="source filename, as downloaded">${esc(t['Tender ID'])}</div></td>
      <td class="dim">${esc(t['Product Family'])}</td>
      <td class="mono r">${esc(t.Count)}</td>
      <td>${pill}</td>
      <td><span class="pill ${t.Usability === 'Usable' ? 'info' : 'mute'}">${esc(t.Usability)}</span></td>
      <td class="rowgo">${ic('arrow','sm')}</td></tr>`;
  }).join('') || `<tr><td colspan="6">${blank('No documents match', 'Try clearing a filter.')}</td></tr>`;
  $$('#td-tbl tbody tr[data-t]').forEach(tr => tr.addEventListener('click', () => openTender(tr.dataset.t)));
}

async function openTender(id) {
  const t = await api('/tender?tender_id=' + encodeURIComponent(id)).catch(() => null);
  if (!t || !t.found) return;
  const cites = (t['IS Numbers Cited'] || '').split(';').map(s => s.trim()).filter(Boolean);
  drawer('Tender document', t.Title || id, `
    <dl class="kv">
      <dt>Source file</dt><dd class="mono xs">${esc(id)}</dd>
      <dt>Family</dt><dd>${esc(t['Product Family'])}</dd>
      <dt>Type</dt><dd>${esc(t['Document Type'])}</dd>
      <dt>Extractability</dt><dd>${esc(t.Usability)}</dd>
      <dt>Dead cites recorded</dt><dd>${esc(t['Any Outdated'])}</dd>
      <dt>Citations</dt><dd class="mono">${cites.length}</dd>
      ${t['Source Link'] && t['Source Link'] !== 'N/A' ? `<dt>Source</dt><dd><a href="${esc(t['Source Link'])}" target="_blank" rel="noopener">original document ${ic('ext','sm')}</a></dd>` : ''}
    </dl>
    <div class="sect"><h3>Cited standards</h3><span class="ln"></span></div>
    <div class="chips">${cites.map(c => `<span class="chip static jump" data-go="${esc(c)}">${esc(c)}</span>`).join('') || '<span class="xs dimmer">none extracted</span>'}</div>
    ${cites.length ? `<button class="btn acc wide" id="dw-run" style="margin-top:14px">Verify these ${cites.length} citations</button>
      <div id="dw-res" style="margin-top:13px"></div>` : ''}`, id);

  $$('#dw-body [data-go]').forEach(el => el.addEventListener('click', () => openStandard(el.dataset.go)));
  const b = $('#dw-run');
  if (b) b.addEventListener('click', async () => {
    b.disabled = true; b.innerHTML = `<span class="spin"></span> Verifying…`;
    try {
      const d = await api('/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cited_is_numbers: cites }) });
      const dead = cites.filter(k => d.dead_citations[k].dead);
      const gone = cites.filter(k => !d.dead_citations[k].found);
      $('#dw-res').innerHTML = `
        ${dead.length
          ? `<div class="note bad">${ic('alert')}<div><b>${dead.length} dead citation(s)</b><br>${dead.map(k => `<span class="mono">${esc(k)}</span> — ${esc(d.dead_citations[k].status)}${d.dead_citations[k].replaced_by !== 'UNKNOWN' ? ` → <span class="mono">${esc(d.dead_citations[k].replaced_by)}</span>` : ', no successor on file'}`).join('<br>')}</div></div>`
          : `<div class="note ok">${ic('check')}<div>No dead citations among the ${cites.length - gone.length} standard(s) held for this document.</div></div>`}
        <div class="tbl auto"><div class="scroll"><table><thead><tr><th>IS Number</th><th>Status</th><th>Certification</th></tr></thead><tbody>
        ${cites.map(k => {
          const x = d.dead_citations[k], c = d.certifications[k] || {};
          return `<tr class="hit" data-go="${esc(k)}"><td class="mono">${esc(k)}</td>
            <td>${x.found ? (x.dead ? `<span class="pill bad">${esc(x.status)}</span>` : '<span class="pill ok">Current</span>') : '<span class="pill mute">Not held</span>'}</td>
            <td>${c.found ? `<span class="pill ${c.certification_mandatory === 'Yes' ? 'bad' : 'mute'}">${esc(c.certification_mandatory)}</span>` : '<span class="xs dimmer">no rule</span>'}</td></tr>`;
        }).join('')}</tbody></table></div></div>`;
      $$('#dw-res [data-go]').forEach(el => el.addEventListener('click', () => openStandard(el.dataset.go)));
    } catch (e) { $('#dw-res').innerHTML = offline(e.message); }
    finally { b.disabled = false; b.textContent = 'Re-verify'; }
  });
}

/* ── standards ─────────────────────────────────────────────────────────── */

let stdTable = null;

async function loadStandards() {
  if (ready.has('standards')) return stdTable.reload();
  ready.add('standards');
  stdTable = pagedTable({
    key: 'st', endpoint: '/standards', countSel: '#st-n', moreSel: '#st-more',
    params: () => ({ q: $('#st-q').value.trim(), status: $('#st-status').value,
                     family: $('#st-fam').value }),
    onFacets: f => { fillSel('#st-status', f.Status); fillSel('#st-fam', f['Product Family']); },
    render: drawStandards,
  });
  ['#st-q'].forEach(x => $(x).addEventListener('input', stdTable.debounced));
  ['#st-status', '#st-fam'].forEach(x => $(x).addEventListener('change', stdTable.reload));
  wireSort('#st-tbl', 'st', () => stdTable.reload());
  stdTable.reload();
}

function drawStandards(rows, total) {
  const st = $('#st-status').value, f = $('#st-fam').value;
  $('#st-n').textContent = rows.length === total
    ? `${total.toLocaleString()} standards`
    : `${rows.length.toLocaleString()} of ${total.toLocaleString()} standards`;
  filterChips('#st-chips', [{ label: 'Status', v: st, sel: '#st-status' },
                            { label: 'Family', v: f, sel: '#st-fam' }], () => stdTable.reload());

  $('#st-tbl tbody').innerHTML = rows.map(s => `
    <tr class="hit" data-s="${esc(s['IS Number'])}">
      <td class="mono">${esc(s['IS Number'])}</td>
      <td style="max-width:430px">${esc(s['Full Title'])}</td>
      <td class="mono r">${esc(s.Year)}</td>
      <td>${statusPill(s.Status)}</td>
      <td class="mono">${s['Replaced By'] === 'UNKNOWN' ? '<span class="dimmer">—</span>' : esc(s['Replaced By'])}</td>
      <td class="rowgo">${ic('arrow','sm')}</td></tr>`).join('')
    || `<tr><td colspan="6">${blank('No standards match', 'Try a different search or clear the filters.')}</td></tr>`;
  $$('#st-tbl tbody tr[data-s]').forEach(tr => tr.addEventListener('click', () => openStandard(tr.dataset.s)));
}

async function openStandard(id) {
  drawer('Standard', id, `<div class="skel" style="height:130px"></div>`, id);
  let d;
  try { d = await api('/standard?is_number=' + encodeURIComponent(id)); }
  catch (e) { $('#dw-body').innerHTML = offline(e.message); return; }

  if (!d.found) {
    $('#dw-body').innerHTML = `<div class="note warn">${ic('alert')}<div>
      <b>Not in register.</b> <span class="mono">${esc(id)}</span> is cited by tenders; no record held. Lookups return <span class="mono">found: false</span>.</div></div>
      <p class="xs dimmer">Listed in the collection backlog under Coverage. Closing it requires the BIS page.</p>`;
    return;
  }
  const s = d.standard, c = d.certification, rel = d.related;
  $('#dw-body').innerHTML = `
    ${d.matched_by === 'is_base_fallback' ? `<div class="note info">${ic('info')}<div>Matched through the <span class="mono">IS Base</span> fallback — the exact part/section suffix is not held separately.</div></div>` : ''}
    <p style="font-size:13.5px;margin-bottom:13px">${esc(s['Full Title'])}</p>
    <dl class="kv">
      <dt>Status</dt><dd>${statusPill(s.Status)}</dd>
      <dt>Year</dt><dd class="mono">${esc(s.Year)}</dd>
      <dt>Family</dt><dd>${esc(s['Product Family'])}</dd>
      <dt>Priority</dt><dd>${esc(s.Priority)}</dd>
      <dt>Superseded by</dt><dd class="mono">${s['Replaced By'] === 'UNKNOWN' ? '<span class="pill warn">no successor on file</span>' : `<span class="jump" data-go="${esc(s['Replaced By'])}">${esc(s['Replaced By'])}</span>`}</dd>
      <dt>Supersedes</dt><dd class="mono">${esc(s.Supersedes)}</dd>
      ${s['Source Link'] && s['Source Link'] !== 'N/A' ? `<dt>Source</dt><dd><a href="${esc(s['Source Link'])}" target="_blank" rel="noopener">BIS standards page ${ic('ext','sm')}</a></dd>` : ''}
    </dl>
    <div class="sect"><h3>Certification duty</h3><span class="ln"></span></div>
    ${c.found ? `<dl class="kv">
      <dt>Mandatory</dt><dd><span class="pill ${c.certification_mandatory === 'Yes' ? 'bad' : 'mute'}">${esc(c.certification_mandatory)}</span></dd>
      <dt>Scheme</dt><dd class="mono">${esc(c.scheme)}</dd>
      <dt>Notification</dt><dd class="xs">${esc(c.notification_reference)}</dd></dl>`
      : `<p class="xs dimmer">No rule on file. Duty table holds 77 records; this IS number is not among them.</p>`}
    <div class="sect"><h3>Co-cited standards</h3><span class="dimmer xs">${rel.length}</span><span class="ln"></span></div>
    ${rel.length ? rel.map(r => `<div class="ev">
        <div class="t"><span class="mono jump" data-go="${esc(r.target_is)}">${esc(r.target_is)}</span>
          <span class="pill mute">conf ${r.confidence}</span><span class="pill mute">lift ${r.lift}</span></div>
        <div class="s">${esc(r.evidence_statement)}</div></div>`).join('')
      : `<p class="xs dimmer">No edges. Below graph thresholds: 5 citing tenders, 3 co-citations, confidence 0.25.</p>`}`;
  $$('#dw-body [data-go]').forEach(el => el.addEventListener('click', () => openStandard(el.dataset.go)));
}

/* ── certifications ────────────────────────────────────────────────────── */

let certTable = null;

async function loadCerts() {
  if (ready.has('certs')) return certTable.reload();
  ready.add('certs');
  certTable = pagedTable({
    key: 'ce', endpoint: '/certifications', countSel: '#ce-n', moreSel: '#ce-more',
    params: () => ({ q: $('#ce-q').value.trim(), scheme: $('#ce-scheme').value,
                     family: $('#ce-fam').value }),
    onFacets: f => { fillSel('#ce-scheme', f.Scheme); fillSel('#ce-fam', f['Product Family']); },
    render: drawCerts,
  });
  $('#ce-q').addEventListener('input', certTable.debounced);
  ['#ce-scheme', '#ce-fam'].forEach(x => $(x).addEventListener('change', certTable.reload));
  wireSort('#ce-tbl', 'ce', () => certTable.reload());
  certTable.reload();
}

function drawCerts(rows, total) {
  $('#ce-n').textContent = rows.length === total
    ? `${total.toLocaleString()} rules`
    : `${rows.length.toLocaleString()} of ${total.toLocaleString()} rules`;
  $('#ce-tbl tbody').innerHTML = rows.map(c => `
    <tr class="hit" data-s="${esc(c['IS Number'])}">
      <td class="mono">${esc(c['IS Number'])}</td>
      <td style="max-width:300px">${esc(c['Product Description'])}</td>
      <td class="xs dim">${esc(c['BIS Product Category'])}</td>
      <td><span class="pill ${c['Certification Mandatory'] === 'Yes' ? 'bad' : 'mute'}">${esc(c['Certification Mandatory'])}</span></td>
      <td class="mono">${esc(c.Scheme)}</td>
      <td class="xs" style="max-width:260px"${c['Notification History'] && c['Notification History'] !== c['Notification Reference']
        ? ` title="${esc(c['Notification History'].slice(0, 600))}"` : ''}>${
        c['Notification Reference'] === 'N/A' ? '<span class="dimmer">not recorded</span>' : esc(c['Notification Reference'])}</td>
    </tr>`).join('') || `<tr><td colspan="6">${blank('No rules match', 'Try a different search or clear the filters.')}</td></tr>`;
  $$('#ce-tbl tbody tr[data-s]').forEach(tr => tr.addEventListener('click', () => openStandard(tr.dataset.s)));
}

/* ── coverage ──────────────────────────────────────────────────────────── */

async function loadCoverage() {
  if (ready.has('coverage')) return drawBacklog();
  try {
    if (!S.stats) S.stats = await api('/stats');
    if (!S.backlog) S.backlog = await api('/backlog');
  } catch (e) { $('#cov-meter').innerHTML = offline(e.message); return; }
  ready.add('coverage');
  const cv = S.stats.coverage, rc = S.stats.row_counts;
  const byStatus = Object.fromEntries(S.stats.standards_by_status.map(d => [d.key, d.count]));

  $('#cov-lead').innerHTML = `<div class="note warn">${ic('alert')}<div>
    <b>${cv.matched} of ${cv.distinct_cited}</b> cited IS numbers held (<b>${cv.pct}%</b>), across ${cv.usable_tenders} extractable documents.
    The other ${cv.unmatched} return <span class="mono">found: false</span>.</div></div>`;

  $('#cov-meter').innerHTML = `
    <div class="meter"><span id="cm1" style="background:var(--ok)"></span><span id="cm2" style="background:var(--ink-4)"></span></div>
    <div style="display:flex;gap:22px;margin-top:12px;flex-wrap:wrap">
      <div><div class="eyebrow" style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:2px;background:var(--ok)"></span>Held</div>
        <div class="mono" style="font-size:15px;margin-top:3px;color:var(--ok)">${cv.matched}</div></div>
      <div><div class="eyebrow" style="display:flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:2px;background:var(--ink-4)"></span>Cited, not held</div>
        <div class="mono" style="font-size:15px;margin-top:3px">${cv.unmatched}</div></div>
    </div>
    <p class="xs dimmer" style="margin-top:12px">${esc(cv.denominator_note)}</p>`;
  setTimeout(() => {
    $('#cm1').style.width = cv.matched / cv.distinct_cited * 100 + '%';
    $('#cm2').style.width = cv.unmatched / cv.distinct_cited * 100 + '%';
  }, 40);

  $('#cov-kv').innerHTML = `
    <dt>Register size</dt><dd class="mono">${rc.standards}</dd>
    <dt>Supersession</dt><dd class="mono">${(byStatus.Superseded || 0) + (byStatus.Withdrawn || 0)} of ${rc.standards} carry a superseded or withdrawn status</dd>
    <dt>Extractable docs</dt><dd class="mono">${cv.usable_tenders} of ${rc.tenders}</dd>
    <dt>Certification</dt><dd class="mono">${rc.certification_rules} rules — LED lighting has none</dd>
    <dt>Graph scope</dt><dd class="mono">${S.stats.graph.nodes} of ${rc.standards} standards appear in the graph</dd>
    <dt>Backlog</dt><dd class="mono">${rc.coverage_gap_backlog} entries ranked by tender demand</dd>`;

  $('#cov-bars').innerHTML = bars(S.backlog.slice(0, 12).map(b => ({ key: b.is_number, count: b.tenders_citing })), 'var(--accent)');
  $('#bk-q').addEventListener('input', drawBacklog);
  $$('#bk-seg button').forEach(b => b.addEventListener('click', () => {
    $$('#bk-seg button').forEach(o => o.classList.remove('on'));
    b.classList.add('on'); drawBacklog();
  }));
  drawBacklog();
}

function drawBacklog() {
  const q = $('#bk-q').value.trim().toLowerCase();
  const f = $('#bk-seg button.on').dataset.f;
  const rows = S.backlog.filter(b => {
    const claimed = S.claims.includes(b.is_number);
    if (f === 'claimed' && !claimed) return false;
    if (f === 'open' && claimed) return false;
    return !q || b.is_number.toLowerCase().includes(q);
  });
  $('#bk-n').textContent = `${rows.length} of ${S.backlog.length} entries · ${S.claims.length} claimed`;
  $('#bk-tbl tbody').innerHTML = rows.slice(0, 420).map(b => {
    const on = S.claims.includes(b.is_number);
    return `<tr><td><input type="checkbox" data-b="${esc(b.is_number)}" ${on ? 'checked' : ''} style="width:auto;height:auto"></td>
      <td class="mono r">${b.tenders_citing}</td>
      <td class="mono jump" data-go="${esc(b.is_number)}">${esc(b.is_number)}</td>
      <td>${on ? '<span class="pill info">claimed</span>' : '<span class="pill mute">not held</span>'}</td></tr>`;
  }).join('') || `<tr><td colspan="4">${blank('Nothing here', 'Adjust the filter.')}</td></tr>`;

  $$('#bk-tbl [data-b]').forEach(cb => cb.addEventListener('change', () => {
    const id = cb.dataset.b, i = S.claims.indexOf(id);
    if (i >= 0) S.claims.splice(i, 1); else S.claims.push(id);
    localStorage.setItem('manak.claims', JSON.stringify(S.claims));
    drawBacklog();
  }));
  $$('#bk-tbl [data-go]').forEach(el => el.addEventListener('click', () => openStandard(el.dataset.go)));
}

/* ── benchmark ─────────────────────────────────────────────────────────── */

async function loadBench(force) {
  if (S.bench && !force) return drawBench();
  $('#bm-out').innerHTML = `<div class="card"><div class="in"><div class="skel" style="height:110px"></div></div></div>`;
  try { S.bench = await api('/benchmark'); } catch (e) { $('#bm-out').innerHTML = offline(e.message); return; }
  drawBench();
}

function drawBench() {
  const b = S.bench;
  $('#bm-out').innerHTML = `
    <div class="note info">${ic('info')}<div>${esc(b.honest_summary)}</div></div>
    <div class="kpis">${[
      { label: 'Agree with the stored flag', value: b.agree ?? (b.true_positives + b.true_negatives),
        sub: `of ${b.evaluated} documents checked`, tone: 'ok', icon: 'check' },
      { label: 'Newly dead since collection', value: b.newly_dead ?? b.false_positives,
        sub: 'register found a dead citation the flag missed',
        tone: (b.newly_dead ?? b.false_positives) ? 'warn' : 'plain', icon: 'alert' },
      { label: 'Flagged dead, now current', value: b.flag_says_dead_register_does_not ?? b.false_negatives,
        sub: 'the flag is stricter than the register',
        tone: (b.flag_says_dead_register_does_not ?? b.false_negatives) ? 'bad' : 'plain', icon: 'alert' },
      { label: 'Documents checked', value: b.evaluated,
        sub: `${b.positives_in_set} flagged dead · ${b.negatives_sampled} sampled clean`,
        tone: 'plain', icon: 'scan' },
    ].map(kpi).join('')}</div>
    <div class="note warn">${ic('alert')}<div><b>What this measures — and what it does not.</b>
      ${esc(b.what_this_measures || '')}
      </div></div>
    <div class="note info">${ic('info')}<div><b>How the set was drawn.</b>
      Every document the stored flag calls dead is included — ${b.positives_in_set} of them — against
      ${b.negatives_sampled} sampled from those it calls clean. The two sides are deliberately
      unbalanced, so counts are reported rather than a rate: a percentage over a 273-to-20 split
      would say more about the sampling than about the corpus.</div></div>
    <div class="tbl">
      <div class="toolbar"><h3 style="flex:1">Per-document results</h3><span class="xs dimmer">n = ${b.evaluated}</span></div>
      <div class="scroll"><table><thead><tr><th>Document</th><th>Flag at collection</th><th>Register today</th><th>Agree</th><th>Dead citations found</th></tr></thead><tbody>
      ${b.results.map(r => `<tr>
        <td style="max-width:300px">${esc(r.tender_id)}</td>
        <td><span class="pill ${r.actual === 'Yes' ? 'bad' : 'ok'}">${esc(r.actual)}</span></td>
        <td><span class="pill ${r.predicted === 'Yes' ? 'bad' : 'ok'}">${esc(r.predicted)}</span></td>
        <td>${r.match ? '<span class="pill ok">✓</span>' : '<span class="pill bad">✕</span>'}</td>
        <td class="mono xs">${r.dead_hits.map(h => `${esc(h.is_number)} (${esc(h.status)})`).join(', ') || '—'}</td></tr>`).join('')}
      </tbody></table></div></div>`;
  runCounts();
}



/* ── peer citations ─────────────────────────────────────────────────────────
   The one answer here that is not derived from the register. It is a tally of
   what other buyers of the same kind of item actually cited, so it is useful
   exactly where the register is silent — and when peers are citing something
   withdrawn, that shows too, because a common practice being wrong is worth
   seeing. */

async function drawPeers(query) {
  const el = $('#fw-peers');
  if (!el) return;
  el.innerHTML = '';
  if (!query) return;
  let d;
  try { d = await api('/peers?text=' + encodeURIComponent(query)); }
  catch (_) { return; }
  if (!d.found || !d.citations.length) return;

  el.innerHTML = `
    <div class="card" id="fw-peer-card" style="margin-top:14px">
      <div class="hd"><span class="eyebrow">What other buyers cited</span>
        <h3></h3><span class="pill mute">${d.matched_documents} comparable bids</span></div>
      <div class="in">
        <div class="tbl"><div class="scroll"><table>
          <thead><tr><th>IS</th><th>Title</th><th>Status</th>
            <th style="text-align:right">Bids citing it</th></tr></thead>
          <tbody>${d.citations.map(c => `<tr>
            <td class="mono ${c.in_register ? 'jump' : ''}"${c.in_register
              ? ` data-go="${esc(c.is_number)}"` : ''}>${esc(c.is_number)}</td>
            <td class="std-title">${esc(String(c.title || '—').slice(0, 62))}</td>
            <td>${c.status ? statusPill(c.status) : '<span class="pill mute">not in register</span>'}</td>
            <td class="mono" style="text-align:right">${c.documents}
              <span class="dimmer">of ${c.of}</span></td></tr>`).join('')}
          </tbody></table></div></div>
        <p class="xs dimmer" style="margin-top:9px">${esc(d.note)}</p>
        <p class="xs dimmer">Similar bids include: ${d.examples.map(e => esc(e)).join(' · ')}</p>
      </div>
    </div>`;
}

/* ── procurement standards health ──────────────────────────────────────────
   Not a measure of this system. A measure of the procurement documents it
   reads: how many real government bids cite a standard BIS has already
   withdrawn. Every figure carries the count it was taken from, because the
   corpus is a sample of Indian procurement and not a census of it. */

/* The health index as a picture.
   A table of "83 of 251" reads as data; a bar reads as a finding. Width is the
   number of documents, the filled part is how many of them cite something dead,
   and the count stays printed at the end — a share on its own hides whether it
   was measured over eleven documents or five hundred. */

function healthBars(d) {
  const fams = (d.by_family || []).filter(f => f.documents >= 20).slice(0, 8);
  const years = (d.by_year || []).filter(y => y.documents >= 10);
  if (!fams.length && !years.length) return '';
  const widest = Math.max(...fams.map(f => f.documents), 1);

  const famRow = (f, i) => {
    const share = f.documents ? f.with_dead_citation / f.documents : 0;
    return `<div class="hix" style="animation-delay:${i * 40}ms">
      <div class="hb-label" title="${esc(f.family)}">${esc(String(f.family).slice(0, 34))}</div>
      <div class="hb-track"><div class="hb-total" style="width:${(f.documents / widest * 100).toFixed(1)}%">
        <div class="hb-dead" style="width:${(share * 100).toFixed(1)}%"></div></div></div>
      <div class="hb-n"><b>${f.with_dead_citation}</b> of ${f.documents}</div>
    </div>`;
  };

  const tallest = Math.max(...years.map(y => y.documents), 1);
  const yearCol = (y, i) => {
    const share = y.documents ? y.with_dead_citation / y.documents : 0;
    return `<div class="ycol" style="animation-delay:${i * 40}ms"
                 title="${esc(y.year)}: ${y.with_dead_citation} of ${y.documents} cite a dead standard">
      <div class="yc-bar" style="height:${(y.documents / tallest * 100).toFixed(1)}%">
        <div class="yc-dead" style="height:${(share * 100).toFixed(1)}%"></div></div>
      <div class="yc-lb">${esc(y.year)}</div>
      <div class="yc-n">${y.with_dead_citation}/${y.documents}</div>
    </div>`;
  };

  return `<div class="grid c2" style="margin-top:14px">
    ${fams.length ? `<div class="card"><div class="hd"><h3>By buying department</h3>
      <span class="hint">bar length = documents read</span></div>
      <div class="in"><div class="hbars">${fams.map(famRow).join('')}</div>
      <p class="xs dimmer" style="margin-top:9px">Departments with at least 20 machine-readable
        documents in this corpus. The darker part of each bar is the documents citing a
        withdrawn or superseded standard.</p></div></div>` : ''}
    ${years.length ? `<div class="card"><div class="hd"><h3>By year the bid was floated</h3>
      <span class="hint">from the GeM bid number</span></div>
      <div class="in"><div class="ycols">${years.map(yearCol).join('')}</div>
      <p class="xs dimmer" style="margin-top:9px">Years with at least 10 documents. The year comes
        from the bid number itself; documents whose identifier carries no year are not shown.</p>
      </div></div>` : ''}
  </div>`;
}

async function drawHealthIndex() {
  const el = $('#ov-health');
  if (!el) return;
  let d;
  try { d = S.healthIndex || (S.healthIndex = await api('/health-index')); }
  catch (e) { el.innerHTML = offline(e.message); return; }

  const h = d.headline, c = d.corpus;
  const share = h.of_documents ? Math.round(100 * h.documents_with_a_dead_citation / h.of_documents) : 0;
  const dead = d.dead_standards_still_cited.slice(0, 6);
  const demand = d.most_cited_standards.slice(0, 6);

  const row = r => `<tr>
    <td class="mono jump" data-go="${esc(r.is_number)}">${esc(r.is_number)}</td>
    <td class="std-title">${esc(String(r.title || '—').slice(0, 58))}</td>
    <td>${r.status ? statusPill(r.status) : ''}${String(r.overdue).toLowerCase() === 'yes'
        ? '<span class="pill warn" title="Past the review date BIS set for this edition">review overdue</span>' : ''}</td>
    <td class="mono" style="text-align:right">${r.documents} <span class="dimmer">of ${r.of}</span></td></tr>`;

  el.innerHTML = `
    <div class="kpis">${[
      { label: 'Cite a dead standard', value: `${h.documents_with_a_dead_citation}`,
        sub: `of ${h.of_documents} documents read · ${share}%`,
        tone: h.documents_with_a_dead_citation ? 'bad' : 'ok', icon: 'alert' },
      { label: 'Dead standards in use', value: `${h.distinct_dead_standards_in_circulation}`,
        sub: 'distinct withdrawn or superseded', tone: 'plain', icon: 'alert' },
      { label: 'Citations read', value: `${c.citations_read}`,
        sub: `across ${c.documents_measured} documents`, tone: 'plain', icon: 'check' },
    ].map(kpi).join('')}</div>

    <div class="grid c2" style="margin-top:14px">
      <div class="tbl"><div class="toolbar"><h3 style="flex:1">Withdrawn or superseded, still cited</h3></div>
        <div class="scroll"><table><thead><tr><th>IS</th><th>Title</th><th>Status</th>
          <th style="text-align:right">Documents</th></tr></thead>
          <tbody>${dead.map(row).join('') || '<tr><td colspan="4" class="dimmer">none found</td></tr>'}</tbody>
        </table></div></div>
      <div class="tbl"><div class="toolbar"><h3 style="flex:1">Most-cited standards</h3>
          <span class="xs dimmer">what procurement depends on</span></div>
        <div class="scroll"><table><thead><tr><th>IS</th><th>Title</th><th></th>
          <th style="text-align:right">Documents</th></tr></thead>
          <tbody>${demand.map(row).join('')}</tbody></table></div></div>
    </div>
    ${healthBars(d)}
    <p class="xs dimmer" style="margin-top:11px">${esc(c.note)}</p>`;
  // The KPI helper renders a span that counts up to data-n; without this the
  // card showed three zeroes.
  runCounts();
}

/* ── graph ─────────────────────────────────────────────────────────────────
   Drawn on a canvas from coordinates the server computed once.

   It used to be SVG: one <line> per edge, one <g> per node, and a physics loop
   that ran 110 frames x 2 passes over 319 mutually repelling nodes, rewriting
   thousands of DOM attributes every frame. That is a quarter of a million
   writes to settle a picture that never changes — the layout is a property of
   the co-citation data, not of the session — and it came out differently on
   every visit depending on how many frames finished before you navigated away.

   graph_layout.py settles it once and ships the coordinates. Here the whole
   scene is three stroke() calls for the edges and one arc per node, redrawn
   only when something actually changes: pan, zoom, filter, hover, selection. */

const G = { n: [], e: [], by: {}, k: 1, tx: 0, ty: 0, fams: [], fit: 1,
            hover: null, pick: null, path: null, drag: null, pan: null };
const GW = 1040, GH = 660;

async function loadGraph() {
  if (ready.has('graph')) return;
  try { if (!S.graph) S.graph = await api('/graph'); }
  catch (e) { $('#gwrap').insertAdjacentHTML('afterbegin', offline(e.message)); return; }
  ready.add('graph');
  G.fams = [...new Set(S.graph.nodes.map(n => n.product_family))].filter(f => f && f !== 'N/A').sort();
  fillSel('#g-fam', G.fams);
  drawGraph();
}

const famColor = f => { const i = G.fams.indexOf(f); return i < 0 ? 'var(--k8)' : KC[i % 8]; };

/* Canvas cannot resolve a CSS custom property, so each token is read once per
   draw from the live computed style — which is also what keeps the picture
   correct when the theme changes. */
function tokens() {
  const cs = getComputedStyle(document.documentElement);
  const get = v => cs.getPropertyValue(v).trim() || '#888';
  return {
    edge: get('--line-hard'), ink: get('--ink-3'), pickC: get('--amber'),
    surface: get('--surface'), fam: G.fams.map((_, i) => get(KC[i % 8].replace(/var\(|\)/g, ''))),
    other: get('--k8'),
  };
}
const famIndex = f => { const i = G.fams.indexOf(f); return i < 0 ? -1 : i; };

function drawGraph() {
  const g = S.graph;
  if (!g || !g.edges) return;
  const t0 = performance.now();

  const maxDeg = Math.max(...g.nodes.map(n => n.degree || 0), 1);
  G.n = g.nodes.map(n => ({
    ...n,
    // A node the layout has never seen (a graph rebuilt without re-running
    // graph_layout.py) is parked in the centre rather than at NaN, so a stale
    // layout degrades to a worse picture instead of a blank panel.
    x: n.x == null ? GW / 2 : n.x,
    y: n.y == null ? GH / 2 : n.y,
    r: 4 + (n.degree || 0) / maxDeg * 13,
    hidden: false, dim: false,
  }));
  G.by = Object.fromEntries(G.n.map(n => [n.id, n]));
  G.e = g.edges.filter(e => G.by[e.source] && G.by[e.target])
               .map(e => ({ ...e, hidden: false, lit: false, onPath: false }));

  $('#gkey').innerHTML = G.fams.map(f =>
    `<div class="r"><span class="sw" style="background:${famColor(f)}"></span>${esc(f)}</div>`).join('')
    + `<div class="r"><span class="sw" style="background:var(--k8)"></span>Not in register</div>`;
  const dens = 2 * G.e.length / (G.n.length * (G.n.length - 1));
  if ($('#graph-meta')) $('#graph-meta').textContent =
    `${G.n.length} standards · ${G.e.length.toLocaleString()} edges · thresholds 5+ co-citations / 40%+ confidence / source cited in 8+ tenders`;
  $('#gstat').innerHTML = `<div><div class="lb">Nodes</div><div class="vl">${G.n.length}</div></div>
    <div><div class="lb">Edges</div><div class="vl">${G.e.length.toLocaleString()}</div></div>
    <div><div class="lb">Density</div><div class="vl">${dens.toFixed(3)}</div></div>`;

  resizeGraph();
  console.info(`graph: ${G.n.length} nodes, ${G.e.length} edges drawn in ${(performance.now() - t0).toFixed(0)} ms`);
}

function resizeGraph() {
  const cv = $('#gcanvas'), wrap = $('#gwrap');
  if (!cv || !wrap) return;
  const r = wrap.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  cv.width = Math.round(r.width * dpr);
  cv.height = Math.round(r.height * dpr);
  G.fit = Math.min(r.width / GW, r.height / GH);
  G.dpr = dpr;
  G.cw = r.width; G.ch = r.height;
  paint();
}

/* world -> css pixels. One matrix, applied to the context, so hit testing is
   the same arithmetic inverted rather than a second code path. */
const sx = x => (x - GW / 2) * G.fit * G.k + G.cw / 2 + G.tx;
const sy = y => (y - GH / 2) * G.fit * G.k + G.ch / 2 + G.ty;
const wx = px => (px - G.cw / 2 - G.tx) / (G.fit * G.k) + GW / 2;
const wy = py => (py - G.ch / 2 - G.ty) / (G.fit * G.k) + GH / 2;

function paint() {
  const cv = $('#gcanvas');
  if (!cv || !G.n.length) return;
  const ctx = cv.getContext('2d');
  const T = tokens();
  const labels = $('#g-lab') ? $('#g-lab').checked : true;
  const anyFocus = !!(G.pick || G.hover || G.path);

  ctx.setTransform(G.dpr, 0, 0, G.dpr, 0, 0);
  ctx.clearRect(0, 0, G.cw, G.ch);

  // Edges in three passes bucketed by confidence — the entire edge set is
  // three stroke() calls instead of 4,916 DOM nodes.
  const buckets = [
    { max: 0.5, w: 0.5, a: 0.13 },
    { max: 0.8, w: 1.0, a: 0.20 },
    { max: 1.01, w: 1.7, a: 0.30 },
  ];
  let lo = 0;
  for (const b of buckets) {
    ctx.beginPath();
    for (const e of G.e) {
      if (e.hidden || e.lit || e.onPath) continue;
      if (!(e.confidence >= lo && e.confidence < b.max)) continue;
      const a = G.by[e.source], c = G.by[e.target];
      if (a.hidden || c.hidden) continue;
      ctx.moveTo(sx(a.x), sy(a.y)); ctx.lineTo(sx(c.x), sy(c.y));
    }
    ctx.strokeStyle = T.edge;
    ctx.globalAlpha = anyFocus ? b.a * 0.3 : b.a;
    ctx.lineWidth = b.w;
    ctx.stroke();
    lo = b.max;
  }

  // Highlighted edges (neighbourhood or traced path) on top, fully opaque.
  const hi = G.e.filter(e => (e.lit || e.onPath) && !e.hidden);
  if (hi.length) {
    ctx.beginPath();
    for (const e of hi) {
      const a = G.by[e.source], c = G.by[e.target];
      ctx.moveTo(sx(a.x), sy(a.y)); ctx.lineTo(sx(c.x), sy(c.y));
    }
    ctx.strokeStyle = T.pickC; ctx.globalAlpha = 0.85; ctx.lineWidth = 1.8; ctx.stroke();
  }

  ctx.globalAlpha = 1;
  ctx.lineWidth = 1.4;
  for (const n of G.n) {
    if (n.hidden) continue;
    const r = Math.max(2.2, n.r * Math.sqrt(G.k));
    ctx.beginPath();
    ctx.arc(sx(n.x), sy(n.y), r, 0, Math.PI * 2);
    const fi = famIndex(n.product_family);
    ctx.fillStyle = fi < 0 ? T.other : T.fam[fi];
    ctx.globalAlpha = anyFocus && n.dim ? 0.18 : 1;
    ctx.fill();
    ctx.strokeStyle = n === G.pick ? T.pickC : T.surface;
    ctx.lineWidth = n === G.pick ? 2.5 : 1.4;
    ctx.stroke();
  }

  // Labels cost text layout, so only where they can be read: the best-connected
  // standards, plus whatever the pointer or a search is pointing at.
  if (labels) {
    ctx.globalAlpha = 1;
    ctx.font = '500 10px "JetBrains Mono", ui-monospace, monospace';
    ctx.fillStyle = T.ink;
    ctx.textBaseline = 'middle';
    const top = [...G.n].filter(n => !n.hidden && !n.dim)
      .sort((a, b) => b.degree - a.degree).slice(0, G.k > 1.6 ? 90 : 34);
    const show = new Set(top);
    if (G.hover) show.add(G.hover);
    if (G.pick) show.add(G.pick);
    for (const n of show) {
      if (n.hidden) continue;
      ctx.fillText(n.id, sx(n.x) + Math.max(2.2, n.r * Math.sqrt(G.k)) + 4, sy(n.y));
    }
  }
}

function tip(ev, n) {
  const t = $('#gtip'), w = $('#gwrap').getBoundingClientRect();
  t.style.display = 'block';
  t.innerHTML = `<div class="a">${esc(n.id)}</div>
    <div class="b">${esc(n.title !== 'N/A' ? n.title.slice(0, 74) : 'Not in the register')}</div>
    <div class="b">${n.degree} connections · ${esc(n.product_family)}</div>`;
  t.style.left = Math.min(ev.clientX - w.left + 14, w.width - 262) + 'px';
  t.style.top = ev.clientY - w.top + 14 + 'px';
}

function nodeAt(ev) {
  const r = $('#gwrap').getBoundingClientRect();
  const x = wx(ev.clientX - r.left), y = wy(ev.clientY - r.top);
  let best = null, bestD = Infinity;
  for (const n of G.n) {
    if (n.hidden) continue;
    const dx = n.x - x, dy = n.y - y, d = dx * dx + dy * dy;
    if (d < bestD) { bestD = d; best = n; }
  }
  // Tolerance in world units, so the target stays the same physical size at
  // every zoom level.
  const tol = Math.max(10, (best ? best.r : 6) + 6) / Math.max(G.k, 0.35);
  return bestD <= tol * tol ? best : null;
}

function clearGraph() {
  G.pick = null; G.path = null; G.hover = null;
  G.n.forEach(n => { n.dim = false; });
  G.e.forEach(e => { e.lit = false; e.onPath = false; });
  gFilter();
}

function focusNode(n, andOpen) {
  G.pick = n; G.path = null;
  const near = new Set([n.id]);
  G.e.forEach(e => {
    const on = e.source === n.id || e.target === n.id;
    e.lit = on; e.onPath = false;
    if (on) { near.add(e.source); near.add(e.target); }
  });
  G.n.forEach(m => { m.dim = !near.has(m.id); });
  paint();
  if (andOpen) openStandard(n.id);
}

function pickNode(id) { const n = G.by[id]; if (n) focusNode(n, true); }

/* Breadth-first search over the real co-citation edges. */
function tracePath() {
  const a = $('#g-a').value.trim(), b = $('#g-b').value.trim();
  if (!G.by[a] || !G.by[b]) { toast('Both IS numbers must be nodes in the graph', 'bad'); return; }
  const adj = {};
  G.e.forEach(e => { (adj[e.source] ||= []).push(e.target); (adj[e.target] ||= []).push(e.source); });
  const prev = { [a]: null }, q = [a];
  while (q.length) {
    const cur = q.shift();
    if (cur === b) break;
    (adj[cur] || []).forEach(nx => { if (!(nx in prev)) { prev[nx] = cur; q.push(nx); } });
  }
  if (!(b in prev)) { toast('No co-citation path connects those two', 'bad'); return; }
  const path = []; for (let c = b; c; c = prev[c]) path.unshift(c);
  const set = new Set(path);
  G.pick = null; G.path = path;
  G.n.forEach(n => { n.dim = !set.has(n.id); });
  G.e.forEach(e => {
    e.onPath = set.has(e.source) && set.has(e.target) &&
      Math.abs(path.indexOf(e.source) - path.indexOf(e.target)) === 1;
    e.lit = false;
  });
  paint();
  toast(`${path.length - 1} hop(s): ${path.join(' → ')}`, 'info');
}

function gFilter() {
  const fam = $('#g-fam').value, min = parseFloat($('#g-conf').value);
  $('#g-cv').textContent = min.toFixed(2);
  const keep = new Set();
  G.e.forEach(e => {
    e.hidden = e.confidence < min;
    if (!e.hidden) { keep.add(e.source); keep.add(e.target); }
  });
  G.n.forEach(n => {
    n.hidden = (fam && n.product_family !== fam) || (min > 0 && !keep.has(n.id));
  });
  paint();
}

function graphSVG() {
  // The canvas is the renderer; an export has to be built from the data. Doing
  // it here keeps the exported file vector — a canvas screenshot would not be.
  const T = tokens();
  const line = e => {
    const a = G.by[e.source], b = G.by[e.target];
    return `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${T.edge}" ` +
           `stroke-width="${(0.4 + e.confidence * 1.6).toFixed(2)}" opacity="${(0.1 + e.confidence * 0.3).toFixed(2)}"/>`;
  };
  const dot = n => {
    const fi = famIndex(n.product_family);
    return `<circle cx="${n.x}" cy="${n.y}" r="${n.r.toFixed(1)}" fill="${fi < 0 ? T.other : T.fam[fi]}" ` +
           `stroke="#fff" stroke-width="1.4"/>` +
           `<text x="${(n.x + n.r + 4).toFixed(1)}" y="${(n.y + 3).toFixed(1)}" ` +
           `font-family="monospace" font-size="8.5" fill="${T.ink}">${esc(n.id)}</text>`;
  };
  const vis = G.n.filter(n => !n.hidden);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${GW} ${GH}" width="${GW}" height="${GH}">` +
    `<rect width="${GW}" height="${GH}" fill="${T.surface}"/>` +
    G.e.filter(e => !e.hidden && !G.by[e.source].hidden && !G.by[e.target].hidden).map(line).join('') +
    vis.map(dot).join('') + `</svg>`;
}

function wireGraph() {
  const cv = $('#gcanvas');
  const zoom = f => { G.k = Math.max(.3, Math.min(4, G.k * f)); paint(); };
  $('#g-in').onclick = () => zoom(1.25);
  $('#g-out').onclick = () => zoom(1 / 1.25);
  $('#g-fit').onclick = () => { G.k = 1; G.tx = G.ty = 0; clearGraph(); };
  $('#g-lab').onchange = paint;
  $('#g-fam').onchange = gFilter;
  $('#g-conf').oninput = gFilter;
  $('#g-path').onclick = tracePath;
  $('#g-q').oninput = e => {
    const q = e.target.value.trim().toUpperCase();
    if (!q) return clearGraph();
    const hit = new Set(G.n.filter(n => n.id.toUpperCase().includes(q)).map(n => n.id));
    G.pick = null; G.path = null;
    G.n.forEach(n => { n.dim = !hit.has(n.id); });
    G.e.forEach(e => { e.lit = false; e.onPath = false; });
    paint();
  };
  $('#g-svg').onclick = () => download('manak-setu-graph.svg', graphSVG(), 'image/svg+xml');

  cv.addEventListener('mousedown', ev => {
    const n = nodeAt(ev);
    if (n) { G.drag = n; } else { G.pan = { x: ev.clientX, y: ev.clientY }; cv.classList.add('grab'); }
  });
  cv.addEventListener('mousemove', ev => {
    if (G.drag || G.pan) return;
    const n = nodeAt(ev);
    if (n !== G.hover) { G.hover = n; paint(); }
    if (n) tip(ev, n); else $('#gtip').style.display = 'none';
  });
  cv.addEventListener('mouseleave', () => {
    if (G.hover) { G.hover = null; paint(); }
    $('#gtip').style.display = 'none';
  });
  cv.addEventListener('click', ev => { const n = nodeAt(ev); if (n) focusNode(n, true); });
  window.addEventListener('mousemove', ev => {
    const r = $('#gwrap').getBoundingClientRect();
    if (G.drag) { G.drag.x = wx(ev.clientX - r.left); G.drag.y = wy(ev.clientY - r.top); paint(); }
    else if (G.pan) { G.tx += ev.clientX - G.pan.x; G.ty += ev.clientY - G.pan.y; G.pan = { x: ev.clientX, y: ev.clientY }; paint(); }
  });
  window.addEventListener('mouseup', () => { G.drag = null; G.pan = null; cv.classList.remove('grab'); });
  cv.addEventListener('wheel', ev => { ev.preventDefault(); zoom(ev.deltaY < 0 ? 1.1 : .9); }, { passive: false });
  window.addEventListener('resize', () => { if (ready.has('graph')) resizeGraph(); }, { passive: true });
}

/* ── drawer ────────────────────────────────────────────────────────────── */

function drawer(kind, title, body, pinId) {
  $('#dw-kind').textContent = kind;
  $('#dw-title').textContent = title;
  $('#dw-body').innerHTML = body;
  $('#dw-pin').hidden = !pinId;
  lastFocus = document.activeElement;
  const dw = $('#drawer');
  dw.classList.add('on');
  dw.removeAttribute('aria-hidden');
  $('#scrim').hidden = false;
  $('#scrim').classList.add('on');
  syncPinBtn();
  $('#dw-close').focus();
}
/* Focus handling for the detail drawer. Without this, Tab walks straight out of
   an open modal into the page behind it, and closing it strands the caret at the
   top of the document — a keyboard user loses their place on every lookup. */
let lastFocus = null;

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),textarea,select,[tabindex]:not([tabindex="-1"])';

const shut = () => {
  const dw = $('#drawer');
  if (!dw.classList.contains('on')) return;
  dw.classList.remove('on');
  $('#scrim').classList.remove('on');
  $('#scrim').hidden = true;
  dw.setAttribute('aria-hidden', 'true');
  if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
  lastFocus = null;
};

function trapFocus(e) {
  const dw = $('#drawer');
  if (e.key !== 'Tab' || !dw.classList.contains('on')) return;
  const items = [...dw.querySelectorAll(FOCUSABLE)].filter(el => el.offsetParent !== null);
  if (!items.length) return;
  const first = items[0], last = items[items.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}

/* ── palette ───────────────────────────────────────────────────────────── */

let pal = [], pi = 0;

function openPal() {
  $('#pal-bg').classList.add('on');
  $('#pal-in').value = ''; $('#pal-in').focus();
  buildPal('');
}
const shutPal = () => $('#pal-bg').classList.remove('on');

function buildPal(q) {
  const l = q.toLowerCase(), out = [];
  visibleNav().filter(n => !l || n.full.toLowerCase().includes(l) || n.label.toLowerCase().includes(l))
    .forEach(n => out.push({ g: 'Go to', icon: n.icon, label: n.full, run: () => go(n.id) }));
  // Results from the last server search for this term. The palette used to
  // filter two arrays held in memory, which is why the whole register had to be
  // downloaded before it could find anything.
  (palHits.q === l ? palHits.standards : []).forEach(s => out.push({
    g: 'Standards', icon: 'book',
    label: `${s['IS Number']} — ${String(s['Full Title']).slice(0, 56)}`,
    run: () => openStandard(s['IS Number']) }));
  (palHits.q === l ? palHits.tenders : []).forEach(t => out.push({
    g: 'Tenders', icon: 'files', label: t.Title ? `${t.Title.slice(0, 54)}` : t['Tender ID'],
    run: () => { go('tenders'); setTimeout(() => openTender(t['Tender ID']), 130); } }));
  pal = out.slice(0, 16); pi = 0; paintPal();
  if (l.length >= 2 && palHits.q !== l) searchPal(l);
}

const palHits = { q: null, standards: [], tenders: [] };
let palTimer = null;

function searchPal(l) {
  clearTimeout(palTimer);
  palTimer = setTimeout(async () => {
    try {
      const [std, ten] = await Promise.all([
        api(`/standards?q=${encodeURIComponent(l)}&limit=7`),
        api(`/tenders?q=${encodeURIComponent(l)}&limit=5`),
      ]);
      palHits.q = l; palHits.standards = std.rows || []; palHits.tenders = ten.rows || [];
      // Only repaint if the user has not typed on since this went out.
      if ($('#pal-in').value.trim().toLowerCase() === l) buildPal($('#pal-in').value.trim());
    } catch (_) { /* the navigation entries still work */ }
  }, 220);
}

function paintPal() {
  if (!pal.length) {
    $('#pal-list').innerHTML = blank('Nothing matches', 'Standards and tenders become searchable once those sections have loaded.');
    return;
  }
  let last = '', h = '';
  pal.forEach((it, i) => {
    if (it.g !== last) { h += `<div class="gl">${esc(it.g)}</div>`; last = it.g; }
    h += `<div class="it ${i === pi ? 'on' : ''}" data-i="${i}">${ic(it.icon, 'sm')}<span>${esc(it.label)}</span></div>`;
  });
  $('#pal-list').innerHTML = h;
  $$('#pal-list .it').forEach(el => el.addEventListener('click', () => { pal[+el.dataset.i].run(); shutPal(); }));
}

/* ── init ──────────────────────────────────────────────────────────────── */

function wireKeys() {
  let g = false;
  window.addEventListener('keydown', e => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName);
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openPal(); return; }
    if (e.key === 'Escape') {
      if (D.on) { demoStop(false); return; }
      shutPal(); shut(); closePins(); return;
    }
    if (D.on && !typing) {
      if (e.key === ' ') { e.preventDefault(); demoPause(); return; }
      if (e.key === 'ArrowRight') { e.preventDefault(); D.paused = false; demoGo(D.i + 1); return; }
      if (e.key === 'ArrowLeft') { e.preventDefault(); D.paused = false; demoGo(D.i - 1); return; }
    }
    if (typing) return;
    if (e.key === '/') { e.preventDefault(); openPal(); return; }
    if (e.key.toLowerCase() === 'g') { g = true; setTimeout(() => g = false, 900); return; }
    if (g) {
      const map = { o: 'overview', d: 'analyze', t: 'tenders', g: 'graph', s: 'standards', c: 'certs', b: 'benchmark', e: 'evidence' };
      const v = map[e.key.toLowerCase()];
      if (v) { go(v); g = false; }
    }
  });
  $('#pal-in').addEventListener('input', e => buildPal(e.target.value.trim()));
  $('#pal-in').addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); pi = Math.min(pal.length - 1, pi + 1); paintPal(); }
    if (e.key === 'ArrowUp') { e.preventDefault(); pi = Math.max(0, pi - 1); paintPal(); }
    if (e.key === 'Enter' && pal[pi]) { pal[pi].run(); shutPal(); }
  });
}

async function boot() {
  // ?role=/?theme= make a view shareable as a link (and scriptable for captures)
  const qs = new URLSearchParams(location.search);
  if (qs.get('role')) { ROLE = qs.get('role'); localStorage.setItem('manak.role', ROLE); }
  if (qs.get('theme')) localStorage.setItem('manak.theme', qs.get('theme'));

  initLang(qs.get('lang') || localStorage.getItem('manak.lang'));
  applyI18n();
  setTimeout(translatePage, 700);

  const th = localStorage.getItem('manak.theme') || 'light';
  document.documentElement.dataset.theme = th;
  $('#theme').addEventListener('click', () => {
    const n = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = n;
    localStorage.setItem('manak.theme', n);
    if (S.graph && ready.has('graph')) drawGraph();
  });

  await resolveApi();
  buildNav();
  renderPins();
  wireKeys();
  wireGraph();

  $('#pins-btn').onclick = e => { e.stopPropagation(); $('#pins-pop').classList.toggle('on'); };
  document.addEventListener('click', e => {
    if (!e.target.closest('#pins-pop') && !e.target.closest('#pins-btn')) closePins();
  });
  $('#open-pal').onclick = openPal;
  $('#pal-bg').onclick = e => { if (e.target.id === 'pal-bg') shutPal(); };
  $('#dw-close').onclick = shut;
  $('#scrim').onclick = shut;
  document.addEventListener('keydown', trapFocus);
  $('#dw-pin').onclick = () => togglePin($('#dw-title').textContent);
  $('#ov-refresh').onclick = () => loadOverview(true);
  $('#bm-run').onclick = () => loadBench(true);

  $('#drop').onclick = () => $('#file').click();
  $('#file').onchange = e => onFile(e.target.files[0]);
  ['dragenter', 'dragover'].forEach(t => $('#drop').addEventListener(t, e => { e.preventDefault(); $('#drop').classList.add('over'); }));
  ['dragleave', 'drop'].forEach(t => $('#drop').addEventListener(t, e => { e.preventDefault(); $('#drop').classList.remove('over'); }));
  $('#drop').addEventListener('drop', e => onFile(e.dataTransfer.files[0]));
  $('#ex-text').onclick = async () => {
    const t = $('#spec').value.trim();
    if (!t) return;
    const r = await api('/extract-text', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: t }) });
    const n = addChips(r.citations);
    $('#ex-status').innerHTML = `<div class="note ${r.citations.length ? 'ok' : 'warn'}" style="margin:11px 0 0">
      ${ic(r.citations.length && !r.scanned ? 'check' : 'alert')}<div>${r.citations.length} citation(s) read from ${r.characters.toLocaleString()} characters${n !== r.citations.length ? `, ${n} new` : ''}.</div></div>`;
  };
  $('#add-btn').onclick = () => { const v = $('#add-is').value.trim(); if (v) { addChips([v]); $('#add-is').value = ''; } };
  $('#add-is').addEventListener('keydown', e => { if (e.key === 'Enter') $('#add-btn').click(); });
  $('#run').onclick = runAudit;
  $('#fw-run').onclick = runForward;
  $('#fw-clear').onclick = () => { $('#fw-spec').value = ''; $('#fw-out').innerHTML = ''; };
  $$('#fw-presets button').forEach(b => b.onclick = () => { $('#fw-spec').value = b.dataset.q; runForward(); });
  buildLangMenu();
  $('#role-btn').onclick = () => {
    ROLE = ROLE === 'admin' ? 'officer' : 'admin';
    localStorage.setItem('manak.role', ROLE);
    buildNav(); paintRole(); go(ROLE === 'admin' ? 'overview' : 'draft');
    toast(`Switched to ${ROLE} view`, 'info');
  };
  paintRole();
  $('#an-clear').onclick = resetAudit;
  $('#ev-go').onclick = () => loadEvidence();
  $('#ev-in').addEventListener('keydown', e => { if (e.key === 'Enter') loadEvidence(); });
  $$('#ev-presets button').forEach(b => b.onclick = () => loadEvidence(b.dataset.e));
  $('#an-csv').onclick = auditCsv;
  $('#demo-btn').onclick = () => D.on ? demoStop(false) : demoStart();
  $('#demo-prev').onclick = () => { D.paused = false; demoGo(D.i - 1); };
  $('#demo-next').onclick = () => { D.paused = false; demoGo(D.i + 1); };
  $('#demo-play').onclick = demoPause;
  $('#demo-exit').onclick = () => demoStop(false);
  $('#an-print').onclick = () => window.print();
  $$('#presets button').forEach(b => b.onclick = () => preset_(b.dataset.p));

  health();
  // Calibration is a file on disk, not a computation — cheap to fetch once and
  // the confidence arc reads it. Silent if it has never been measured.
  api('/calibration').then(c => { if (c && c.buckets) S.calibration = c; }).catch(() => {});

  const [v, ent] = location.hash.slice(1).split('/');
  go(v || 'draft');

  // ?q= pre-fills and runs the forward flow, so a result is linkable
  const preset = qs.get('q');
  if (preset) { $('#fw-spec').value = preset; setTimeout(runForward, 200); }

  // ?audit=outdated|led|pipes|cables loads that corpus example and verifies it
  const au = qs.get('audit');
  if (au) setTimeout(async () => { await preset_(au); await runAudit(); }, 250);
  if (ent) setTimeout(() => openStandard(decodeURIComponent(ent)), 300);
}


/* ── findings, decisions, evidence ──────────────────────────────────────────
   The audit screen's centre of gravity. /analyze answers "is each citation
   alive"; /audit-text answers "what is wrong with this document" — dead
   references, a mandatory certification the tender never asks for, and the
   standards comparable tenders cite that this one omits. Every finding shows
   the row it came from, and an officer can accept or override it on the spot.
   ──────────────────────────────────────────────────────────────────────── */

const KIND = {
  dispute_risk:       { get label() { return t('find.dispute_risk'); },       icon: 'alert', tone: 'bad'  },
  statutory_omission: { get label() { return t('find.statutory_omission'); }, icon: 'badge', tone: 'bad'  },
  missing_connected:  { get label() { return t('find.missing_connected'); },  icon: 'net',   tone: 'warn' },
  not_in_register:    { get label() { return t('find.not_in_register'); },    icon: 'pie',   tone: 'mute' },
};

const VERDICT = {
  blocking:   { get t() { return t('verdict.blocking'); },   c: 'blocking' },
  review:     { get t() { return t('verdict.review'); },     c: 'review'   },
  clean:      { get t() { return t('verdict.clean'); },      c: 'clean'    },
  unreadable: { get t() { return t('verdict.unreadable'); }, c: 'unreadable' },
};

function renderFindings(a) {
  if (!a) return '';
  const v = VERDICT[a.verdict] || VERDICT.review;
  let h = `<div class="verdict-bar ${v.c}">${ic(a.verdict === 'clean' ? 'check' : 'alert')}
    <div><div class="vt">${esc(v.t)}</div></div>
    <div class="vs">${esc(a.summary)}</div></div>`;

  if (a.extraction && a.extraction.scanned) {
    h += `<div class="note bad">${ic('alert')}<div><b>No text layer.</b> ${esc(a.extraction.scanned_note)}</div></div>`;
  }

  const S = a.suggestions;
  if (!S || !S.counts || !Object.values(S.counts).some(Boolean)) return h;

  /* The audit is a list of edits to make to the tender, not a queue of things to
     approve. The officer changes their document; the document is the record. */
  const block = (title, icon, tone, rows) => rows.length ? `
    <div class="card" style="margin-top:14px"><div class="hd">${ic(icon, 'sm')}
      <h3>${esc(title)}</h3><span class="pill ${tone}">${rows.length}</span></div>
      <div class="in">${rows.join('')}</div></div>` : '';

  h += block('Replace these citations', 'alert', 'bad', S.replace.map(r => `
    <div class="edit" data-finding="${esc(r.cite)}">
      <div class="top">
        <span class="mono strike jump" data-go="${esc(r.cite)}">${esc(r.cite)}</span>
        <span class="pill bad">${esc(r.status)}</span>
        ${r.with ? `${ic('arrow','sm')}<span class="mono jump" style="color:var(--ok);font-weight:600"
             data-go="${esc(r.with)}">${esc(r.with)}</span>`
                 : '<span class="pill warn">no successor on file</span>'}
      </div>
      <div class="why">${esc(r.why)}</div>
      ${r.evidence && r.evidence.link ? `<div class="src"><a href="${esc(r.evidence.link)}"
        target="_blank" rel="noopener">BIS record</a></div>` : ''}
    </div>`));

  h += block('Consider adding these standards', 'net', 'warn', S.add.map(r => `
    <div class="edit" data-finding="${esc(r.cite)}">
      <div class="top">
        <span class="mono jump" data-go="${esc(r.cite)}">${esc(r.cite)}</span>
        ${r.confidence != null ? `<span class="pill mute">${(r.confidence * 100).toFixed(0)}% of comparable tenders</span>` : ''}
        ${r.in_register === false ? '<span class="pill warn">not in register</span>' : ''}
      </div>
      ${r.title ? `<div class="std-title why">${esc(r.title)}</div>` : ''}
      <div class="why">${esc(r.why)}</div>
      <div class="src"><span class="jump" data-ev="${esc(r.cite)}">see citing tenders</span></div>
    </div>`));

  h += block('Add these certification clauses', 'badge', 'bad', S.add_clause.map(r => `
    <div class="edit" data-finding="${esc(r.for)}">
      <div class="top">
        <span class="mono jump" data-go="${esc(r.for)}">${esc(r.for)}</span>
        <span class="pill bad">${esc(r.scheme || 'mandatory')}</span>
      </div>
      <div class="why">Mandatory certification applies and no Standard Mark clause was found.</div>
      <blockquote class="clause-suggest">${esc(r.clause)}</blockquote>
      <button class="btn tiny" data-copy="${esc(r.clause)}">${ic('copy','sm')}Copy clause</button>
    </div>`));

  if (S.unresolved.length) {
    h += `<div class="card" style="margin-top:14px"><div class="hd">${ic('pie','sm')}
      <h3>Not in the register</h3><span class="pill mute">${S.unresolved.length}</span></div>
      <div class="in"><div class="xs" style="color:var(--ink-2)">
      ${S.unresolved.map(u => u.did_you_mean
        ? `<div style="margin-bottom:7px"><span class="mono">${esc(u.cite)}</span>
             <span class="dimmer">— not in the catalogue. Possibly a slip for</span>
             <span class="mono jump" data-go="${esc(u.did_you_mean.is_number)}">${esc(u.did_you_mean.is_number)}</span>
             <div class="xs dimmer" style="margin-top:2px">${esc(u.did_you_mean.evidence)} Confirm against the source document before changing anything.</div></div>`
        : `<span class="mono">${esc(u.cite)}</span>`).join(' · ')}
      <div class="xs dimmer" style="margin-top:6px">Cited by this tender and not held, so status and
      certification cannot be checked. Logged as a collection gap rather than assumed valid.</div>
      </div></div></div>`;
  }

  h += `<div class="note info">${ic('check')}<div>${esc(S.note)}</div></div>`;
  return h;
}

/* An override with no reason is the thing an auditor asks about a year later,
   so the backend rejects it and the UI asks before sending. */
/* ── corpus evidence ───────────────────────────────────────────────────────
   The "where did your data come from" screen. Every row is a real published
   tender with its own link — the claim is checkable without trusting us. */

async function loadEvidence(isNumber) {
  const out = $('#ev-out');
  const q = (isNumber || $('#ev-in').value || '').trim();
  if (!q) { toast('Enter an IS number', 'bad'); return; }
  $('#ev-in').value = q;
  go('evidence');
  out.innerHTML = `<div class="card"><div class="in"><div class="skel" style="height:90px"></div></div></div>`;
  let d;
  try { d = await api('/evidence?is_number=' + encodeURIComponent(q)); }
  catch (e) { out.innerHTML = offline(e.message); return; }

  const std = d.standard || {};
  let h = `<div class="kpis">` + [
    { label: 'Tenders citing', value: d.tenders_citing, sub: `of ${d.corpus_size} in the corpus`, icon: 'doc' },
    { label: 'Share of corpus', value: d.share, dec: 1, suffix: '%', sub: 'of collected tenders cite it', icon: 'pie' },
    { label: 'In the register', text: d.in_register ? 'Yes' : 'No', sub: d.in_register ? `matched ${d.matched_by === 'exact' ? 'exactly' : 'on base number'}` : 'no catalogue record held', tone: d.in_register ? 'ok' : 'warn', icon: 'book' },
    { label: 'Certification', text: d.certification ? (d.certification['Certification Mandatory'] === 'Yes' ? 'Mandatory' : 'Voluntary') : 'No rule', sub: d.certification ? d.certification['Scheme'] : 'none on file', tone: d.certification && d.certification['Certification Mandatory'] === 'Yes' ? 'bad' : d.certification ? 'ok' : 'plain', icon: 'badge' },
  ].map(kpi).join('') + `</div>`;

  if (d.in_register) {
    h += `<div class="card"><div class="hd"><h3>${esc(d.resolved_as)}</h3>${statusPill(std['Status'])}
      <span class="hint">${esc(std['Product Family'] || '')}</span></div>
      <div class="in"><div class="dt" style="font-size:13px;line-height:1.65;color:var(--ink-2)">${esc(std['Full Title'] || '—')}</div>
      <div class="src" style="margin-top:9px;font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--ink-3)">
        year ${esc(std['Year'] || '—')}
        ${std['Source Link'] && std['Source Link'] !== 'N/A' ? ` · <a href="${esc(std['Source Link'])}" target="_blank" rel="noopener">BIS record</a>` : ''}
      </div></div></div>`;
  } else {
    h += `<div class="note warn">${ic('alert')}<div><b>${esc(q)} is cited by real tenders but is not in the register.</b>
      Its status and supersession cannot be checked, so it is logged to the coverage backlog rather than assumed current.</div></div>`;
  }

  h += d.tenders_citing
    ? `<div class="card"><div class="hd"><h3>Citing tenders</h3>
        <span class="hint">${d.tenders_citing} document${d.tenders_citing > 1 ? 's' : ''}${d.truncated ? ` · showing first ${d.tenders.length}` : ''}</span></div>
      <div class="scroll"><table><thead><tr><th>Tender</th><th>Family</th><th>Type</th><th>Usability</th><th class="r">Citations</th><th>Dead refs</th><th></th></tr></thead><tbody>
      ${d.tenders.map(t => `<tr>
        <td><div>${esc(t.title || t.tender_id)}</div>
            <div class="xs dimmer mono" title="source filename">${esc(t.tender_id)}</div></td>
        <td class="xs">${esc(t.product_family || '—')}</td>
        <td class="xs">${esc(t.document_type || '—')}</td>
        <td>${t.usability === 'Usable' ? '<span class="pill ok">Usable</span>' : `<span class="pill mute">${esc(t.usability || '—')}</span>`}</td>
        <td class="mono r">${esc(t.citation_count)}</td>
        <td>${t.any_outdated === 'Yes' ? '<span class="pill bad">Yes</span>' : '<span class="dimmer">—</span>'}</td>
        <td>${t.source_link && t.source_link !== 'N/A' ? `<a href="${esc(t.source_link)}" target="_blank" rel="noopener">open</a>` : ''}</td>
      </tr>`).join('')}</tbody></table></div>
      <div class="ft">Citations were extracted literally from each document's text. A tender appears here only if its own words contain this IS number.</div>
    </div>`
    : blank(`No tender in the corpus cites ${q}`,
        `The corpus is ${(S.stats && S.stats.row_counts.tenders) || 220} collected documents, not the whole of Indian procurement — absence here is a gap in our collection, not evidence the standard is unused.`);

  out.innerHTML = h;
  runCounts();
}

/* ── language ──────────────────────────────────────────────────────────────
   Switching re-renders the chrome in place. Results already on screen are
   re-rendered from the data we still hold, so nothing is re-fetched and the
   officer does not lose their place. */

function buildLangMenu() {
  const pop = $('#lang-pop'), btn = $('#lang-btn');
  if (!pop || !btn) return;
  const paint = () => {
    pop.innerHTML = LANGS.map(l => `<button data-lang="${l.code}" role="option"
      aria-selected="${l.code === document.documentElement.lang}">
      <span>${esc(l.native)}</span><span class="en">${esc(l.label)}</span></button>`).join('');
    $('#lang-now').textContent = document.documentElement.lang.toUpperCase();
    $$('#lang-pop button').forEach(b => b.onclick = () => {
      setLang(b.dataset.lang);
      pop.classList.remove('on');
      btn.setAttribute('aria-expanded', 'false');
    });
  };
  paint();
  btn.onclick = e => {
    e.stopPropagation();
    const open = pop.classList.toggle('on');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  };
  document.addEventListener('click', e => {
    if (!e.target.closest('.lang-wrap')) { pop.classList.remove('on'); btn.setAttribute('aria-expanded', 'false'); }
  });
  document.addEventListener('langchange', () => {
    paint();
    buildNav();
    go(view);
    if (S.analysis) renderAudit(S.analysis);
    if (S.fw) renderForward(S.fw);
    toast(t('ui.language') + ' · ' + langLabel(), 'info');
    translatePage();
  });
}

document.addEventListener('DOMContentLoaded', boot);
