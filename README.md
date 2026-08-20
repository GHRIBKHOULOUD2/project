# Digital Twin — Complete Recovery Guide
## PC: 192.168.1.100 | OVS: 192.168.1.10 | AP: 192.168.1.20

---

## Step 1 — Fresh Ubuntu/Debian install on PC

```bash
# Update system
sudo apt update && sudo apt upgrade -y
```

---

## Step 2 — Run the installation script

```bash
# Copy install.sh to PC then:
bash install.sh
```

This installs:
- Python 3 + venv (ryu-env)
- Ryu SDN Framework
- Flask web server
- Mosquitto MQTT broker
- InfluxDB 2.x
- Grafana
- All Python packages

---

## Step 3 — Copy project files

Copy these files to `~/digital_twin/`:

| File | Purpose |
|------|---------|
| `config.py` | All IPs, VLANs, thresholds, host info |
| `shared_state.py` | State management (JSON file) |
| `ryu_controller.py` | OpenFlow SDN controller |
| `mqtt_bridge.py` | MQTT -> state bridge |
| `metrics_influx.py` | InfluxDB metrics writer |
| `app.py` | Flask web dashboard |

```bash
mkdir -p ~/digital_twin
cp *.py ~/digital_twin/
cp startup.sh ~/digital_twin/
```

---

## Step 4 — Network configuration (after every reboot)

### On OVS (ssh khouloud@192.168.1.10):
```bash
sudo ip route del 192.168.1.20 dev eth0 2>/dev/null || true
sudo ip route add 192.168.1.20 dev br0 metric 50 2>/dev/null || true
sudo ip route add 192.168.1.1 via 192.168.1.20 dev br0 metric 10 2>/dev/null || true
sudo ip route add default via 192.168.1.20 dev br0 metric 50 2>/dev/null || true
sudo sysctl -w net.ipv4.conf.all.send_redirects=0
```

### On AP (ssh maissara@192.168.1.20):
```bash
sudo sysctl -w net.ipv4.ip_forward=1
sudo ip route add 192.168.1.11 dev eth0 scope link 2>/dev/null || true
sudo ip route add 192.168.1.10 via 192.168.1.11 dev eth0 metric 10 2>/dev/null || true
sudo ip route add 192.168.1.100 via 192.168.1.11 dev eth0 metric 10 2>/dev/null || true
sudo ip route add 192.168.1.1 dev eth1 src 192.168.1.33 metric 5 2>/dev/null || true
```

### On PC:
```bash
sudo ip route add 192.168.1.1 via 192.168.1.10 dev eno1 metric 10 2>/dev/null || true
```

---

## Step 5 — Start everything

```bash
source ~/ryu-env/bin/activate
cd ~/digital_twin
bash startup.sh
```

Or start individually in separate terminals:

```bash
# Terminal 1 — Ryu controller
source ~/ryu-env/bin/activate
cd ~/digital_twin
ryu-manager ryu_controller.py --ofp-tcp-listen-port 6633

# Terminal 2 — MQTT bridge
source ~/ryu-env/bin/activate
cd ~/digital_twin
python3 mqtt_bridge.py

# Terminal 3 — InfluxDB metrics
source ~/ryu-env/bin/activate
cd ~/digital_twin
python3 metrics_influx.py

# Terminal 4 — Flask dashboard
source ~/ryu-env/bin/activate
cd ~/digital_twin
python3 app.py
```

---

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Dashboard | http://localhost:5000 | — |
| Grafana | http://localhost:3000 | admin/admin |
| InfluxDB | http://localhost:8086 | admin/Admin1234! |
| State JSON | http://localhost:5000/api/twin | — |

---

## Network Topology

```
INTERNET
    |
MODEM (192.168.1.1)
    | eth1: 192.168.1.33
RPi-AP (192.168.1.20)  [NAT + Forwarding]
    | eth0 <--cable--> eth1
RPi-OVS  eth0:192.168.1.10  br0:192.168.1.11
    | eth0
PC (192.168.1.100)  [Ryu Controller :6633]
```

---

## Physical Cable Order

1. OVS eth1 <-> AP eth0  (must be plugged FIRST)
2. OVS eth0 <-> PC eno1
3. AP eth1  <-> Modem LAN port

---

## MAC Addresses (current boards)

| Device | Interface | MAC |
|--------|-----------|-----|
| RPi-OVS | eth0 | b8:27:eb:63:51:8a |
| RPi-OVS | eth1/br0 | 00:e8:00:36:f2:e8 |
| RPi-AP | eth0 | b8:27:eb:41:58:ff |

---

## InfluxDB Token

```
Token: MyInfluxToken123
Org:   nettwin
Bucket: digital_twin
```

---

## Common Problems

### OVS can't ping AP
```bash
sudo ip route add 192.168.1.20 dev br0 metric 50
```

### AP not forwarding (ip_forward=0)
```bash
sudo sysctl -w net.ipv4.ip_forward=1
```

### Flask template error (Jinja2 elif)
Remove any `{# comment #}` lines between `{% if %}` / `{% elif %}` blocks.

### influxdb_client not found
```bash
pip install influxdb-client
```

### paho-mqtt not found
```bash
pip install paho-mqtt
```
