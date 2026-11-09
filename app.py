#!/usr/bin/env python3
"""Web server for the front-room gas fireplace (Raspberry Pi Zero 2 W).

Routes
------
GET  /              the control page
GET  /api/status    JSON: {on, now, off_at, off_in_seconds, ceiling_at}
POST /api/on        light the fire            -> status JSON
POST /api/off       extinguish the fire       -> status JSON
POST /api/adjust    body {"hours": 1 | -1}    -> status JSON

Compatibility (used by the ac.local mini-split app -- keep these):
GET  /get_time      JSON: {fire_off_time, current_time, fire_status_str}
POST /               form field set_button | unset_button | add_hour | subtract_hour
"""
from __future__ import annotations

import atexit
import logging
import os
import signal

from flask import Flask, jsonify, redirect, render_template, request

from controller import Controller

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pyro.app")

HARDWARE = os.environ.get("FIRE_HARDWARE", "1") != "0"
PORT = int(os.environ.get("PORT", "5000"))

app = Flask(__name__)
controller = Controller(hardware=HARDWARE)


def _shutdown(*_args) -> None:
    controller.shutdown()


atexit.register(_shutdown)


# ---- modern API ---------------------------------------------------------
@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def api_status():
    return jsonify(controller.status())


@app.post("/api/on")
def api_on():
    return jsonify(controller.turn_on())


@app.post("/api/off")
def api_off():
    return jsonify(controller.turn_off())


@app.post("/api/adjust")
def api_adjust():
    data = request.get_json(silent=True) or {}
    try:
        hours = int(data.get("hours", 0))
    except (TypeError, ValueError):
        hours = 0
    if hours not in (-1, 1):
        return jsonify({"error": "hours must be 1 or -1"}), 400
    return jsonify(controller.adjust(hours))


# ---- compatibility endpoints (ac.local mini-split app) ------------------
@app.get("/get_time")
def get_time():
    st = controller.status()
    off = f"Fire will turn off at {st['off_at']}" if st["on"] else ""
    return jsonify({
        "fire_off_time": off,
        "current_time": st["now"],
        "fire_status_str": "The Fireplace is ON" if st["on"] else "The Fireplace is OFF",
    })


@app.post("/")
def legacy_form():
    form = request.form
    if "set_button" in form:
        controller.turn_on()
    elif "unset_button" in form:
        controller.turn_off()
    elif "add_hour" in form:
        controller.adjust(1)
    elif "subtract_hour" in form:
        controller.adjust(-1)
    return redirect("/", code=303)


def main() -> None:
    # Make sure a SIGTERM from systemd leaves the fire off.
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    log.info("starting on :%d (hardware=%s)", PORT, HARDWARE)
    try:
        app.run(host="0.0.0.0", port=PORT, threaded=True)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        _shutdown()


if __name__ == "__main__":
    main()
