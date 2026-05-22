# Common Issues

Quick solutions to frequent problems.

## Bluetooth Connection Issues

### Symptom: Hosts won't auto-connect

**Solution**: See [Auto-Connect Troubleshooting](01-bt-autoconnect-and-incoming.md)

**Quick Fix**:
1. Check BlueZ service: `systemctl status bluetooth`
2. Verify pairing: `bluetoothctl paired-devices`
3. Check logs: `journalctl -u rpi-kvm-core -f`

### Symptom: Connection drops frequently

**Possible Causes**:
- Bluetooth interference (WiFi on 2.4GHz)
- Distance/obstacles
- Power supply issues

**Solutions**:
- Use 5GHz WiFi or Ethernet
- Move RPi closer to hosts
- Use quality power supply (2.5A+ for Pi 3/4)

## Performance Issues

### Symptom: Mouse lag

See [Mouse Performance](04-mouse-performance.md) for detailed analysis.

**Quick Checks**:
- Bluetooth signal strength
- CPU usage on RPi
- USB hub quality (if using hub)

### Symptom: Keyboard delay

**Possible Causes**:
- Bluetooth latency
- CPU overload
- Input buffering

**Solutions**:
- Check system load: `top`
- Reduce logging verbosity
- Ensure adequate power

## Service Issues

### Symptom: Service won't start

```bash
# Check status
sudo systemctl status rpi-kvm-core

# View logs
journalctl -u rpi-kvm-core -n 50

# Restart
sudo systemctl restart rpi-kvm-core
```

### Symptom: Web UI unreachable

**Checks**:
1. Service running: `systemctl is-active rpi-kvm-core`
2. Port listening: `netstat -tln | grep 8080`
3. Firewall rules: `sudo iptables -L`

**Default URL**: `http://raspberrypi:8080`

## Host-Specific Issues

### Windows

- Bluetooth drivers may need updates
- Some laptops require manual pairing
- Windows may disconnect idle devices

### macOS

- May require "Allow Bluetooth devices to wake computer"
- System Preferences → Bluetooth → Advanced

### Linux

- BlueZ version differences
- Some distros auto-disconnect HID devices
- Check `bluetoothd` configuration

## Hardware Issues

### USB Devices Not Detected

```bash
# List input devices
ls -la /dev/input/by-id/

# Check permissions
groups pi
# Should include 'input'
```

### Display Issues (LCD/Touch pHAT)

**LCD not working**: See [LCD Setup](../hardware/lcd.md)

**Touch pHAT not detected**:
```bash
i2cdetect -y 1
# Should show device
```

## Getting Help

If issue persists:

1. Check [troubleshooting docs](.)
2. Search [GitHub Issues](https://github.com/BLeeEZ/rpi-kvm/issues)
3. Create new issue with:
   - System info (`uname -a`, Pi model)
   - Logs (`journalctl -u rpi-kvm-core`)
   - Steps to reproduce
