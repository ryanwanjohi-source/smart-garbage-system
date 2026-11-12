# System architecture

Maps to proposal §3.3.3 (Phase 3) and the conceptual architecture (Figure 2.6).

```
┌─────────────┐   MQTT telemetry    ┌──────────────┐   SQLAlchemy   ┌────────────┐
│  ESP32 bin  │ ─────────────────▶ │ Flask backend │ ───────────▶ │ PostgreSQL │
│  (firmware) │   smartbin/+/tele-  │  + MQTT       │              │            │
│  ultrasonic │   metry, /sort      │  ingest       │              │ bins,      │
│  load cell  │ ◀───────────────── │               │              │ telemetry, │
│  MQ-135     │   smartbin/+/       │  REST API     │              │ routes,    │
│  sorter     │   command           │               │              │ users      │
└─────────────┘                     └──────┬────────┘              └────────────┘
                                          │ REST/JSON
                                   ┌──────▼────────┐
                                   │  Analytics    │
                                   │  NetworkX     │
                                   │  route opt.   │
                                   │  sklearn fill │
                                   │  prediction   │
                                   └──────┬────────┘
                                          │
                                   ┌──────▼────────┐
                                   │  Dashboard    │
                                   │  Bootstrap 5  │
                                   │  bin status,  │
                                   │  routes, map  │
                                   └───────────────┘
```

## Data flow

1. ESP32 reads ultrasonic fill height, load-cell mass, MQ-135 gas level every
   60 s, publishes JSON to `smartbin/<code>/telemetry`.
2. When waste is deposited, the sorting actuator diverts it to one of three
   compartments (recyclable / organic / general); the event is published to
   `smartbin/<code>/sort`.
3. If MQTT is unreachable, readings are cached in on-device SQLite/LittleFS
   and replayed on reconnect (proposal §1.7.2 delimitations: offline cache).
4. `mqtt_ingest.py` persists telemetry and sort events to PostgreSQL.
5. The analytics module scores bins by fill level, builds a distance graph with
   NetworkX, and returns an ordered collection route via the API.
6. The dashboard shows live bin status, fill bars, and the optimized route.
