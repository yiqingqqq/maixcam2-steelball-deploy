#!/usr/bin/env bash
#
# Deploy & Start Web Streaming Mode on MaixCAM (WITHOUT autostart)
#

DEFAULT_IP="maixcam.local"
MAIX_IP="${1:-$DEFAULT_IP}"
PROJECT_DIR="$(cd "$(dirname "$0")/../maix_project" && pwd)"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

echo "==================================================="
echo " Deploying & Running Web Stream Mode -> MaixCAM (${MAIX_IP})"
echo " Local project dir: ${PROJECT_DIR}"
echo " Note: Boot autostart is DISABLED as requested."
echo "==================================================="

# 1. Ensure target directory exists on MaixCAM
ssh ${SSH_OPTS} "root@${MAIX_IP}" "mkdir -p /root/maix_project /root/recordings" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[ERROR] Cannot connect to MaixCAM at ${MAIX_IP}. Check Wi-Fi / Hotspot / USB connection."
    exit 1
fi

# 2. Upload project code
echo "[1/3] Uploading maix_project to /root/maix_project on MaixCAM..."
scp ${SSH_OPTS} -r "${PROJECT_DIR}/"* "root@${MAIX_IP}:/root/maix_project/"
if [ $? -ne 0 ]; then
    echo "[ERROR] SCP upload failed!"
    exit 1
fi

# 3. Clean up any autostart entries in /etc/rc.local (Ensuring NO autostart)
echo "[2/3] Cleaning up autostart entries to ensure manual Web mode only..."
ssh ${SSH_OPTS} "root@${MAIX_IP}" "sed -i '/maix_project\/main.py/d' /etc/rc.local 2>/dev/null; sed -i '/MaixCAM steelball/d' /etc/rc.local 2>/dev/null"

# 4. Kill old processes and launch main.py with Web Server
echo "[3/3] Launching Python detection & Web Server in background..."
ssh ${SSH_OPTS} "root@${MAIX_IP}" "killall -9 python3 2>/dev/null; pkill -9 maixapp 2>/dev/null; sleep 1; cd /root/maix_project && export LD_LIBRARY_PATH=/opt/usr/lib:/opt/lib:/maixapp/lib:/usr/local/lib:\$LD_LIBRARY_PATH && python3 main.py > /root/app.log 2>&1 &"

sleep 3

echo "==================================================="
echo " 🎉 Web Stream Mode Successfully Launched!"
echo " Open your browser on Mac/Phone to view live stream & telemetry:"
echo " 👉 http://${MAIX_IP}:8080"
echo " 👉 http://maixcam.local:8080"
echo "==================================================="
