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

## Performance Tuning

Coming soon.
