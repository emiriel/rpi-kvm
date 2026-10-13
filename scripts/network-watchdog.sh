#!/bin/bash
# Network watchdog for the Raspberry Pi.
# Runs periodically (see rpi-kvm-network-watchdog.timer): verifies
# connectivity against the default gateway, restarts the network stack
# when it drops, and reboots the Pi if the restart does not recover it.

set -u

FAILS_BEFORE_REBOOT="${NW_FAILS_BEFORE_REBOOT:-3}"
STATE_FILE="/run/network-watchdog.state"  # tmpfs: counter resets on boot
LOG_TAG="network-watchdog"

check_connectivity() {
    local gateway
    gateway=$(ip route 2>/dev/null | awk '/^default/ {print $3; exit}')
    [ -n "$gateway" ] || return 1
    ping -c 1 -W 5 "$gateway" >/dev/null 2>&1
}

restart_network() {
    # Detect the network manager actually in use on this Pi
    if systemctl is-active --quiet NetworkManager; then
        systemctl restart NetworkManager
    elif systemctl is-active --quiet systemd-networkd; then
        systemctl restart systemd-networkd
    elif systemctl is-active --quiet dhcpcd; then
        systemctl restart dhcpcd
    else
        systemctl restart networking
    fi
}

record_fails() {
    echo "$1" > "$STATE_FILE"
}

if check_connectivity; then
    record_fails 0
    exit 0
fi

# Brief grace period: transient loss recovers by itself
sleep 10
if check_connectivity; then
    record_fails 0
    exit 0
fi

logger -t "$LOG_TAG" "gateway unreachable - restarting network stack"
restart_network
sleep 30

if check_connectivity; then
    record_fails 0
    logger -t "$LOG_TAG" "network recovered after restart"
    exit 0
fi

fails=$(($(cat "$STATE_FILE" 2>/dev/null || echo 0) + 1))
record_fails "$fails"
logger -t "$LOG_TAG" "still unreachable (failure $fails/$FAILS_BEFORE_REBOOT)"

if [ "$fails" -ge "$FAILS_BEFORE_REBOOT" ]; then
    logger -t "$LOG_TAG" "network restart ineffective - rebooting"
    systemctl reboot
fi
