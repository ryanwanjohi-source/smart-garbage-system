#!/usr/bin/env bash
# One-command demo for the smart garbage system.
# Starts Mosquitto, seeds the SQLite demo DB, then runs the MQTT ingest,
# the Flask backend (dashboard on http://localhost:5000) and the 6-bin simulator.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export DATABASE_URL="sqlite:///${ROOT}/demo.db"
export MQTT_HOST="${MQTT_HOST:-localhost}"
export MQTT_PORT="${MQTT_PORT:-1883}"
export PORT="${PORT:-5000}"

mkdir -p logs

# --- Python env -------------------------------------------------------------
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Creating project venv (.venv)..."
  python3 -m venv "$ROOT/.venv"
fi
if ! "$ROOT/.venv/bin/python" -c "import flask, paho.mqtt, flask_sqlalchemy" 2>/dev/null; then
  echo "Installing backend dependencies..."
  "$ROOT/.venv/bin/pip" install -q -r "$ROOT/backend/requirements.txt"
fi
PY="$ROOT/.venv/bin/python"

# --- Mosquitto --------------------------------------------------------------
MOSQ_STARTED=0
if ! command -v mosquitto >/dev/null 2>&1; then
  echo "ERROR: 'mosquitto' is not installed."
  echo "  Ubuntu/Debian: sudo apt install mosquitto"
  echo "  macOS:         brew install mosquitto"
  echo "  ...then re-run ./demo.sh"
  exit 1
fi
if ! pgrep -x mosquitto >/dev/null 2>&1; then
  echo "Starting Mosquitto (MQTT broker)..."
  mosquitto -d -c "$ROOT/mosquitto.conf"
  MOSQ_STARTED=1
  sleep 1
fi
echo "$MOSQ_STARTED" > .demo_mosq_owned

# --- Seed (idempotent) ------------------------------------------------------
echo "Seeding demo bins..."
"$PY" backend/seed.py

# --- Services ---------------------------------------------------------------
start_svc() { # name, script dir, script
  nohup "$PY" -u "$2/$3" >"logs/$1.log" 2>&1 &
  echo $! >> .demo_pids
  echo "  $1 (pid $!)"
}

rm -f .demo_pids
echo "Starting services (logs in logs/)..."
start_svc ingest backend mqtt_ingest.py
start_svc backend backend app.py
start_svc simulator simulator bin_sim.py

# --- Wait for the dashboard -------------------------------------------------
echo -n "Waiting for http://localhost:${PORT}"
for _ in $(seq 1 30); do
  if curl -sf -o /dev/null "http://localhost:${PORT}/api/bins" 2>/dev/null; then
    echo
    echo "DEMO READY"
    echo "  Dashboard : http://localhost:${PORT}/"
    echo "  API bins  : http://localhost:${PORT}/api/bins"
    echo "  Login     : dispatcher@demo.ke / demo1234  (seeded demo account)"
    echo "  Stop      : ./stop-demo.sh"
    exit 0
  fi
  echo -n "."
  sleep 1
done
echo
echo "The dashboard did not come up. Check logs/:"
ls logs/
exit 1
