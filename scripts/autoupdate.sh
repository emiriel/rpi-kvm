#!/bin/bash
# Self-update for rpi-kvm: poll origin, deploy when the tracked branch moved.
#
# Runs periodically (rpi-kvm-autoupdate.timer). The Pi initiates the
# connection, so no port forwarding, no exposed services and no secrets
# are required — public repositories fetch anonymously over HTTPS.
# This replaces the previous webhook receiver.

set -eu

PROJECT_PATH="${PROJECT_PATH:-/root/tools/rpi-kvm}"
BRANCH="${AUTOPDATE_BRANCH:-main}"
SERVICES="${SERVICES:-rpi-kvm-core rpi-kvm-web rpi-kvm-infohub rpi-kvm-touchphat}"
LOG_TAG="autoupdate"

cd "$PROJECT_PATH"

git fetch origin

local_ref="$(git rev-parse HEAD)"
remote_ref="$(git rev-parse "origin/$BRANCH")"

if [ "$local_ref" = "$remote_ref" ]; then
    exit 0
fi

logger -t "$LOG_TAG" "update detected: $local_ref -> $remote_ref ($BRANCH)"

git reset --hard "origin/$BRANCH"

# scripts/install.sh substitutes __INSTALL_DIR__ in the deployed tree; the
# reset above restored the placeholder in web.py, so re-apply it here.
sed -i "s|__INSTALL_DIR__|$PROJECT_PATH|g" "$PROJECT_PATH/rpi_kvm/web.py"

systemctl restart $SERVICES

logger -t "$LOG_TAG" "deployed $(git rev-parse HEAD) and restarted: $SERVICES"
