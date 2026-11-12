"""Flask REST API (proposal §3.3.3.2 / §3.3.3.4 dashboard backing).

Endpoints:
  GET  /api/bins                      list bins + latest telemetry
  GET  /api/bins/<id>/telemetry       recent readings for one bin
  POST /api/bins/<code>/command       publish SORT:<n> to smartbin/<code>/command
  GET  /api/alerts?threshold=80       bins currently above the fill threshold
  POST /api/routes/optimize           build a route over full bins
  GET  /api/routes/<id>               fetch a stored route
  GET  /                             the dashboard (static files)

Run:  python app.py   ->  http://localhost:5000
Env:  DATABASE_URL, MQTT_HOST, MQTT_PORT
"""
import os
import sys
from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analytics"))
from models import db, Bin, TelemetryReading, CollectionRoute, RouteStop
from route_optimizer import optimize_route  # noqa: E402

import paho.mqtt.client as mqtt

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "postgresql://smartbin:smartbin@localhost:5432/smartbin")
db.init_app(app)

DASHBOARD_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard")

_mqtt_client = None


def mqtt_client():
    """Lazily-connected publish client for bin commands."""
    global _mqtt_client
    if _mqtt_client is None:
        _mqtt_client = mqtt.Client()
        _mqtt_client.connect(os.getenv("MQTT_HOST", "localhost"),
                             int(os.getenv("MQTT_PORT", "1883")))
        _mqtt_client.loop_start()
    return _mqtt_client


@app.get("/")
def dashboard():
    return send_from_directory(DASHBOARD_DIR, "index.html")


@app.get("/<path:path>")
def dashboard_static(path):
    # serve dashboard css/js; anything else 404s
    if path.startswith(("css/", "js/")):
        return send_from_directory(DASHBOARD_DIR, path)
    return jsonify({"error": "not found"}), 404


@app.get("/api/bins")
def list_bins():
    out = []
    for b in Bin.query.all():
        t = b.latest_telemetry()
        out.append({
            "id": b.id, "code": b.code, "location": b.location_name,
            "lat": b.latitude, "lng": b.longitude, "status": b.status,
            "fill_pct": t.fill_pct if t else None,
            "mass_kg": t.mass_kg if t else None,
            "last_seen": t.recorded_at.isoformat() if t else None,
        })
    return jsonify(out)


@app.get("/api/bins/<int:bin_id>/telemetry")
def bin_telemetry(bin_id):
    rows = (TelemetryReading.query.filter_by(bin_id=bin_id)
            .order_by(TelemetryReading.recorded_at.desc()).limit(100).all())
    return jsonify([{
        "fill_pct": r.fill_pct, "mass_kg": r.mass_kg,
        "gas_raw": r.gas_raw, "at": r.recorded_at.isoformat()} for r in rows])


@app.post("/api/bins/<code>/command")
def bin_command(code):
    """Publish a sort command to the bin over MQTT. Body: {"category": 0|1|2}."""
    b = Bin.query.filter_by(code=code).first()
    if not b:
        return jsonify({"error": f"unknown bin {code}"}), 404
    try:
        category = int((request.get_json(force=True) or {}).get("category", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "category must be 0, 1 or 2"}), 400
    if category not in (0, 1, 2):
        return jsonify({"error": "category must be 0, 1 or 2"}), 400
    topic = f"smartbin/{code}/command"
    mqtt_client().publish(topic, f"SORT:{category}")
    return jsonify({"ok": True, "topic": topic,
                    "command": f"SORT:{category}"}), 202


@app.get("/api/alerts")
def alerts():
    """Bins whose latest fill reading is at/above the threshold (default 80%)."""
    threshold = float(request.args.get("threshold", 80))
    out = []
    for b in Bin.query.filter_by(status="active").all():
        t = b.latest_telemetry()
        if t and t.fill_pct >= threshold:
            out.append({"code": b.code, "location": b.location_name,
                        "fill_pct": t.fill_pct,
                        "at": t.recorded_at.isoformat()})
    out.sort(key=lambda r: r["fill_pct"], reverse=True)
    return jsonify(out)


@app.post("/api/routes/optimize")
def make_route():
    """Build a collection route over bins above the fill threshold."""
    threshold = float(request.args.get("threshold", 70))
    bins = Bin.query.filter_by(status="active").all()
    candidates = [b for b in bins
                  if (t := b.latest_telemetry()) and t.fill_pct >= threshold]
    if not candidates:
        return jsonify({"error": "no bins above threshold"}), 404
    order, km = optimize_route(
        [(b.id, b.latitude, b.longitude) for b in candidates])
    route = CollectionRoute(
        name=f"Route {len(CollectionRoute.query.all()) + 1}", total_distance_km=km)
    db.session.add(route)
    db.session.flush()
    for i, bid in enumerate(order):
        db.session.add(RouteStop(route_id=route.id, bin_id=bid, stop_order=i))
    db.session.commit()
    return jsonify({"route_id": route.id, "stops": order,
                    "distance_km": round(km, 2)}), 201


@app.get("/api/routes/<int:route_id>")
def get_route(route_id):
    r = CollectionRoute.query.get_or_404(route_id)
    stops = (RouteStop.query.filter_by(route_id=r.id)
             .order_by(RouteStop.stop_order).all())
    return jsonify({
        "id": r.id, "name": r.name, "status": r.status,
        "distance_km": r.total_distance_km,
        "stops": [{"bin_id": s.bin_id, "order": s.stop_order} for s in stops],
    })


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
