# pyro-pi — front-room fireplace controller

A small Flask web app on a Raspberry Pi Zero 2 W that turns the gas fireplace on
and off and enforces an automatic shut-off timer. Served on port 5000 as the
`fire_pi_webapp` systemd service, and also driven by the house `ac.local` app.

## How it works

- **`fireplace.py`** — GPIO driver. The relay board is pulsed for 0.2 s on
  BCM pin 17 (on) or 22 (off). Hardware access is skipped when run with
  `FIRE_HARDWARE=0`.
- **`controller.py`** — holds the on/off state and the shut-off time, and runs a
  background thread that turns the fire off when the timer expires, even if no
  browser is open. The fire is forced off at start-up and at shutdown.
- **`app.py`** — Flask routes and the JSON API.
- **`templates/` + `static/`** — the control page.

## HTTP interface

| Method & path     | Purpose                                             |
|-------------------|-----------------------------------------------------|
| `GET /`           | control page                                        |
| `GET /api/status` | `{on, now, off_at, off_in_seconds, ceiling_at}`     |
| `POST /api/on`    | light the fire                                      |
| `POST /api/off`   | extinguish the fire                                 |
| `POST /api/adjust`| body `{"hours": 1 \| -1}` — move the shut-off time  |
| `GET /get_time`   | legacy status JSON (used by `ac.local`)             |
| `POST /`          | legacy form buttons (used by `ac.local`)            |

## Configuration (environment variables)

| Variable               | Default | Meaning                               |
|------------------------|---------|---------------------------------------|
| `PORT`                 | `5000`  | web server port                       |
| `FIRE_HARDWARE`        | `1`     | `0` = simulation, no GPIO             |
| `FIRE_DEFAULT_MINUTES` | `60`    | on-time when first lit                |
| `FIRE_MAX_MINUTES`     | `240`   | hard ceiling the fire can't exceed    |

## Run locally (no hardware)

    FIRE_HARDWARE=0 PORT=5055 python3 app.py

## Service

    sudo systemctl restart fire_pi_webapp
    journalctl -u fire_pi_webapp -f
