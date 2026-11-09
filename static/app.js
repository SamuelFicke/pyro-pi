"use strict";

const $ = (id) => document.getElementById(id);
const body = document.body;
let busy = false;        // a command is in flight
const ITEM_H = 44;       // must match --item-h in style.css

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

async function command(path, options) {
  if (busy) return;
  busy = true;
  $("btn-on").disabled = $("btn-off").disabled = true;
  try {
    render(await api(path, options));
  } catch (e) {
    markOffline();
  } finally {
    busy = false;
  }
}

function markOffline() {
  body.classList.remove("on", "off", "loading");
  $("state").textContent = "—";
  $("offline-note").hidden = false;
  $("timer").hidden = true;
  $("btn-on").disabled = $("btn-off").disabled = true;
}

/* ---------- a single scrollable wheel column ---------- */
function makeWheel(listEl, onSettle) {
  let opts = [];
  let programmatic = false;
  let scrolling = false;
  let settleT = null;

  const clampIdx = (i) => Math.max(0, Math.min(opts.length - 1, i));
  const currentIndex = () => clampIdx(Math.round(listEl.scrollTop / ITEM_H));
  const mark = (i) => { for (const el of listEl.children) el.classList.toggle("sel", +el.dataset.i === i); };

  function setIndex(i, smooth) {
    i = clampIdx(i);
    programmatic = true;
    listEl.scrollTo({ top: i * ITEM_H, behavior: smooth ? "smooth" : "auto" });
    mark(i);
    clearTimeout(setIndex._t);
    setIndex._t = setTimeout(() => { programmatic = false; }, smooth ? 450 : 140);
  }

  function build(items, selIndex) {
    opts = items;
    listEl.innerHTML = items.map((o, i) => `<li class="wheel-item" data-i="${i}">${o.label}</li>`).join("");
    setIndex(selIndex, false);
  }

  listEl.addEventListener("scroll", () => {
    mark(currentIndex());
    if (programmatic) return;
    scrolling = true;
    clearTimeout(settleT);
    settleT = setTimeout(() => {
      scrolling = false;
      onSettle(currentIndex());
    }, 200);
  });

  return {
    build, setIndex, currentIndex, mark,
    value: () => opts[currentIndex()],
    length: () => opts.length,
    isScrolling: () => scrolling,
  };
}

/* ---------- hours + minutes duration picker ---------- */
let sessionCeiling = 0;    // ceiling_epoch the wheels were built for
let builtRemMin = -1;      // remaining minutes the wheels were built for
let suppressSyncUntil = 0;
let hoursOpts = [];

const pad2 = (n) => (n < 10 ? "0" + n : "" + n);

function remainingMin(st) {
  return Math.max(1, Math.floor((st.ceiling_epoch - st.now_epoch) / 60));
}
function maxHours(remMin) { return Math.floor(remMin / 60); }

function minuteOptions(h, remMin) {
  const maxH = maxHours(remMin);
  const hi = (h === maxH) ? (remMin - maxH * 60) : 59;   // cap at the ceiling
  const lo = (h === 0) ? 1 : 0;                          // at least 1 minute total
  const out = [];
  for (let m = lo; m <= Math.max(lo, hi); m++) out.push({ value: m, label: pad2(m) });
  return out;
}
function nearestIdx(opts, value) {
  let best = 0, bd = Infinity;
  for (let i = 0; i < opts.length; i++) {
    const d = Math.abs(opts[i].value - value);
    if (d < bd) { bd = d; best = i; }
  }
  return best;
}

const hoursWheel = makeWheel($("list-h"), onHourSettle);
const minutesWheel = makeWheel($("list-m"), () => postDuration());

function rebuildMinutes(h, keepMinute, selectNearest) {
  const remMin = builtRemMin;
  const opts = minuteOptions(h, remMin);
  minutesWheel.build(opts, selectNearest ? nearestIdx(opts, keepMinute) : 0);
  return opts;
}

function onHourSettle() {
  const h = hoursWheel.value().value;
  const curM = minutesWheel.value() ? minutesWheel.value().value : 0;
  rebuildMinutes(h, curM, true);
  postDuration();
}

function postDuration() {
  const h = hoursWheel.value() ? hoursWheel.value().value : 0;
  const m = minutesWheel.value() ? minutesWheel.value().value : 0;
  const total = Math.max(1, h * 60 + m);
  suppressSyncUntil = Date.now() + 1500;
  command("/api/off_time", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ in_minutes: total }),
  });
}

function buildPicker(st, remMin) {
  const maxH = maxHours(remMin);
  hoursOpts = [];
  for (let h = 0; h <= maxH; h++) hoursOpts.push({ value: h, label: String(h) });

  const offMin = Math.min(remMin, Math.max(1, Math.round((st.off_epoch - st.now_epoch) / 60)));
  const selH = Math.min(Math.floor(offMin / 60), maxH);
  const selM = offMin - selH * 60;

  sessionCeiling = st.ceiling_epoch;
  builtRemMin = remMin;
  hoursWheel.build(hoursOpts, nearestIdx(hoursOpts, selH));
  const mOpts = minuteOptions(selH, remMin);
  minutesWheel.build(mOpts, nearestIdx(mOpts, selM));
}

function syncPicker(st) {
  const remMin = remainingMin(st);
  const picking = hoursWheel.isScrolling() || minutesWheel.isScrolling();

  const newSession = st.ceiling_epoch !== sessionCeiling || builtRemMin < 0;
  const stale = !newSession && remMin !== builtRemMin;
  if (newSession || (stale && !picking && Date.now() > suppressSyncUntil)) {
    buildPicker(st, remMin);
    return;
  }
  if (picking || Date.now() < suppressSyncUntil) return;

  // Reflect an off-time changed elsewhere (ac.local, another phone).
  const offMin = Math.min(remMin, Math.max(1, Math.round((st.off_epoch - st.now_epoch) / 60)));
  const wantH = Math.min(Math.floor(offMin / 60), maxHours(remMin));
  const wantM = offMin - wantH * 60;
  const curH = hoursWheel.value() ? hoursWheel.value().value : -1;
  const curM = minutesWheel.value() ? minutesWheel.value().value : -1;
  if (wantH !== curH) {
    hoursWheel.setIndex(nearestIdx(hoursOpts, wantH), false);
    rebuildMinutes(wantH, wantM, true);
  } else if (wantM !== curM) {
    const mOpts = minuteOptions(wantH, remMin);
    minutesWheel.setIndex(nearestIdx(mOpts, wantM), false);
  }
}

/* ---------- render ---------- */
function render(st) {
  body.classList.remove("loading");
  $("offline-note").hidden = true;

  body.classList.toggle("on", st.on);
  body.classList.toggle("off", !st.on);
  $("state").textContent = st.on ? "ON" : "OFF";
  if (st.now) $("clock").textContent = st.now;

  if (st.on) {
    $("timer").hidden = false;
    syncPicker(st);
    $("timer-off").textContent = st.off_at ? "Turns off at " + st.off_at : "";
    $("ceiling-hint").textContent = st.ceiling_at ? "Latest allowed: " + st.ceiling_at : "";
  } else {
    $("timer").hidden = true;
    sessionCeiling = 0;
    builtRemMin = -1;
  }

  if (!busy) {
    $("btn-on").disabled = $("btn-off").disabled = false;
    $("btn-on").classList.toggle("is-current", st.on);
    $("btn-off").classList.toggle("is-current", !st.on);
  }
}

async function poll() {
  if (busy || hoursWheel.isScrolling() || minutesWheel.isScrolling()) return;
  try {
    render(await api("/api/status"));
  } catch (e) {
    markOffline();
  }
}

$("btn-on").addEventListener("click", () => command("/api/on", { method: "POST" }));
$("btn-off").addEventListener("click", () => command("/api/off", { method: "POST" }));

poll();
setInterval(poll, 1000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
