#!/bin/bash
# Automated deployment script called by webhook receiver.
# PROD deployment: the Pi tree is a git checkout of origin/main and this
# script resets it to the pushed state. The debug alternative is
# deploy_to_rpi.sh from the dev machine (direct ssh sync, no GitHub).

set -e

PROJECT_PATH="${PROJECT_PATH:-/root/tools/rpi-kvm}"
SERVICES="${SERVICES:-rpi-kvm-core rpi-kvm-web rpi-kvm-infohub rpi-kvm-touchphat}"

echo "=== Starting deployment at $(date) ==="

cd "$PROJECT_PATH"

echo "Pulling latest changes..."
git fetch origin
git reset --hard origin/main

echo "Current state:"
git log --oneline -3

# scripts/install.sh substitutes __INSTALL_DIR__ in the deployed tree; the
# reset above restored the placeholder in web.py, so re-apply it here.
echo "Re-applying __INSTALL_DIR__ substitution in web.py"
sed -i "s|__INSTALL_DIR__|$PROJECT_PATH|g" $PROJECT_PATH/rpi_kvm/web.py

echo "Restarting services: $SERVICES"
systemctl restart $SERVICES

# Wait for services to start
sleep 2

echo "Service status:"
systemctl list-units 'rpi-kvm*' --no-pager --no-legend

echo "=== Deployment completed at $(date) ==="
