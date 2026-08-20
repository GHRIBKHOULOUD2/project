#!/usr/bin/env python3
# =============================================================
# shared_state.py — Thread-safe shared state (JSON file)
# =============================================================

import json, os, time, threading
from config import VLAN_DEFAULT_POLICY

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
_lock = threading.Lock()

DEFAULT_STATE = {
    "hosts":       {},
    "blocked":     [],
    "switches":    {},
    "alerts":      [],
    "camera":      {"data": None, "timestamp": None, "ip": None},
    "sensor_data": {},
    "mqtt_data":   {
        "env":              {},
        "rfid":             {},
        "leds":             {"led_temp": "OFF", "led_hum": "OFF"},
        "access_log":       [],
        "last_rfid_uid":    "",
        "last_rfid_status": "",
    },
    "vlan_policy": {},
    "host_policy": {},
    "last_updated": "",
}


def read_state() -> dict:
    with _lock:
        if not os.path.exists(STATE_FILE):
            return dict(DEFAULT_STATE)
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
            # Merge missing keys
            for k, v in DEFAULT_STATE.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            return dict(DEFAULT_STATE)


def write_state(state: dict):
    state["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with _lock:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)


def add_alert(alert_type: str, message: str, severity: str = "MEDIUM"):
    state = read_state()
    alerts = state.get("alerts", [])
    alerts.append({
        "type":      alert_type,
        "message":   message,
        "severity":  severity,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    # Keep only last 100 alerts
    state["alerts"] = alerts[-100:]
    write_state(state)


def update_mqtt_env(temp: float, hum: float, led_temp: str, led_hum: str):
    state = read_state()
    state.setdefault("mqtt_data", {})["env"] = {
        "temperature": temp,
        "humidity":    hum,
        "timestamp":   time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    state["mqtt_data"]["leds"] = {
        "led_temp": led_temp,
        "led_hum":  led_hum,
    }
    write_state(state)


def update_mqtt_rfid(uid: str, status: str, name: str):
    state = read_state()
    mqtt = state.setdefault("mqtt_data", {})
    mqtt["rfid"] = {
        "uid":         uid,
        "status":      status,
        "rfid_name":   name,
        "rfid_tag":    uid,
        "rfid_status": status,
        "access_count": len(mqtt.get("access_log", [])) + 1,
        "timestamp":   time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    mqtt["last_rfid_uid"]    = uid
    mqtt["last_rfid_status"] = status
    log = mqtt.setdefault("access_log", [])
    log.append({
        "uid":       uid,
        "name":      name,
        "status":    status,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    mqtt["access_log"] = log[-50:]  # keep last 50
    write_state(state)


def get_vlan_policy(state: dict, src_vlan: int, dst_vlan: int) -> str:
    if src_vlan == dst_vlan:
        return "allow"
    key = f"{src_vlan}_{dst_vlan}"
    vlan_policy = state.get("vlan_policy", {})
    if key in vlan_policy:
        return vlan_policy[key]
    # Fall back to default
    return VLAN_DEFAULT_POLICY.get((src_vlan, dst_vlan), "deny")


def set_vlan_policy(src_vlan: int, dst_vlan: int, action: str):
    state = read_state()
    key = f"{src_vlan}_{dst_vlan}"
    state.setdefault("vlan_policy", {})[key] = action
    write_state(state)


def set_host_policy(ip: str, allow_vlans: list, deny_vlans: list):
    state = read_state()
    state.setdefault("host_policy", {})[ip] = {
        "allow_vlans": allow_vlans,
        "deny_vlans":  deny_vlans,
    }
    write_state(state)


def reset_vlan_policy():
    state = read_state()
    state["vlan_policy"] = {}
    state["host_policy"]  = {}
    write_state(state)
