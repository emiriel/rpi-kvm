"""pytest configuration and fixtures for rpi-kvm tests"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
import sys
from pathlib import Path

# Add rpi_kvm to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_dbus():
    """Mock dbus-next MessageBus and objects"""
    bus = AsyncMock()

    # Mock introspection and proxy object
    introspection = Mock()
    proxy_obj = Mock()

    # Mock BlueZ Device1 interface
    device_interface = Mock()
    device_interface.get_name = AsyncMock(return_value="TestDevice")
    device_interface.get_connected = AsyncMock(return_value=False)
    device_interface.get_services_resolved = AsyncMock(return_value=False)

    # Mock Properties interface
    props_interface = Mock()
    props_interface.on_properties_changed = Mock()

    proxy_obj.get_interface = Mock(side_effect=lambda iface: {
        "org.bluez.Device1": device_interface,
        "org.freedesktop.DBus.Properties": props_interface
    }[iface])

    bus.introspect = AsyncMock(return_value=introspection)
    bus.get_proxy_object = Mock(return_value=proxy_obj)

    return {
        "bus": bus,
        "device_interface": device_interface,
        "props_interface": props_interface,
        "proxy_obj": proxy_obj
    }


@pytest.fixture
def mock_socket():
    """Mock socket module for Bluetooth L2CAP connections"""
    import socket as real_socket

    mock_ctrl_sock = Mock()
    mock_intr_sock = Mock()

    # Track socket creation
    sockets_created = []

    original_socket = real_socket.socket

    def mock_socket_factory(family, type, proto):
        if family == real_socket.AF_BLUETOOTH and proto == real_socket.BTPROTO_L2CAP:
            sock = Mock()
            sock.connect = Mock()
            sock.close = Mock()
            sock.setblocking = Mock()
            sockets_created.append(sock)
            return sock
        return original_socket(family, type, proto)

    return {
        "factory": mock_socket_factory,
        "sockets": sockets_created
    }


@pytest.fixture
def mock_logging():
    """Mock logging to suppress output during tests"""
    import logging

    # Save original handlers
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers.copy()
    original_level = root_logger.level

    # Clear handlers and set to CRITICAL (suppress output)
    root_logger.handlers.clear()
    root_logger.setLevel(logging.CRITICAL)

    yield logging

    # Restore
    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)


@pytest.fixture
def property_variant():
    """Factory for creating D-Bus variant mocks"""
    def make_variant(value):
        variant = Mock()
        variant.value = value
        return variant
    return make_variant
