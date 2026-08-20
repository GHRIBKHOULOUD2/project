#!/usr/bin/env python3
# =============================================================
# metrics_influx.py — InfluxDB 2.x metrics writer
# Updated: dual ESP8266 (RFID + ENV), VLAN policy metrics
# =============================================================

import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from config import (
    INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET,
    HOST_INFO, HOST_VLAN, HOST_QOS, VLAN_NAMES,
)
from shared_state import read_state, get_vlan_policy

client    = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

_seen_alerts  = set()
_prev_bytes   = {}
_alert_counts = {}

# Interface -> IP mapping (adjust to match your OVS port names)
INTF_TO_IP = {
    "br0-eth1": "192.168.10.1",   # PC-Client
    "br0-eth2": "192.168.20.1",   # Phone
    "br0-eth3": "192.168.30.1",   # RPi-Camera
    "br0-eth4": "192.168.30.2",   # ESP8266-RFID
    "br0-eth5": "192.168.30.3",   # ESP8266-ENV
}


def _get_bytes(intf: str):
    try:
        with open(f"/sys/class/net/{intf}/statistics/tx_bytes") as f:
            tx = int(f.read())
        with open(f"/sys/class/net/{intf}/statistics/rx_bytes") as f:
            rx = int(f.read())
        return tx, rx
    except Exception:
        return 0, 0


def write_points(points: list):
    try:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
    except Exception as e:
        print(f"[influx] write error: {e}")


def collect():
    state   = read_state()
    blocked = set(state.get("blocked", []))
    hosts   = state.get("hosts", {})
    points  = []
    now     = time.time_ns()

    # -- 1. Host status, QoS ------------------------------------------
    for ip, info in HOST_INFO.items():
        if ip in ("OVS-SWITCH", "AP-RPI"):
            continue
        if not ip.startswith("192.168"):
            continue

        name      = info["name"]
        vlan      = HOST_VLAN.get(ip, 0)
        vlan_name = VLAN_NAMES.get(vlan, "unknown")
        dev_type  = info.get("type", "unknown")
        sensors   = ",".join(info.get("sensors", []))

        if ip in blocked:
            status_val, status_str = -1, "blocked"
        elif hosts.get(ip, {}).get("status") == "online":
            status_val, status_str = 1, "online"
        else:
            status_val, status_str = 0, "offline"

        points.append(
            Point("host_status")
            .tag("host_ip",     ip)
            .tag("host_name",   name)
            .tag("vlan",        str(vlan))
            .tag("vlan_name",   vlan_name)
            .tag("device_type", dev_type)
            .tag("sensors",     sensors)
            .field("status",     status_val)
            .field("status_str", status_str)
            .time(now, WritePrecision.NS)
        )

        q_id    = HOST_QOS.get(ip, {}).get("queue", 3)
        q_level = HOST_QOS.get(ip, {}).get("level", "NORMAL")
        points.append(
            Point("qos_queue")
            .tag("host_ip",   ip)
            .tag("host_name", name)
            .tag("level",     q_level)
            .field("queue_id", q_id)
            .time(now, WritePrecision.NS)
        )

    # -- 2. Bandwidth --------------------------------------------------
    for intf, ip in INTF_TO_IP.items():
        tx, rx = _get_bytes(intf)
        if intf in _prev_bytes:
            ptx, prx = _prev_bytes[intf]
            mbps_tx  = max(0, tx - ptx) / 10 / 125000
            mbps_rx  = max(0, rx - prx) / 10 / 125000
            name     = HOST_INFO.get(ip, {}).get("name", ip)
            vlan     = HOST_VLAN.get(ip, 0)
            points.append(
                Point("bandwidth")
                .tag("host_ip",   ip)
                .tag("host_name", name)
                .tag("vlan",      str(vlan))
                .field("tx_mbps", round(mbps_tx, 4))
                .field("rx_mbps", round(mbps_rx, 4))
                .time(now, WritePrecision.NS)
            )
        _prev_bytes[intf] = (tx, rx)

    # -- 3. Switch status ----------------------------------------------
    for dpid, status in state.get("switches", {}).items():
        points.append(
            Point("switch_status")
            .tag("dpid", dpid)
            .field("online", 1 if status == "online" else 0)
            .time(now, WritePrecision.NS)
        )

    # -- 4. AI alerts --------------------------------------------------
    for alert in state.get("alerts", []):
        aid = f"{alert.get('timestamp','')}_{alert.get('type','')}"
        if aid in _seen_alerts:
            continue
        _seen_alerts.add(aid)
        atype = alert.get("type", "UNKNOWN")
        sev   = alert.get("severity", "MEDIUM")
        _alert_counts[atype] = _alert_counts.get(atype, 0) + 1
        points.append(
            Point("ai_alert")
            .tag("alert_type", atype)
            .tag("severity",   sev)
            .field("count",      1)
            .field("message",    str(alert.get("message", ""))[:255])
            .field("cumulative", _alert_counts[atype])
            .time(now, WritePrecision.NS)
        )

    # -- 5. Sensor data MQTT SmartGuard --------------------------------
    mqtt_data = state.get("mqtt_data", {})

    # ESP8266-DHT (smartguard/env)
    env_data = mqtt_data.get("env", {})
    if env_data:
        p = (
            Point("env_sensor")
            .tag("device_ip",   "192.168.1.36")
            .tag("device_name", "ESP8266-DHT")
            .tag("topic",       "smartguard/env")
        )
        if "temperature" in env_data:
            p = p.field("temperature", float(env_data["temperature"]))
        if "humidity" in env_data:
            p = p.field("humidity", float(env_data["humidity"]))
        points.append(p.time(now, WritePrecision.NS))

    # ESP8266-RFID (smartguard/rfid)
    rfid_data = mqtt_data.get("rfid", {})
    if rfid_data:
        status_val = 1 if rfid_data.get("status") == "GRANTED" else 0
        p = (
            Point("rfid_events")
            .tag("device_ip",   "192.168.1.37")
            .tag("device_name", "ESP8266-RFID")
            .tag("topic",       "smartguard/rfid")
            .tag("uid",         str(rfid_data.get("uid", "")))
            .tag("status",      str(rfid_data.get("status", "")))
            .field("access_granted", status_val)
            .field("access_count",   len(mqtt_data.get("access_log", [])))
        )
        points.append(p.time(now, WritePrecision.NS))

    # LED states
    leds = mqtt_data.get("leds", {})
    if leds:
        p = (
            Point("led_states")
            .tag("device_ip", "192.168.1.36")
            .field("led_temp", 1 if leds.get("led_temp") == "ON" else 0)
            .field("led_hum",  1 if leds.get("led_hum")  == "ON" else 0)
        )
        points.append(p.time(now, WritePrecision.NS))

    # -- 6. VLAN stats -------------------------------------------------
    vlan_counts      = {10: 0, 20: 0, 30: 0}
    blocked_per_vlan = {10: 0, 20: 0, 30: 0}
    for ip, hdata in hosts.items():
        v = HOST_VLAN.get(ip, 0)
        if v in vlan_counts:
            vlan_counts[v] += 1
        if ip in blocked and v in blocked_per_vlan:
            blocked_per_vlan[v] += 1

    for vlan_id, cnt in vlan_counts.items():
        points.append(
            Point("vlan_stats")
            .tag("vlan_id",   str(vlan_id))
            .tag("vlan_name", VLAN_NAMES.get(vlan_id, ""))
            .field("active_hosts",  cnt)
            .field("blocked_hosts", blocked_per_vlan.get(vlan_id, 0))
            .time(now, WritePrecision.NS)
        )

    # -- 7. VLAN policy state ------------------------------------------
    vlans = [10, 20, 30]
    for sv in vlans:
        for dv in vlans:
            if sv == dv:
                continue
            pol_str = get_vlan_policy(state, sv, dv)
            pol_val = 1 if pol_str == "allow" else 0
            points.append(
                Point("vlan_policy")
                .tag("src_vlan", str(sv))
                .tag("dst_vlan", str(dv))
                .field("policy",     pol_val)
                .field("policy_str", pol_str)
                .time(now, WritePrecision.NS)
            )

    if points:
        write_points(points)
        print(f"[influx] wrote {len(points)} points -- {time.strftime('%H:%M:%S')}")


def main():
    print(f"[influx] Connecting to {INFLUX_URL} ...")
    try:
        health = client.ping()
        print(f"[influx] InfluxDB reachable: {health}")
    except Exception as e:
        print(f"[influx] WARNING: InfluxDB not reachable: {e}")
        print("[influx] Will retry every 10s...")

    while True:
        try:
            collect()
        except Exception as e:
            print(f"[influx] collect error: {e}")
        time.sleep(10)


if __name__ == "__main__":
    main()
