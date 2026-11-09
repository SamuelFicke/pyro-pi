"""Stateful fireplace controller with an automatic shut-off timer.

This owns the single source of truth for whether the fire is on and when it
should turn itself off. A background thread enforces the shut-off even when no
browser is connected, which is the whole reason the controller is separate from
the web layer.

Safety behaviour:
  * the fire is forced OFF when the controller starts,
  * the fire is forced OFF again on shutdown,
  * it always turns itself off after at most MAX_ON (hard ceiling), and
  * '+ hour' can never push past that ceiling.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timedelta

from fireplace import Fireplace

log = logging.getLogger("pyro.controller")


def _minutes(env_name: str, default_minutes: int) -> int:
    try:
        return max(1, int(os.environ[env_name]))
    except (KeyError, ValueError):
        return default_minutes


# Defaults match the original app (1 hour on, 4 hour ceiling); overridable by env
# so the behaviour is configurable and the tests can use short windows.
DEFAULT_ON = timedelta(minutes=_minutes("FIRE_DEFAULT_MINUTES", 60))
MAX_ON = timedelta(minutes=_minutes("FIRE_MAX_MINUTES", 240))
_TICK_SECONDS = 2
_TIME_FMT = "%I:%M:%S %p"


class Controller:
    def __init__(self, hardware: bool = True):
        self._fire = Fireplace(hardware=hardware)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self.on = False
        self.off_at: datetime | None = None
        self.ceiling_at: datetime | None = None

        # Known-safe starting point.
        self._fire.off()

        self._thread = threading.Thread(target=self._watchdog, name="auto-off", daemon=True)
        self._thread.start()

    # ---- commands -------------------------------------------------------
    def turn_on(self) -> dict:
        with self._lock:
            if not self.on:
                now = datetime.now()
                self.on = True
                self.off_at = now + DEFAULT_ON
                self.ceiling_at = now + MAX_ON
                self._fire.on()
                log.info("turned ON, off at %s", self.off_at.strftime(_TIME_FMT))
            return self.status()

    def turn_off(self) -> dict:
        with self._lock:
            # Always send an off pulse, even if we already think it's off.
            self._set_off()
            return self.status()

    def adjust(self, hours: int) -> dict:
        with self._lock:
            if self.on and self.off_at is not None:
                self.off_at += timedelta(hours=hours)
                if self.off_at > self.ceiling_at:
                    self.off_at = self.ceiling_at
                if self.off_at <= datetime.now():
                    # Subtracted past the present -> just turn it off now.
                    self._set_off()
                else:
                    log.info("off time now %s", self.off_at.strftime(_TIME_FMT))
            return self.status()

    # ---- internals ------------------------------------------------------
    def _set_off(self) -> None:
        self.on = False
        self.off_at = None
        self.ceiling_at = None
        self._fire.off()
        log.info("turned OFF")

    def _watchdog(self) -> None:
        while not self._stop.wait(_TICK_SECONDS):
            with self._lock:
                if self.on and self.off_at is not None and datetime.now() >= self.off_at:
                    log.info("auto-off reached")
                    self._set_off()

    def status(self) -> dict:
        with self._lock:
            now = datetime.now()
            remaining = 0
            if self.on and self.off_at is not None:
                remaining = max(0, int((self.off_at - now).total_seconds()))
            return {
                "on": self.on,
                "now": now.strftime(_TIME_FMT),
                "off_at": self.off_at.strftime(_TIME_FMT) if self.on and self.off_at else "",
                "off_in_seconds": remaining,
                "ceiling_at": self.ceiling_at.strftime(_TIME_FMT) if self.on and self.ceiling_at else "",
            }

    def shutdown(self) -> None:
        """Stop the watchdog and leave the fire off. Safe to call repeatedly."""
        self._stop.set()
        with self._lock:
            self._set_off()
            self._fire.cleanup()
