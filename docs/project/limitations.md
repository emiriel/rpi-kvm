# Known Limitations

Current limitations and constraints of rpi-kvm.

## Bluetooth Limitations

### Range
- ~10m typical (depends on environment)
- Walls/obstacles reduce range
- Class 2 Bluetooth (standard range)

### Latency
- 10-30ms typical input lag
- Higher under load or interference
- Not suitable for gaming/real-time apps

### Bandwidth
- HID profile: low bandwidth
- Mouse high-frequency polling limited
- Audio would require separate profile

## Hardware Constraints

### Connected Hosts
- Bluetooth limit: ~7 active connections
- Practical: 3-4 hosts recommended
- More hosts = slower switching

### Input Devices
- USB HID keyboards/mice only
- Complex gaming peripherals may not work
- Multi-device receivers (Logitech Unifying) limited support

### Raspberry Pi
- CPU-bound for many clients
- Pi Zero: 1-2 hosts max
- Pi 3/4: 3-4 hosts recommended
- Pi 5: Best performance

## Protocol Limitations

### HID Profile
- One-way communication only (host can't send to device)
- No force feedback
- No RGB control
- Basic keyboard/mouse only

### Operating Systems
- Works best with Linux/macOS
- Windows Bluetooth stack quirks
- Mobile OS limited HID support
- BIOS/UEFI access not possible (pre-boot)

## Software Limitations

### Security
- Relies on Bluetooth pairing security
- No end-to-end encryption for clipboard
- Web UI has no authentication (local network only)

### Clipboard
- Text only (no images/rich content)
- Size limits
- Sync delays

### Hotkeys
- Host OS may intercept first
- Some key combinations reserved by OS
- Limited to standard HID keycodes

## Future Improvements

Many limitations can be addressed:
- See [Next Steps](next-steps.md) for roadmap
- Contribute solutions!

## Workarounds

### Gaming/Low Latency
- Use wired keyboard/mouse for gaming host
- Switch non-gaming tasks to rpi-kvm

### Pre-boot Access
- Keep USB keyboard/mouse dongle for BIOS
- Or use separate cable-based KVM

### Rich Clipboard
- Use network file sharing
- Or cloud clipboard (Dropbox, etc.)

### Security
- Run web UI on localhost only
- Use VPN for remote access
- Implement authentication (contribution welcome!)
