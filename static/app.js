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

/* ---------- wheel (iOS-style scrolling off-time picker) ---------- */
const wheel = $("wheel-list");
let wheelOpts = [];        // [{epoch, label}]
let wheelCeiling = 0;      // ceiling_epoch the current options were built for
let scrolling = false;     // user is dragging the wheel
let programmatic = false;  // we are moving the wheel in code
let settleTimer = null;
let suppressSyncUntil = 0; // ignore server echo right after a user pick

const fmtClock = (epoch) =>
  new Date(epoch * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

function buildWheel(st) {
  const startMin = Math.floor(st.now_epoch / 60) + 1;  // next whole minute
  const endMin = Math.floor(st.ceiling_epoch / 60);    // at the ceiling
  wheelOpts = [];
  for (let m = startMin; m <= endMin; m++) wheelOpts.push({ epoch: m * 60, label: fmtClock(m * 60) });
  if (!wheelOpts.length) wheelOpts.push({ epoch: st.ceiling_epoch, label: fmtClock(st.ceiling_epoch) });
  wheel.innerHTML = wheelOpts.map((o, i) => `<li class="wheel-item" data-i="${i}">${o.label}</li>`).join("");
  wheelCeiling = st.ceiling_epoch;
}

function nearestIndex(epoch) {
  let best = 0, bd = Infinity;
  for (let i = 0; i < wheelOpts.length; i++) {
    const d = Math.abs(wheelOpts[i].epoch - epoch);
    if (d < bd) { bd = d; best = i; }
  }
  return best;
}

function markSelected(i) {
  for (const el of wheel.children) el.classList.toggle("sel", +el.dataset.i === i);
}

function scrollToIndex(i, smooth) {
  programmatic = true;
  wheel.scrollTo({ top: i * ITEM_H, behavior: smooth ? "smooth" : "auto" });
  markSelected(i);
  clearTimeout(scrollToIndex._t);
  scrollToIndex._t = setTimeout(() => { programmatic = false; }, smooth ? 450 : 140);
}

function currentIndex() {
  return Math.max(0, Math.min(wheelOpts.length - 1, Math.round(wheel.scrollTop / ITEM_H)));
}

wheel.addEventListener("scroll", () => {
  markSelected(currentIndex());
  if (programmatic) return;          // ignore our own scrollTo
  scrolling = true;
  clearTimeout(settleTimer);
  settleTimer = setTimeout(() => {
    scrolling = false;
    const idx = currentIndex();
    markSelected(idx);
    suppressSyncUntil = Date.now() + 1500;
    command("/api/off_time", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ at_epoch: wheelOpts[idx].epoch }),
    });
  }, 200);
});

function syncWheel(st) {
  // Rebuild when a new on-session starts, or when stale leading options pile up.
  const stale = wheelOpts.length && wheelOpts[0].epoch < st.now_epoch - 90;
  if (wheelCeiling !== st.ceiling_epoch || !wheelOpts.length || (stale && !scrolling)) {
    const keep = wheelOpts.length ? wheelOpts[nearestIndex(st.off_epoch)].epoch : st.off_epoch;
    buildWheel(st);
    scrollToIndex(nearestIndex(keep), false);
    return;
  }
  if (scrolling || Date.now() < suppressSyncUntil) return;  // don't fight the user
  const i = nearestIndex(st.off_epoch);
  if (i !== currentIndex()) scrollToIndex(i, false);
  else markSelected(i);
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
    syncWheel(st);
    $("ceiling-hint").textContent = st.ceiling_epoch ? "Latest allowed: " + fmtClock(st.ceiling_epoch) : "";
  } else {
    $("timer").hidden = true;
    wheelOpts = [];
    wheelCeiling = 0;
  }

  if (!busy) {
    $("btn-on").disabled = $("btn-off").disabled = false;
    $("btn-on").classList.toggle("is-current", st.on);
    $("btn-off").classList.toggle("is-current", !st.on);
  }
}

async function poll() {
  if (busy || scrolling) return;
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
