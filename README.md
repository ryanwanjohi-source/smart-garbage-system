# Smart Garbage System

Final-year project implementation for the proposal
*"Smart garbage system with multi-sensor telemetry, automated mechanical waste
segregation, and route optimization for urban Kenya."*

## Modules

| Folder | Layer (per proposal §3.3.3) | Tech |
|---|---|---|
| `firmware/` | 3.3.3.1 Edge and mechanical module | ESP32 + C++ (PlatformIO) |
| `backend/` | 3.3.3.2 Communication, back-end, storage | Python + Flask, MQTT ingest, PostgreSQL |
| `analytics/` | 3.3.3.3 Analytics and route optimization | pandas, scikit-learn, NetworkX |
| `dashboard/` | 3.3.3.4 Dashboard and access control | HTML/CSS/JS + Bootstrap 5 |
| `simulator/` | Demo/test stand-in for ESP32 hardware | Python + paho-mqtt |
| `db/` | Central data | PostgreSQL schema |

## Quickstart

### Option A — full stack with Docker (recommended on your machine)

1. Open this folder in VS Code.
2. Start infrastructure:
   ```bash
   docker compose up -d        # PostgreSQL + Mosquitto MQTT broker
   ```
3. Backend (two terminals):
   ```bash
   cd backend && pip install -r requirements.txt
   python seed.py              # demo bins + dispatcher user (idempotent)
   python app.py               # API + dashboard on http://localhost:5000
   python mqtt_ingest.py       # telemetry subscriber (second terminal)
   ```
4. Simulate bins (third terminal, no hardware needed):
   ```bash
   cd simulator && pip install paho-mqtt
   python bin_sim.py           # 6 bins publish telemetry every 5 s
   ```
5. Open http://localhost:5000 — live bin table, alerts, route optimizer,
   and the sort-command panel (commands publish to `smartbin/<code>/command`
   and the simulator executes them).
6. Firmware: open `firmware/` in PlatformIO, set Wi-Fi/MQTT credentials and
   `BIN_CODE` in `src/main.cpp`, flash to the ESP32.

### Option B — without Docker (SQLite)

```bash
export DATABASE_URL="sqlite:///smartbin.db"
# then follow steps 3–5 above (skip docker compose; run a local mosquitto
#  broker or point MQTT_HOST at a reachable broker)
```

## API reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/bins` | bins + latest telemetry |
| GET | `/api/bins/<id>/telemetry` | last 100 readings for a bin |
| POST | `/api/bins/<code>/command` | `{"category": 0\|1\|2}` → publishes `SORT:<n>` |
| GET | `/api/alerts?threshold=80` | bins currently above fill threshold |
| POST | `/api/routes/optimize?threshold=70` | build route over full bins |
| GET | `/api/routes/<id>` | fetch a stored route |
| GET | `/` | the dashboard |

## MQTT topics

- `smartbin/<bin_code>/telemetry` — sensor payload from bin → backend
- `smartbin/<bin_code>/sort` — segregation event from bin → backend
- `smartbin/<bin_code>/command` — backend → bin (`SORT:0|1|2`)

## Demo login

dispatcher@demo.ke / demo1234 (seeded by `backend/seed.py`; dashboard
currently runs without enforced login — wire it to FR08 when ready).
