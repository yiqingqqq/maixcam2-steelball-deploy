#!/usr/bin/env bash
#
# Sync recorded videos from MaixCAM to Mac ~/Desktop/
#

DEST_DIR="$HOME/Desktop"
WIFI_IP="172.17.190.231"
MAIX_IP="${1:-$WIFI_IP}"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

echo "==============================================="
echo " Syncing recorded videos via Wi-Fi -> Mac ~/Desktop/"
echo " Target Device Wi-Fi IP: ${MAIX_IP}"
echo " Local Desktop:          ${DEST_DIR}"
echo "==============================================="

# Ensure Mac ~/Desktop directory exists
mkdir -p "${DEST_DIR}"

echo "Downloading recorded videos from MaixCAM..."
scp ${SSH_OPTS} -r "root@${MAIX_IP}:/root/recordings/*" "${DEST_DIR}/"

echo "==============================================="
echo " Sync completed! Check videos on your Mac ~/Desktop/"
echo "==============================================="
