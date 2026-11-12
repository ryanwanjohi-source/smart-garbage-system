/*
 * Smart bin edge firmware (proposal §3.3.3.1)
 * ESP32: reads ultrasonic fill height (HC-SR04), load-cell mass (HX711),
 * MQ-135 air-quality gas sensor; publishes telemetry over MQTT; drives the
 * tri-category sorting actuator; caches readings offline when MQTT is down.
 */
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <HX711.h>
#include <ESP32Servo.h>
#include <LittleFS.h>

// ---- config: fill in before flashing ----
const char* WIFI_SSID = "YOUR_SSID";
const char* WIFI_PASS = "YOUR_PASSWORD";
const char* MQTT_HOST = "192.168.1.10";
const int   MQTT_PORT = 1883;
const char* BIN_CODE  = "NRB-001";

// ---- pins ----
const int TRIG_PIN = 5, ECHO_PIN = 18;      // HC-SR04 ultrasonic
const int HX_DOUT  = 16, HX_SCK = 4;        // HX711 load cell
const int MQ_PIN   = 34;                    // MQ-135 (analog)
const int SORT_PIN = 25;                    // sorting servo signal
const int BIN_DEPTH_CM = 90;                // bin interior depth

WiFiClient espClient;
PubSubClient mqtt(espClient);
HX711 scale;
Servo sortServo;

float readFillPercent() {
  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long us = pulseIn(ECHO_PIN, HIGH, 30000);
  float distCm = us / 58.0;
  float pct = 100.0 * (1.0 - distCm / BIN_DEPTH_CM);
  return constrain(pct, 0, 100);
}

// 0=recyclable, 1=organic, 2=general — servo positions per compartment
void sortWaste(int category) {
  int angles[3] = {30, 90, 150};
  if (category < 0 || category > 2) return;
  int target = angles[category];
  int pos = sortServo.read();
  int step = (target > pos) ? 2 : -2;   // smooth sweep, ~2 deg per 15 ms
  for (; (step > 0) ? (pos < target) : (pos > target); pos += step) {
    sortServo.write(pos);
    delay(15);
  }
  sortServo.write(target);
  Serial.printf("Sorted to compartment %d (servo %d deg)\n", category, target);
}

void cacheOffline(const String& payload) {
  File f = LittleFS.open("/cache.log", FILE_APPEND);
  if (f) { f.println(payload); f.close(); }
}

void replayCache() {
  if (!LittleFS.exists("/cache.log")) return;
  File f = LittleFS.open("/cache.log", FILE_READ);
  String topic = String("smartbin/") + BIN_CODE + "/telemetry";
  while (f.available()) {
    String line = f.readStringUntil('\n');
    line.trim();
    if (line.length() && mqtt.connected()) mqtt.publish(topic.c_str(), line.c_str());
  }
  f.close();
  LittleFS.remove("/cache.log");
}

void onCommand(char* topic, byte* payload, unsigned int len) {
  String msg; for (unsigned i = 0; i < len; i++) msg += (char)payload[i];
  if (msg.startsWith("SORT:")) sortWaste(msg.substring(5).toInt());
}

void reconnectMqtt() {
  while (!mqtt.connected()) {
    Serial.print("MQTT connecting...");
    if (mqtt.connect(BIN_CODE)) {
      Serial.println("ok");
      String cmd = String("smartbin/") + BIN_CODE + "/command";
      mqtt.subscribe(cmd.c_str());
      replayCache();
    } else { Serial.println("retry in 5s"); delay(5000); }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT); pinMode(ECHO_PIN, INPUT);
  pinMode(SORT_PIN, OUTPUT);
  scale.begin(HX_DOUT, HX_SCK);
  // TODO: scale.set_scale(<calibration factor>); scale.tare();
  sortServo.attach(SORT_PIN);   // tri-category sorting actuator
  LittleFS.begin(true);

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onCommand);
}

void loop() {
  if (!mqtt.connected()) reconnectMqtt();
  mqtt.loop();

  float fill  = readFillPercent();
  float mass  = scale.is_ready() ? scale.get_units(5) : -1;
  int   gas   = analogRead(MQ_PIN);

  char payload[160];
  snprintf(payload, sizeof(payload),
           "{\"bin\":\"%s\",\"fill_pct\":%.1f,\"mass_kg\":%.2f,\"gas_raw\":%d}",
           BIN_CODE, fill, mass, gas);

  String topic = String("smartbin/") + BIN_CODE + "/telemetry";
  if (mqtt.connected()) mqtt.publish(topic.c_str(), payload);
  else cacheOffline(payload);   // offline cache per §1.7.2 delimitations

  delay(60000); // report every 60 s
}
