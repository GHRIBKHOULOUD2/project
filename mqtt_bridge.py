#!/usr/bin/env python3
# =============================================================
# mqtt_bridge.py — MQTT -> shared_state bridge
# Listens to SmartGuard topics and updates state
# Runs on PC Controller (192.168.1.100)
# =============================================================

import json, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import paho.mqtt.client as mqtt
from config import MQTT_BROKER, MQTT_PORT, TEMP_THRESHOLD, HUM_MIN, HUM_MAX, RFID_AUTHORIZED
from shared_state import (
    read_state, add_alert,
    update_mqtt_env, update_mqtt_rfid
)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[mqtt_bridge] Connected to broker {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe("smartguard/#")
        print("[mqtt_bridge] Subscribed to smartguard/#")
    else:
        print(f"[mqtt_bridge] Connection failed rc={rc}")


def on_message(client, userdata, msg):
    topic   = msg.topic
    payload = msg.payload.decode("utf-8", errors="ignore").strip()
    print(f"[mqtt_bridge] {topic} -> {payload}")

    # ── smartguard/env ────────────────────────────────────────
    if topic == "smartguard/env":
        try:
            data = json.loads(payload)
            temp = float(data.get("temp", 0))
            hum  = float(data.get("hum", 0))

            led_temp = "ON" if temp > TEMP_THRESHOLD else "OFF"
            led_hum  = "ON" if (hum < HUM_MIN or hum > HUM_MAX) else "OFF"

            update_mqtt_env(temp, hum, led_temp, led_hum)

            if temp > 35:
                add_alert("HIGH_TEMP",
                    f"Critical temperature: {temp}C (threshold 35C)", "HIGH")
            if hum > 90:
                add_alert("HIGH_HUMIDITY",
                    f"Critical humidity: {hum}% (threshold 90%)", "MEDIUM")

        except Exception as e:
            print(f"[mqtt_bridge] ENV parse error: {e}")

    # ── smartguard/rfid ───────────────────────────────────────
    elif topic == "smartguard/rfid":
        try:
            data   = json.loads(payload)
            uid    = str(data.get("uid", "")).strip().upper()
            name   = RFID_AUTHORIZED.get(uid, "UNKNOWN")
            status = "GRANTED" if name != "UNKNOWN" else "DENIED"

            update_mqtt_rfid(uid, status, name)

            if status == "DENIED":
                add_alert("RFID_DENIED",
                    f"Access denied - UID: {uid}", "MEDIUM")
            else:
                print(f"[mqtt_bridge] Access granted: {name} ({uid})")

        except Exception as e:
            print(f"[mqtt_bridge] RFID parse error: {e}")

    # ── smartguard/cmd/* ──────────────────────────────────────
    elif topic.startswith("smartguard/cmd/"):
        cmd   = topic.split("/")[-1]
        state = read_state()
        state.setdefault("mqtt_data", {}).setdefault("leds", {})
        if cmd == "led_temp":
            state["mqtt_data"]["leds"]["led_temp"] = payload
        elif cmd == "led_hum":
            state["mqtt_data"]["leds"]["led_hum"] = payload
        elif cmd == "rfid":
            state["mqtt_data"]["last_rfid_status"] = payload
        from shared_state import write_state
        write_state(state)


def main():
    client = mqtt.Client(client_id="dt_mqtt_bridge")
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[mqtt_bridge] Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("[mqtt_bridge] Stopped")
        client.disconnect()
    except Exception as e:
        print(f"[mqtt_bridge] Error: {e}")
        time.sleep(5)
        main()


if __name__ == "__main__":
    main()
