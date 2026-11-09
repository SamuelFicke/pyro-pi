"""Logic + HTTP tests for the rewritten fireplace app (run in simulation mode)."""
import json, time, urllib.request, urllib.error
from datetime import datetime, timedelta

import controller as C

ok = True
def check(name, cond):
    global ok
    ok = ok and cond
    print(("PASS " if cond else "FAIL ") + name)

# ---- controller logic (no HTTP) ----
ctl = C.Controller(hardware=False)
check("starts off", ctl.status()["on"] is False)

s = ctl.turn_on()
check("turn_on -> on", s["on"] is True and s["off_in_seconds"] > 0)
check("default ~60 min", 3500 <= s["off_in_seconds"] <= 3600)

ceiling = ctl.ceiling_at
for _ in range(10):
    ctl.adjust(1)
check("+hour capped at ceiling", ctl.off_at == ceiling)

ctl.turn_on()  # already on, no change expected
ctl.off_at = datetime.now() + timedelta(minutes=30)
ctl.adjust(-1)  # 30min - 60min -> past -> should turn off
check("subtract past present turns off", ctl.status()["on"] is False)

# auto-off watchdog: arm, force the deadline into the past, wait one tick
ctl.turn_on()
ctl.off_at = datetime.now() - timedelta(seconds=1)
time.sleep(3)
check("watchdog auto-off fired", ctl.status()["on"] is False)
ctl.shutdown()
print("--- logic done ---")

# ---- HTTP (against the running server on :5055) ----
BASE = "http://127.0.0.1:5055"
def req(path, method="GET", body=None, form=None):
    data, headers = None, {}
    if body is not None:
        data = json.dumps(body).encode(); headers["Content-Type"] = "application/json"
    if form is not None:
        data = form.encode(); headers["Content-Type"] = "application/x-www-form-urlencoded"
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r)
        return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

st, b = req("/api/status"); j = json.loads(b)
check("GET /api/status 200 off", st == 200 and j["on"] is False)
st, b = req("/", "GET"); check("GET / serves page", st == 200 and "Fireplace" in b)
st, b = req("/static/style.css"); check("static css served", st == 200 and "--ember" in b)

st, b = req("/api/on", "POST"); j = json.loads(b)
check("POST /api/on", st == 200 and j["on"] is True)

st, b = req("/get_time"); j = json.loads(b)
check("compat /get_time ON", "ON" in j["fire_status_str"] and j["fire_off_time"].startswith("Fire will turn off at"))

st, b = req("/api/adjust", "POST", body={"hours": 1}); check("adjust +1 ok", st == 200)
st, b = req("/api/adjust", "POST", body={"hours": 5}); check("adjust bad value 400", st == 400)

st, b = req("/", "POST", form="unset_button=Fire+Off"); check("compat form off (<400)", st < 400)
st, b = req("/get_time"); j = json.loads(b)
check("after form off -> OFF", "OFF" in j["fire_status_str"] and j["fire_off_time"] == "")

st, b = req("/", "POST", form="set_button=Fire+On"); check("compat form on (<400)", st < 400)
st, b = req("/api/status"); j = json.loads(b); check("after form on -> on", j["on"] is True)

# absolute off-time picker
target = (j["now_epoch"] // 60 + 30) * 60  # 30 whole minutes from now
st, b = req("/api/off_time", "POST", body={"at_epoch": target}); j2 = json.loads(b)
check("off_time sets ~30m", st == 200 and abs(j2["off_epoch"] - target) <= 60)
st, b = req("/api/off_time", "POST", body={"at_epoch": j["now_epoch"] + 99 * 3600}); j3 = json.loads(b)
check("off_time clamps to ceiling", 0 < j3["off_epoch"] <= j3["ceiling_epoch"])
st, b = req("/api/off_time", "POST", body={}); check("off_time missing arg 400", st == 400)
req("/api/off", "POST")

print("ALL PASS" if ok else "SOME FAILED")
import sys; sys.exit(0 if ok else 1)
