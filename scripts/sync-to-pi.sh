#!/bin/bash
# Shared transport used by install-from-ssh.sh and deploy_to_rpi.sh:
# stages the local working tree on the Raspberry Pi via tar over ssh
# (rsync may be absent on the dev machine), then rsyncs it into the
# remote install directory with proper deletions (rsync runs on the Pi).
# Preserves .git and runtime-generated conf state on the remote side.
# See AGENTS.md "SSH access" for the SSH setup.

set -euo pipefail

cd "$(dirname "$0")/.."

HOST="${RPI_KVM_HOST:-rpi-kvm.home}"
REMOTE_DIR="${RPI_KVM_REMOTE_DIR:-/root/tools/rpi-kvm}"
STAGE_DIR="/tmp/rpi-kvm-sync"
SSH_OPTS=(-o UserKnownHostsFile=/tmp/ssh_known_hosts)

# tar excludes what must not leave the dev machine; rsync excludes what
# must survive on the Pi (--delete would remove it otherwise).
TAR_EXCLUDES=(
    --exclude='.git'
    --exclude='__pycache__'
    --exclude='.pytest_cache'
    --exclude='.vagrant'
    --exclude='.claude'
    --exclude='.vscode'
    --exclude='web/node_modules'
    --exclude='web/coverage'
)
RSYNC_EXCLUDES=(
    --exclude '.git/'
    --exclude '__pycache__/'
    --exclude 'conf/rpi-kvm-settings.json'
    --exclude 'conf/rpi-kvm-client-order.json'
    --exclude 'conf/bluetooth.service.bak'
    --exclude 'deployment/'
)

echo "=== Staging working tree on $HOST:$STAGE_DIR ==="
ssh "${SSH_OPTS[@]}" "$HOST" \
    "rm -rf $STAGE_DIR && mkdir -p $STAGE_DIR && sudo mkdir -p $REMOTE_DIR"

tar czf - "${TAR_EXCLUDES[@]}" ./ \
| ssh "${SSH_OPTS[@]}" "$HOST" "tar xzf - -C $STAGE_DIR"

echo "=== Syncing $STAGE_DIR into $REMOTE_DIR (rsync on the Pi) ==="
ssh "${SSH_OPTS[@]}" "$HOST" \
    "sudo rsync -a --delete ${RSYNC_EXCLUDES[*]} $STAGE_DIR/ $REMOTE_DIR/"

echo "=== Cleaning up staging dir ==="
ssh "${SSH_OPTS[@]}" "$HOST" "sudo rm -rf $STAGE_DIR"
