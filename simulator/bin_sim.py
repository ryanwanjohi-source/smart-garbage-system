"""Bin simulator: stands in for ESP32 hardware during demos/tests.

Each simulated bin publishes telemetry to smartbin/<code>/telemetry every
INTERVAL seconds (fill level rises slowly, then the bin is 'emptied'),
occasionally publishes sort events, and listens on smartbin/<code>/command
to execute SORT:<n> commands like the real firmware.

Run:  python bin_sim.py [--bins NRB-001,NRB-002] [--interval 5]
Env:  MQTT_HOST, MQTT_PORT
"""
import argparse
import json
import os
import random
import threading
import time

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

CATEGORIES = ["recyclable", "organic", "general"]


class SimBin(threading.Thread):
    def __init__(self, code, interval):
        super().__init__(daemon=True)
        self.code = code
        self.interval = interval
        self.fill = random.uniform(20, 60)
        self.client = mqtt.Client()
        self.client.on_message = self.on_message
        self.client.connect(MQTT_HOST, MQTT_PORT)
        self.client.subscribe(f"smartbin/{code}/command")
        self.client.loop_start()

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode().strip()
        print(f"[{self.code}] command received: {payload}", flush=True)
        if payload.startswith("SORT:"):
            try:
                cat = int(payload.split(":")[1])
            except ValueError:
                return
            time.sleep(2)  # actuator travel time
            self.client.publish(
                f"smartbin/{self.code}/sort",
                json.dumps({"category": CATEGORIES[cat]}))
            print(f"[{self.code}] sorted -> {CATEGORIES[cat]}", flush=True)

    def run(self):
        while True:
            self.fill += random.uniform(0.5, 3.0)
            if self.fill >= 98:          # collection truck emptied the bin
                self.fill = random.uniform(5, 15)
            payload = {
                "bin": self.code,
                "fill_pct": round(self.fill, 1),
                "mass_kg": round(self.fill * 0.42 + random.uniform(-1, 1), 2),
                "gas_raw": random.randint(120, 420),
            }
            self.client.publish(f"smartbin/{self.code}/telemetry",
                                json.dumps(payload))
            if random.random() < 0.15:   # occasional sort event
                self.client.publish(
                    f"smartbin/{self.code}/sort",
                    json.dumps({"category": random.choice(CATEGORIES)}))
            time.sleep(self.interval)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins", default=",".join(f"NRB-00{i}" for i in range(1, 7)))
    ap.add_argument("--interval", type=float, default=5)
    args = ap.parse_args()
    sims = [SimBin(code.strip(), args.interval)
            for code in args.bins.split(",") if code.strip()]
    for s in sims:
        s.start()
    print(f"simulating {len(sims)} bins -> {MQTT_HOST}:{MQTT_PORT} "
          f"(Ctrl+C to stop)", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("stopped")


if __name__ == "__main__":
    main()
