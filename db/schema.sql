-- Smart garbage system schema (proposal §3.3.3.2, PostgreSQL)

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin','dispatcher','driver','regulator')),
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bins (
    id             SERIAL PRIMARY KEY,
    code           TEXT UNIQUE NOT NULL,          -- e.g. NRB-001
    location_name  TEXT NOT NULL,
    latitude       DOUBLE PRECISION NOT NULL,
    longitude      DOUBLE PRECISION NOT NULL,
    capacity_litres INTEGER NOT NULL DEFAULT 240,
    status         TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS telemetry_readings (
    id          SERIAL PRIMARY KEY,
    bin_id      INTEGER NOT NULL REFERENCES bins(id) ON DELETE CASCADE,
    fill_pct    REAL NOT NULL,
    mass_kg     REAL,
    gas_raw     INTEGER,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_telemetry_bin_time ON telemetry_readings(bin_id, recorded_at DESC);

CREATE TABLE IF NOT EXISTS sort_events (
    id          SERIAL PRIMARY KEY,
    bin_id      INTEGER NOT NULL REFERENCES bins(id) ON DELETE CASCADE,
    category    TEXT NOT NULL CHECK (category IN ('recyclable','organic','general')),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS collection_routes (
    id                SERIAL PRIMARY KEY,
    name              TEXT NOT NULL,
    total_distance_km REAL,
    status            TEXT NOT NULL DEFAULT 'planned',
    created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS route_stops (
    id        SERIAL PRIMARY KEY,
    route_id  INTEGER NOT NULL REFERENCES collection_routes(id) ON DELETE CASCADE,
    bin_id    INTEGER NOT NULL REFERENCES bins(id) ON DELETE CASCADE,
    stop_order INTEGER NOT NULL
);

-- demo seed: two bins in Nairobi CBD
INSERT INTO bins (code, location_name, latitude, longitude) VALUES
  ('NRB-001', 'Kenyatta Ave / Moi Ave', -1.2864, 36.8172),
  ('NRB-002', 'Tom Mboya St',           -1.2841, 36.8219)
ON CONFLICT (code) DO NOTHING;
