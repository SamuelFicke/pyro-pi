"""Low-level driver for the gas fireplace.

The fireplace is switched by a two-input relay board wired to two GPIO pins.
Turning the fire on or off is a momentary *pulse* on the matching pin (it emulates
pressing the on/off buttons of the fireplace's own controller), after which both
pins are driven low again.

The pin numbers, the pulse length and the exact on/off sequence are kept identical
to the original, proven version -- do not change them without testing on the real
hardware, since they drive a real gas appliance.
"""
from __future__ import annotations

import logging
from time import sleep

log = logging.getLogger("pyro.fireplace")

# BCM pin numbers of the relay inputs.
PIN_ON = 17   # pulse high to light the fire
PIN_OFF = 22  # pulse high to extinguish the fire
PULSE_SECONDS = 0.2


class Fireplace:
    """Pulses the relay to turn the fire on or off.

    With ``hardware=False`` no GPIO library is imported and actions are only
    logged, so the web app can be run and tested on any machine.
    """

    def __init__(self, hardware: bool = True):
        self.hardware = hardware
        self._gpio = None
        if hardware:
            import RPi.GPIO as GPIO  # imported lazily so sim mode needs no GPIO
            self._gpio = GPIO
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(PIN_ON, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(PIN_OFF, GPIO.OUT, initial=GPIO.LOW)
            log.info("GPIO ready (on=%d, off=%d)", PIN_ON, PIN_OFF)
        else:
            log.info("simulation mode: GPIO not touched")

    def on(self) -> None:
        """Pulse the 'on' line to light the fire."""
        self._pulse(PIN_ON)
        log.info("fire ON pulse")

    def off(self) -> None:
        """Pulse the 'off' line to extinguish the fire."""
        self._pulse(PIN_OFF)
        log.info("fire OFF pulse")

    def _pulse(self, active_pin: int) -> None:
        if not self.hardware:
            return
        other = PIN_OFF if active_pin == PIN_ON else PIN_ON
        self._gpio.output(active_pin, True)
        self._gpio.output(other, False)
        sleep(PULSE_SECONDS)
        self._all_low()

    def _all_low(self) -> None:
        if self.hardware:
            self._gpio.output(PIN_ON, False)
            self._gpio.output(PIN_OFF, False)

    def cleanup(self) -> None:
        """Release the GPIO pins. Safe to call more than once."""
        if self.hardware and self._gpio is not None:
            self._all_low()
            self._gpio.cleanup()
            self._gpio = None
            log.info("GPIO cleaned up")


if __name__ == "__main__":
    # Manual control:  python3 fireplace.py on|off
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action not in ("on", "off"):
        sys.exit("usage: python3 fireplace.py on|off")
    fp = Fireplace()
    try:
        getattr(fp, action)()
    finally:
        fp.cleanup()
