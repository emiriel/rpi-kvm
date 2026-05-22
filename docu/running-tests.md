# Running Tests

Guide to running rpi-kvm test suite.

## Test Types

### Unit Tests (Fast, No Dependencies)

Mock-based tests, run anywhere:

```bash
python3 -m pytest tests/test_bt_client.py -v
```

**Coverage**: 16 tests covering BtClient logic
**Runtime**: ~50ms
**Requirements**: Python 3.7+, pytest

### Integration Tests (Requires BlueZ)

Tests with real D-Bus and BlueZ:

```bash
python3 -m pytest tests/test_bt_integration.py -v -m integration
```

**Coverage**: D-Bus connection, BlueZ adapter detection
**Runtime**: ~2-5s
**Requirements**: BlueZ daemon running, D-Bus system bus

## Setup Methods

### Method 1: Vagrant VM (Recommended)

Isolated test environment with virtual Bluetooth:

```bash
# Install Vagrant + VirtualBox
sudo apt-get install vagrant virtualbox  # Ubuntu/Debian
# or brew install vagrant virtualbox     # macOS

# Start VM (first run downloads Ubuntu image, ~5-10min)
vagrant up

# SSH into VM
vagrant ssh

# Run tests
cd /vagrant
python3 -m pytest tests/ -v

# Run only unit tests
python3 -m pytest tests/test_bt_client.py -v

# Run only integration tests
python3 -m pytest tests/test_bt_integration.py -v -m integration

# Stop VM
exit
vagrant halt
```

**VM includes**:
- Ubuntu 22.04
- BlueZ + D-Bus
- vhci kernel module (virtual Bluetooth)
- All Python dependencies

### Method 2: Local System

Run on host machine (affects real Bluetooth):

```bash
# Install dependencies
pip3 install pytest pytest-asyncio dbus-next evdev aiohttp

# Ensure BlueZ running
systemctl status bluetooth

# Run tests
python3 -m pytest tests/ -v
```

**Caution**: Integration tests interact with system BlueZ.

### Method 3: CI/CD

GitHub Actions example:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y bluez dbus
          pip install pytest pytest-asyncio dbus-next
      - name: Start services
        run: |
          sudo systemctl start dbus
          sudo systemctl start bluetooth
      - name: Run tests
        run: pytest tests/ -v
```

## Test Markers

Filter tests by marker:

```bash
# Only integration tests
pytest -m integration

# Exclude integration tests
pytest -m "not integration"

# Only async tests
pytest -m asyncio

# Only slow tests
pytest -m slow
```

## Test Output

### Verbose Mode

```bash
pytest tests/ -v
```

Shows each test name and result.

### Coverage Report

```bash
pytest tests/ --cov=rpi_kvm --cov-report=html
```

Generates `htmlcov/index.html` with coverage details.

### Detailed Output

```bash
pytest tests/ -vv -s
```

- `-vv`: More verbose
- `-s`: Show print statements

## Debugging Tests

### Run Single Test

```bash
pytest tests/test_bt_client.py::TestBtClientBasics::test_init -v
```

### Drop into Debugger on Failure

```bash
pytest tests/ --pdb
```

### See Full Tracebacks

```bash
pytest tests/ --tb=long
```

## Common Issues

### `ModuleNotFoundError: No module named 'dbus_next'`

**Solution**:
```bash
pip3 install dbus-next pytest pytest-asyncio
```

### `D-Bus not available`

**Solution**: Start D-Bus and BlueZ:
```bash
sudo systemctl start dbus
sudo systemctl start bluetooth
```

Or use Vagrant VM (has services pre-configured).

### `pytest: command not found`

**Solution**:
```bash
pip3 install pytest
# or
python3 -m pytest tests/  # Use module mode
```

### Integration Tests Skip

Integration tests auto-skip if BlueZ unavailable. Expected in non-VM environments.

To force run (will fail if services missing):
```bash
pytest tests/test_bt_integration.py --runxfail
```

## Writing New Tests

### Unit Test Template

```python
# tests/test_myfeature.py
from rpi_kvm.mymodule import MyClass

def test_my_feature():
    """Test description"""
    obj = MyClass()
    result = obj.do_something()
    assert result == expected
```

### Async Test Template

```python
import pytest

@pytest.mark.asyncio
async def test_async_feature():
    """Test async functionality"""
    result = await some_async_function()
    assert result is not None
```

### Integration Test Template

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_bluez():
    """Test requiring real BlueZ"""
    # Will auto-skip if BlueZ not available
    pass
```

## Continuous Testing

Watch mode (re-run on file changes):

```bash
# Install pytest-watch
pip install pytest-watch

# Run
ptw tests/
```

## Next Steps

- See [Testing Setup](testing-setup.md) for Vagrant details
- See [Contributing](contributing.md) for PR requirements
- Write tests before committing features!
