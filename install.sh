#!/bin/bash
# =============================================================
# install.sh — Full Digital Twin PC Recovery Script
# Run as: bash install.sh
# PC IP: 192.168.1.100
# =============================================================

set -e
echo "=============================================="
echo " Digital Twin — Full Installation Recovery"
echo "=============================================="

# ── 1. System packages ────────────────────────────────────────
echo "[1/8] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    git curl wget net-tools \
    mosquitto mosquitto-clients \
    iptables netfilter-persistent \
    openvswitch-switch openvswitch-common \
    nmap tcpdump \
    influxdb2 influxdb2-cli

# ── 2. InfluxDB setup ─────────────────────────────────────────
echo "[2/8] Starting InfluxDB..."
sudo systemctl enable influxdb
sudo systemctl start influxdb
sleep 3

echo "[influxdb] Setting up org/bucket/token..."
influx setup \
  --org nettwin \
  --bucket digital_twin \
  --username admin \
  --password Admin1234! \
  --token MyInfluxToken123 \
  --force 2>/dev/null || echo "[influxdb] Already configured, skipping."

# ── 3. Mosquitto MQTT broker ──────────────────────────────────
echo "[3/8] Configuring Mosquitto MQTT broker..."
sudo tee /etc/mosquitto/conf.d/nettwin.conf > /dev/null << 'EOF'
listener 1883
allow_anonymous true
EOF
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto
echo "[mqtt] Broker running on port 1883"

# ── 4. Grafana ────────────────────────────────────────────────
echo "[4/8] Installing Grafana..."
if ! command -v grafana-server &>/dev/null; then
    sudo apt-get install -y apt-transport-https software-properties-common
    wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
    echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
    sudo apt-get update -qq
    sudo apt-get install -y grafana
fi
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
echo "[grafana] Running on http://localhost:3000 (admin/admin)"

# ── 5. Python virtual environment ────────────────────────────
echo "[5/8] Creating Python virtual environment..."
cd ~
python3 -m venv ryu-env
source ~/ryu-env/bin/activate

pip install --upgrade pip -q
pip install -q \
    ryu \
    flask \
    paho-mqtt \
    influxdb-client \
    scikit-learn \
    numpy \
    pandas \
    eventlet \
    flask-socketio

echo "[python] All packages installed in ~/ryu-env"

# ── 6. Digital Twin project folder ───────────────────────────
echo "[6/8] Creating project structure..."
mkdir -p ~/digital_twin
cd ~/digital_twin

# ── 7. Network routes (run after every reboot) ───────────────
echo "[7/8] Applying network routes..."
sudo ip route add 192.168.1.1 via 192.168.1.10 dev eno1 metric 10 2>/dev/null || true
sudo ip route add 192.168.1.20 via 192.168.1.11 dev eno1 metric 10 2>/dev/null || true
echo "[network] Routes applied"

# ── 8. Done ───────────────────────────────────────────────────
echo ""
echo "=============================================="
echo " Installation Complete!"
echo "=============================================="
echo " Grafana:   http://localhost:3000  (admin/admin)"
echo " InfluxDB:  http://localhost:8086  (admin/Admin1234!)"
echo " MQTT:      localhost:1883"
echo " Python env: source ~/ryu-env/bin/activate"
echo " Project:    ~/digital_twin/"
echo "=============================================="
