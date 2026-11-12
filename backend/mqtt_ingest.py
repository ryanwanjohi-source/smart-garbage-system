"""MQTT telemetry ingest (proposal §3.3.3.2).
Subscribes to smartbin/+/telemetry and smartbin/+/sort, persists to PostgreSQL.
Run:  python mqtt_ingest.py
"""
import json
import os
import paho.mqtt.client as mqtt
from models import db, Bin, TelemetryReading, SortEvent
from flask import Flask

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "postgresql://smartbin:smartbin@localhost:5432/smartbin")
db.init_app(app)

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))


def on_message(client, userdata, msg):
    topic = msg.topic  # smartbin/<code>/telemetry  or  smartbin/<code>/sort
    parts = topic.split("/")
    if len(parts) != 3 or parts[0] != "smartbin":
        return
    code, kind = parts[1], parts[2]
    with app.app_context():
        b = Bin.query.filter_by(code=code).first()
        if not b:
            print(f"unknown bin {code}; ignoring")
            return
        data = json.loads(msg.payload.decode())
        if kind == "telemetry":
            db.session.add(TelemetryReading(
                bin_id=b.id, fill_pct=data["fill_pct"],
                mass_kg=data.get("mass_kg"), gas_raw=data.get("gas_raw")))
        elif kind == "sort":
            db.session.add(SortEvent(bin_id=b.id, category=data["category"]))
        db.session.commit()
        print(f"stored {kind} for {code}")


client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT)
client.subscribe("smartbin/+/telemetry")
client.subscribe("smartbin/+/sort")
print(f"ingest listening on {MQTT_HOST}:{MQTT_PORT}")
client.loop_forever()
