#!/bin/bash
# Install rpi-kvm on the Raspberry Pi from this machine's working tree,
# without GitHub: sync the tree via ssh (scripts/sync-to-pi.sh), then run
# the common on-Pi installer (scripts/install.sh) remotely.
# The git alternative is scripts/install-from-git.sh, run on the Pi
# itself inside a git checkout.

set -euo pipefail

cd "$(dirname "$0")/.."

HOST="${RPI_KVM_HOST:-rpi-kvm.home}"
REMOTE_DIR="${RPI_KVM_REMOTE_DIR:-/root/tools/rpi-kvm}"
SSH_OPTS=(-o UserKnownHostsFile=/tmp/ssh_known_hosts)

./scripts/sync-to-pi.sh

# REMOTE_DIR is under /root on the Pi: the cd must run under sudo too.
echo "=== Running installer on $HOST ($REMOTE_DIR) ==="
ssh "${SSH_OPTS[@]}" "$HOST" \
    "sudo bash -c 'cd $REMOTE_DIR && bash ./scripts/install.sh'"

echo ""
echo "=== Install from ssh complete ==="
ssh "${SSH_OPTS[@]}" "$HOST" \
    "systemctl list-units 'rpi-kvm*' --no-pager --no-legend"
