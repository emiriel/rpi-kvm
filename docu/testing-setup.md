# Testing Setup for rpi-kvm

This document explains how to run tests for the rpi-kvm project using a virtualized Bluetooth environment.

## Why Vagrant + Virtual Bluetooth?

Testing Bluetooth code is challenging:
- Requires actual Bluetooth hardware
- Needs BlueZ daemon and D-Bus
- Hard to reproduce specific scenarios (device boot, disconnect, etc.)

**Solution**: Use Vagrant to create a VM with:
- Virtual Bluetooth controller (`hci_vhci` kernel module)
- Complete BlueZ stack
- D-Bus system bus
- Isolated test environment

## Prerequisites

Install Vagrant and VirtualBox:

```bash
# Ubuntu/Debian
sudo apt-get install vagrant virtualbox

# macOS
brew install vagrant virtualbox

# Or download from:
# https://www.vagrantup.com/downloads
# https://www.virtualbox.org/wiki/Downloads
```

## Quick Start

### 1. Start the Test VM

From project root:

```bash
vagrant up
```

First run will:
- Download Ubuntu 22.04 base image (~500MB)
- Create and configure VM
- Install BlueZ, Python, dependencies
- Load virtual Bluetooth module
- Takes ~5-10 minutes

Subsequent runs are instant (VM is cached).

### 2. Run Tests

**Easy way** (from host):
```bash
./run_tests.sh
```

**Manual way**:
```bash
vagrant ssh
cd /vagrant
python3 -m pytest tests/ -v
```

### 3. Stop the VM

```bash
vagrant halt          # Stop VM (keeps state)
vagrant destroy       # Delete VM completely
```

## Project Structure

```
rpi-kvm/
├── Vagrantfile           # VM configuration
├── .vagrantignore        # Files excluded from VM sync
├── run_tests.sh          # Test runner script
├── tests/                # Test suite
│   ├── __init__.py
│   ├── conftest.py       # pytest fixtures
│   ├── test_bt_client.py # BtClient unit tests
│   └── test_integration.py # Integration tests
└── docu/
    └── testing-setup.md  # This file
```

## How It Works

### Vagrant Configuration

The `Vagrantfile` defines:

```ruby
config.vm.box = "ubuntu/jammy64"        # Ubuntu 22.04 LTS
config.vm.synced_folder ".", "/vagrant" # Project mounted in VM
config.vm.network "forwarded_port", guest: 8080, host: 8080
```

### Virtual Bluetooth

The VM loads `hci_vhci` kernel module:
- Creates virtual Bluetooth controller
- Appears as `/dev/vhci`
- BlueZ treats it like real hardware
- Can simulate devices, connections, signals

### Test Isolation

Each test run:
- Uses clean VM state
- Mock D-Bus interactions
- Simulates BlueZ property changes
- No interference with host Bluetooth

## Writing Tests

### Unit Tests

Test individual functions with mocks:

```python
# tests/test_bt_client.py
import pytest
from unittest.mock import Mock, AsyncMock
from rpi_kvm.bt_client import BtClient

@pytest.mark.asyncio
async def test_services_resolved_triggers_reconnect():
    """When ServicesResolved=True, client should initiate HID connection"""
    client = BtClient("00:11:22:33:44:55")
    client._connect_to_dbus_service = AsyncMock()

    # Simulate ServicesResolved property change
    variant = Mock()
    variant.value = True

    client._on_properties_changed("org.bluez.Device1",
                                   {"ServicesResolved": variant},
                                   [])

    # Assert reconnect was triggered
    assert client._services_resolved == True
```

### Integration Tests

Test with simulated BlueZ interactions:

```python
# tests/test_integration.py
@pytest.mark.asyncio
async def test_full_reconnect_flow(mock_bluez):
    """Test complete reconnect flow: RSSI -> Connected -> ServicesResolved -> HID"""
    client = await BtClient.create_via_address("AA:BB:CC:DD:EE:FF")

    # Simulate device boot sequence
    mock_bluez.emit_property_change("RSSI", -50)
    await asyncio.sleep(0.1)

    mock_bluez.emit_property_change("Connected", True)
    await asyncio.sleep(0.1)

    mock_bluez.emit_property_change("ServicesResolved", True)
    await asyncio.sleep(0.5)

    # Verify HID connection established
    assert client.is_connected
```

## Debugging

### Access VM

```bash
vagrant ssh
```

Inside VM:
```bash
# Check Bluetooth status
hciconfig
systemctl status bluetooth

# Monitor D-Bus
dbus-monitor --system

# View BlueZ devices
bluetoothctl list
bluetoothctl show

# Run specific test
cd /vagrant
python3 -m pytest tests/test_bt_client.py::test_name -v -s
```

### Common Issues

**VM won't start**:
```bash
vagrant destroy -f
vagrant up
```

**Tests fail with D-Bus errors**:
```bash
vagrant ssh
sudo service dbus restart
sudo service bluetooth restart
```

**Module not found errors**:
```bash
vagrant ssh
pip3 list | grep dbus-next
# Reinstall if needed:
pip3 install --break-system-packages dbus-next pytest pytest-asyncio
```

## CI/CD Integration

For automated testing in CI (GitHub Actions, GitLab CI):

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install Vagrant
        run: sudo apt-get install -y vagrant virtualbox
      - name: Run tests
        run: ./run_tests.sh
```

## Performance

- **First run**: 5-10 min (download + provision)
- **Subsequent runs**: <30 seconds
- **Test execution**: 1-5 seconds per test
- **VM disk usage**: ~2GB

## Next Steps

1. Write comprehensive test suite
2. Add coverage reporting
3. Set up CI/CD pipeline
4. Document test scenarios

See `docu/bluetooth-auto-connection.md` for implementation details.
