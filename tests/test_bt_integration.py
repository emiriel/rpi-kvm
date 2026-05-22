"""Integration tests with real D-Bus and BlueZ simulation"""

import pytest
import asyncio
import dbus_next
from dbus_next.aio import MessageBus
from dbus_next import BusType, Message, MessageType
from unittest.mock import Mock, patch
import subprocess
import time

from rpi_kvm.bt_client import BtClient, BtConnectionRole


pytestmark = pytest.mark.integration


@pytest.fixture
async def dbus_connection():
    """Connect to system D-Bus"""
    try:
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        yield bus
        bus.disconnect()
    except Exception as e:
        pytest.skip(f"D-Bus not available: {e}")


@pytest.fixture
def check_bluez_running():
    """Check if BlueZ daemon is running"""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'bluetooth'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode != 0:
            pytest.skip("BlueZ (bluetooth service) not running")
    except Exception as e:
        pytest.skip(f"Cannot check BlueZ status: {e}")


@pytest.fixture
async def mock_bluez_device(dbus_connection):
    """Create a mock BlueZ device on D-Bus for testing

    Note: This is a simplified mock. Real BlueZ device would need
    proper object registration and interface implementation.
    """
    # For now, skip actual device creation - would need bluez mock server
    pytest.skip("BlueZ device mocking not yet implemented - needs mock bluez server")


class TestBtClientWithRealDBus:
    """Integration tests with real D-Bus connection"""

    @pytest.mark.asyncio
    async def test_dbus_connection(self, dbus_connection):
        """Test that we can connect to D-Bus"""
        assert dbus_connection is not None
        assert dbus_connection.unique_name.startswith(':')

    @pytest.mark.asyncio
    async def test_bluez_adapter_exists(self, dbus_connection, check_bluez_running):
        """Test that BlueZ adapter is available on D-Bus"""
        try:
            introspection = await dbus_connection.introspect(
                'org.bluez',
                '/org/bluez/hci0'
            )
            assert introspection is not None
        except Exception as e:
            pytest.skip(f"BlueZ adapter not available: {e}")

    @pytest.mark.asyncio
    async def test_list_bluez_devices(self, dbus_connection, check_bluez_running):
        """List paired Bluetooth devices via D-Bus"""
        try:
            # Get ObjectManager interface
            introspection = await dbus_connection.introspect(
                'org.bluez',
                '/'
            )
            obj = dbus_connection.get_proxy_object('org.bluez', '/', introspection)
            manager = obj.get_interface('org.freedesktop.DBus.ObjectManager')

            # Get all managed objects
            objects = await manager.call_get_managed_objects()

            # Filter for Device1 interfaces
            devices = [
                path for path, interfaces in objects.items()
                if 'org.bluez.Device1' in interfaces
            ]

            print(f"\nFound {len(devices)} paired devices")
            for device_path in devices:
                print(f"  - {device_path}")

            # Test passes even with 0 devices (just verifying D-Bus works)
            assert isinstance(devices, list)

        except Exception as e:
            pytest.skip(f"Cannot list BlueZ devices: {e}")


class TestBtClientIntegration:
    """Integration tests for BtClient with mocked hardware"""

    @pytest.mark.asyncio
    async def test_create_client_with_fake_device(self):
        """Test BtClient creation with non-existent device

        Should handle gracefully when device doesn't exist
        """
        # Use fake MAC that definitely doesn't exist
        fake_address = "FF:FF:FF:FF:FF:FF"

        # Mock socket to avoid actual connection attempts
        with patch('socket.socket'):
            client = BtClient(fake_address)

            # Should initialize without error
            assert client.address == fake_address
            assert client.is_connected == False

            # Attempting to connect to D-Bus will fail for fake device
            # (expected behavior - device doesn't exist)

    @pytest.mark.asyncio
    async def test_property_change_simulation(self):
        """Simulate D-Bus property changes without real BlueZ"""
        client = BtClient("AA:BB:CC:DD:EE:FF")
        client._name = "TestDevice"

        # Mock connect to avoid asyncio issues
        with patch.object(client, 'connect'):
            # Simulate property change callback
            variant = Mock()
            variant.value = True

            # Test Connected property
            client._on_properties_changed(
                "org.bluez.Device1",
                {"Connected": variant},
                []
            )
            assert client._is_bluez_connected == True

            # Test ServicesResolved property
            client._on_properties_changed(
                "org.bluez.Device1",
                {"ServicesResolved": variant},
                []
            )
            assert client._services_resolved == True


# Manual test instructions (for VM testing)
"""
To test with real BlueZ in VM:

1. Start VM:
   vagrant up
   vagrant ssh

2. Check BlueZ status:
   systemctl status bluetooth

3. Load vhci module:
   sudo modprobe hci_vhci

4. Run integration tests:
   cd /vagrant
   python3 -m pytest tests/test_bt_integration.py -v -m integration

5. Optional - create virtual BT device:
   # Would need tools like:
   # - hciconfig to create virtual controller
   # - dbus-send to simulate property changes
   # - Custom mock BlueZ device implementation
"""
