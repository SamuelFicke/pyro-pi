"use strict";

const $ = (id) => document.getElementById(id);
const body = document.body;
let busy = false;        // a command is in flight
let offline = false;

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

async function command(path, options) {
  if (busy) return;
  busy = true;
  setButtonsEnabled(false);
  try {
    render(await api(path, options));
  } catch (e) {
    markOffline();
  } finally {
    busy = false;
  }
}

function setButtonsEnabled(on) {
  for (const b of document.querySelectorAll(".btn, .step")) b.disabled = !on;
}

function markOffline() {
  offline = true;
  body.classList.remove("on", "off", "loading");
  $("state").textContent = "—";
  $("offline-note").hidden = false;
  $("timer").hidden = true;
  setButtonsEnabled(false);
}

function render(st) {
  offline = false;
  body.classList.remove("loading");
  $("offline-note").hidden = true;

  body.classList.toggle("on", st.on);
  body.classList.toggle("off", !st.on);
  $("state").textContent = st.on ? "ON" : "OFF";

  // Keep the clock fresh from the server's own time.
  if (st.now) $("clock").textContent = st.now;

  const timer = $("timer");
  if (st.on) {
    timer.hidden = false;
    $("off-time").textContent = st.off_at || "—";
    $("ceiling-hint").textContent = st.ceiling_at ? ("Latest allowed: " + st.ceiling_at) : "";
  } else {
    timer.hidden = true;
  }

  if (!busy) {
    setButtonsEnabled(true);
    $("btn-on").classList.toggle("is-current", st.on);
    $("btn-off").classList.toggle("is-current", !st.on);
  }
}

async function poll() {
  if (busy) return;
  try {
    render(await api("/api/status"));
  } catch (e) {
    markOffline();
  }
}

$("btn-on").addEventListener("click", () => command("/api/on", { method: "POST" }));
$("btn-off").addEventListener("click", () => command("/api/off", { method: "POST" }));
$("plus").addEventListener("click", () => adjust(1));
$("minus").addEventListener("click", () => adjust(-1));

function adjust(hours) {
  command("/api/adjust", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hours }),
  });
}

poll();
setInterval(poll, 1000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });
