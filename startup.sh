#!/bin/bash
# =============================================================
# startup.sh — Run this after every reboot on PC
# Usage: bash ~/digital_twin/startup.sh
# =============================================================

echo "=============================="
echo " NetTwin — Startup Script"
echo "=============================="

# ── 1. Network routes ─────────────────────────────────────────
echo "[1/5] Applying network routes..."
sudo ip route add 192.168.1.1  via 192.168.1.10 dev eno1 metric 10 2>/dev/null || true
sudo ip route add 192.168.1.20 via 192.168.1.11 dev eno1 metric 10 2>/dev/null || true
echo "  Routes OK"

# ── 2. Services check ─────────────────────────────────────────
echo "[2/5] Checking services..."
sudo systemctl start influxdb   2>/dev/null && echo "  InfluxDB OK"   || echo "  InfluxDB FAILED"
sudo systemctl start mosquitto  2>/dev/null && echo "  Mosquitto OK"  || echo "  Mosquitto FAILED"
sudo systemctl start grafana-server 2>/dev/null && echo "  Grafana OK" || echo "  Grafana FAILED"

# ── 3. Activate Python env ────────────────────────────────────
echo "[3/5] Activating Python environment..."
source ~/ryu-env39/bin/activate
echo "  Python env: $(which python3)"

# ── 4. Start Digital Twin services ───────────────────────────
echo "[4/5] Starting Digital Twin services..."
cd ~/digital_twin

# Start Ryu controller
echo "  Starting Ryu controller..."
ryu-manager ryu_controller.py --ofp-tcp-listen-port 6633 &
RYU_PID=$!
echo "  Ryu PID: $RYU_PID"
sleep 2

# Start MQTT bridge
echo "  Starting MQTT bridge..."
python3 mqtt_bridge.py &
MQTT_PID=$!
echo "  MQTT bridge PID: $MQTT_PID"

# Start InfluxDB metrics writer
echo "  Starting InfluxDB metrics writer..."
python3 metrics_influx.py &
INFLUX_PID=$!
echo "  InfluxDB writer PID: $INFLUX_PID"

# Start Flask dashboard
echo "  Starting Flask dashboard..."
python3 app.py &
FLASK_PID=$!
echo "  Flask PID: $FLASK_PID"

# ── 5. Done ───────────────────────────────────────────────────
echo ""
echo "[5/5] All services started!"
echo "=============================="
echo " Dashboard: http://localhost:5000"
echo " Grafana:   http://localhost:3000"
echo " InfluxDB:  http://localhost:8086"
echo " MQTT:      192.168.1.20:1883"
echo "=============================="
echo ""
echo "PIDs: Ryu=$RYU_PID  MQTT=$MQTT_PID  Influx=$INFLUX_PID  Flask=$FLASK_PID"
echo "To stop all: kill $RYU_PID $MQTT_PID $INFLUX_PID $FLASK_PID"

# Keep script alive and show logs
wait
