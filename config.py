#!/usr/bin/env python3
# =============================================================
# config.py — Central Configuration
# PC Controller: 192.168.1.100
# =============================================================

# ── InfluxDB ──────────────────────────────────────────────────
INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = "IMsXkssxdJqnTqjCfOso-1KvtMS7y1sFFMRsVPKM1YnG3Un69fqU9m8dGuGVj21S_IIWL-LvpSQwnqdcaQmC6Q=="
INFLUX_ORG    = "nettwin"
INFLUX_BUCKET = "digital_twin"

# ── MQTT ──────────────────────────────────────────────────────
MQTT_BROKER = "192.168.1.20"   # RPi-AP runs the broker
MQTT_PORT   = 1883

# ── Flask ─────────────────────────────────────────────────────
FLASK_PORT     = 5000
CONTROLLER_IP  = "192.168.1.100"

# ── Sensor thresholds ─────────────────────────────────────────
TEMP_THRESHOLD = 28.0   # °C — LED temp ON above this
HUM_MIN        = 20.0   # % — LED hum ON below this
HUM_MAX        = 80.0   # % — LED hum ON above this

# ── RFID authorized cards ─────────────────────────────────────
RFID_AUTHORIZED = {
    "A1B2C3D4": "Khouloud",
    "11223344": "Maissara",
    "AABBCCDD": "Admin",
}

# ── VLAN definitions ──────────────────────────────────────────
VLAN_NAMES = {
    10: "IT",
    20: "WiFi",
    30: "IoT",
}

VLAN_DEFAULT_POLICY = {
    (10, 20): "deny",
    (10, 30): "deny",
    (20, 10): "deny",
    (20, 30): "deny",
    (30, 10): "deny",
    (30, 20): "deny",
}

# ── Host → VLAN mapping ───────────────────────────────────────
HOST_VLAN = {
    "192.168.1.100":  10,   # PC Controller
    "192.168.10.1":   10,   # PC-Client
    "192.168.20.1":   20,   # Phone
    "192.168.30.1":   30,   # RPi-Camera
    "192.168.1.36":   30,   # ESP8266-DHT
    "192.168.1.37":   30,   # ESP8266-RFID
}

# ── QoS queue definitions ─────────────────────────────────────
QOS_QUEUES = {
    0: {"name": "CRITICAL",  "min": "10Mbps",  "max": "100Mbps"},
    1: {"name": "HIGH",      "min": "5Mbps",   "max": "50Mbps"},
    2: {"name": "MEDIUM",    "min": "2Mbps",   "max": "20Mbps"},
    3: {"name": "NORMAL",    "min": "1Mbps",   "max": "10Mbps"},
    4: {"name": "LOW",       "min": "512Kbps", "max": "5Mbps"},
}

# ── Host → QoS mapping ───────────────────────────────────────
HOST_QOS = {
    "192.168.1.100": {"queue": 0, "level": "CRITICAL"},
    "192.168.10.1":  {"queue": 1, "level": "HIGH"},
    "192.168.20.1":  {"queue": 3, "level": "NORMAL"},
    "192.168.30.1":  {"queue": 2, "level": "MEDIUM"},
    "192.168.1.36":  {"queue": 3, "level": "NORMAL"},
    "192.168.1.37":  {"queue": 3, "level": "NORMAL"},
}

# ── Host info ─────────────────────────────────────────────────
HOST_INFO = {
    "OVS-SWITCH": {
        "name": "RPi-OVS",
        "role": "Open vSwitch / SDN Bridge",
        "type": "infrastructure",
        "sensors": [],
    },
    "AP-RPI": {
        "name": "RPi-AP",
        "role": "Access Point / NAT Gateway",
        "type": "infrastructure",
        "sensors": [],
    },
    "192.168.1.100": {
        "name": "PC-Controller",
        "role": "Ryu SDN Controller / Flask Dashboard",
        "type": "controller",
        "sensors": [],
    },
    "192.168.10.1": {
        "name": "PC-Client",
        "role": "Client workstation VLAN 10",
        "type": "workstation",
        "sensors": [],
    },
    "192.168.20.1": {
        "name": "Phone",
        "role": "WiFi device VLAN 20",
        "type": "mobile",
        "sensors": [],
    },
    "192.168.30.1": {
        "name": "RPi-Camera",
        "role": "IP Camera / IoT VLAN 30",
        "type": "camera",
        "sensors": ["camera"],
    },
    "192.168.1.36": {
        "name": "ESP8266-DHT",
        "role": "Temperature & Humidity sensor",
        "type": "iot",
        "sensors": ["temperature", "humidity"],
    },
    "192.168.1.37": {
        "name": "ESP8266-RFID",
        "role": "RFID Access control",
        "type": "iot",
        "sensors": ["rfid"],
    },
}
