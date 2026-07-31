#!/usr/bin/env bash
#
# Deploy maix_project to MaixCAM and configure Linux autostart (Option 1)
#

DEFAULT_IP="maixcam.local"
MAIX_IP="${1:-$DEFAULT_IP}"
PROJECT_DIR="$(cd "$(dirname "$0")/../maix_project" && pwd)"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

echo "==================================================="
echo " Deploying maix_project -> MaixCAM (${MAIX_IP})"
echo " Local project dir: ${PROJECT_DIR}"
echo "==================================================="

if [ ! -d "${PROJECT_DIR}" ]; then
    echo "[ERROR] Local directory ${PROJECT_DIR} does not exist!"
    exit 1
fi

echo "[1/2] Uploading maix_project to /root/maix_project on MaixCAM..."
scp ${SSH_OPTS} -r "${PROJECT_DIR}" "root@${MAIX_IP}:/root/"

if [ $? -ne 0 ]; then
    echo "[ERROR] SCP upload failed! Check USB/Wi-Fi connection to ${MAIX_IP}."
    exit 1
fi

echo "[2/2] Configuring Linux autostart script on MaixCAM..."
ssh ${SSH_OPTS} "root@${MAIX_IP}" bash -s << 'EOF'
AUTOSTART_FILE=""
if [ -f "/maixapp/startup.sh" ]; then
    AUTOSTART_FILE="/maixapp/startup.sh"
elif [ -f "/etc/rc.local" ]; then
    AUTOSTART_FILE="/etc/rc.local"
else
    AUTOSTART_FILE="/etc/init.d/S99maixapp"
fi

echo "[REMOTE] Autostart script location: ${AUTOSTART_FILE}"

# Update autostart entry with sleep 3 delay to allow hardware drivers to initialize on boot
sed -i '/maix_project\/main.py/d' "${AUTOSTART_FILE}" 2>/dev/null
echo "" >> "${AUTOSTART_FILE}"
echo "# MaixCAM steelball autostart" >> "${AUTOSTART_FILE}"
echo "export LD_LIBRARY_PATH=/opt/usr/lib:/opt/lib:/maixapp/lib:/usr/local/lib:/lib:/usr/lib:\$LD_LIBRARY_PATH" >> "${AUTOSTART_FILE}"
echo "(export LD_LIBRARY_PATH=/opt/usr/lib:/opt/lib:/maixapp/lib:/usr/local/lib:/lib:/usr/lib:\$LD_LIBRARY_PATH && sleep 3 && cd /root/maix_project && python3 main.py > /root/app.log 2>&1) &" >> "${AUTOSTART_FILE}"
echo "[REMOTE] Successfully configured autostart with 3s boot delay in ${AUTOSTART_FILE}."
EOF

echo "==================================================="
echo " Deployment completed successfully!"
echo " MaixCAM is now configured to launch maix_project on boot."
echo "==================================================="
