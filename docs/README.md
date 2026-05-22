# rpi-kvm Documentation

Complete documentation for the Raspberry Pi KVM (Keyboard-Video-Mouse) over Bluetooth project.

## Table of Contents

### Getting Started
- [Project Overview](../README.md) - Main project README
- [Installation Guide](development/installation.md)
- [Quick Start](development/quick-start.md)

### Architecture
- [System Overview](architecture/system-overview.md)
- [Component Design](architecture/components.md)
- [Data Flow](architecture/data-flow.md)

### Bluetooth
- [Auto-Connection Explained](bluetooth/bluetooth-auto-connection.md)
- [HID Descriptors](bluetooth/hid-descriptors.md)
- [BlueZ Device1 API](bluetooth/bluez-device1-example.md)
- [References & Resources](bluetooth/references.md)

### Hardware
- [LCD Display Setup](hardware/lcd.md)
- [Raspberry Pi Configuration](hardware/raspberry-pi.md)
- [Touch pHAT Integration](hardware/touch-phat.md)

### Development
- [Testing Setup](development/testing-setup.md)
- [Contributing Guidelines](development/contributing.md)
- [Code Style](development/code-style.md)

### Troubleshooting
- [Common Issues](troubleshooting/common-issues.md)
- [Bluetooth Auto-Connect Issues](troubleshooting/01-bt-autoconnect-and-incoming.md)
- [Auto-Switch Problems](troubleshooting/02-autoswitch.md)
- [Offline Host Switching](troubleshooting/03-pihat-switches-to-offline-hosts.md)
- [Mouse Performance](troubleshooting/04-mouse-performance.md)

### Project Management
- [Next Steps & Roadmap](project/next-steps.md)
- [Feature Ideas](project/feature-ideas.md)
- [Known Limitations](project/limitations.md)

## Quick Links

- **Setting up tests?** → [Testing Setup](development/testing-setup.md)
- **Bluetooth not connecting?** → [Auto-Connection Guide](bluetooth/bluetooth-auto-connection.md)
- **Want to contribute?** → [Contributing](development/contributing.md)
- **Hardware setup?** → [Hardware Docs](hardware/)

## Documentation Structure

```
docs/
├── README.md                    # This file
├── architecture/                # System design and architecture
├── bluetooth/                   # Bluetooth protocol documentation
├── hardware/                    # Hardware setup guides
├── development/                 # Development and testing
├── troubleshooting/             # Known issues and fixes
└── project/                     # Project management
```

## Contributing to Documentation

Documentation improvements are welcome! Please:
1. Keep docs up to date with code changes
2. Use clear, concise language
3. Include code examples where helpful
4. Add diagrams for complex concepts
5. Test all commands and instructions

See [Contributing Guidelines](development/contributing.md) for details.
