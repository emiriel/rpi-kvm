# Raspberry Pi Configuration

## Supported Models

- Raspberry Pi 3 Model B/B+
- Raspberry Pi 4 Model B
- Raspberry Pi 5
- Raspberry Pi Zero W/2W (limited performance)

## Requirements

- Bluetooth support (built-in or USB adapter)
- 1GB+ RAM recommended
- Raspberry Pi OS (Debian-based)

## Setup

See main [README.md](../../README.md) for installation.

## OS Configuration

### Bluetooth

Ensure BlueZ is enabled:
```bash
sudo systemctl enable bluetooth
sudo systemctl start bluetooth
```

### USB HID Access

User needs permission to access `/dev/input/*`:
```bash
sudo usermod -a -G input pi
```

## Network Reliability

A headless Pi that drops off the network is unreachable until someone
power-cycles it. rpi-kvm ships a watchdog for this:

- `scripts/network-watchdog.sh`, run every 2 minutes by
  `rpi-kvm-network-watchdog.timer` (enabled by the installer)
- Checks the default gateway; on failure it restarts the active network
  stack (NetworkManager, systemd-networkd or dhcpcd)
- If connectivity does not recover after the restart, it counts
  consecutive failures and reboots the Pi after 3 (override with
  `NW_FAILS_BEFORE_REBOOT`)

```bash
# Manual control
sudo systemctl start/stop rpi-kvm-network-watchdog.timer
journalctl -t network-watchdog
```

### Wi-Fi Power Save

If the Pi runs on Wi-Fi, power saving is the most common cause of
"no route to host" dropouts. Disable it for NetworkManager:

```bash
# /etc/NetworkManager/conf.d/wifi-powersave.conf
[connection]
wifi.powersave = 2
```

## Performance Tuning

See [troubleshooting](../troubleshooting/04-mouse-performance.md) for
mouse latency topics.
