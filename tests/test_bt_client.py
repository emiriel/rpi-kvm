"""Unit tests for BtClient"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import socket

from rpi_kvm.bt_client import BtClient, BtConnectionRole


class TestBtClientBasics:
    """Test basic BtClient functionality"""

    def test_init(self):
        """Test BtClient initialization"""
        address = "AA:BB:CC:DD:EE:FF"
        client = BtClient(address)

        assert client.address == address
        assert client.object_path == "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"
        assert client.is_connected == False
        assert client.is_alive == False

    def test_mac_address_conversion(self):
        """Test MAC address <-> object path conversion"""
        address = "11:22:33:44:55:66"
        path = BtClient.get_device_object_path_from_mac_address(address)
        assert path == "/org/bluez/hci0/dev_11_22_33_44_55_66"

        recovered = BtClient.get_mac_address_from_devie_object_path(path)
        assert recovered == address


class TestBtClientPropertyChanges:
    """Test D-Bus property change handling"""

    def test_connected_property_change(self, property_variant, mock_logging):
        """Test Connected property change tracking"""
        client = BtClient("AA:BB:CC:DD:EE:FF")
        client._name = "TestHost"

        # Simulate Connected = True
        variant = property_variant(True)
        client._on_properties_changed(
            "org.bluez.Device1",
            {"Connected": variant},
            []
        )

        assert client._is_bluez_connected == True

        # Simulate Connected = False
        variant = property_variant(False)
        client._on_properties_changed(
            "org.bluez.Device1",
            {"Connected": variant},
            []
        )

        assert client._is_bluez_connected == False

    def test_services_resolved_property_change(self, property_variant, mock_logging):
        """Test ServicesResolved property change tracking"""
        client = BtClient("AA:BB:CC:DD:EE:FF")
        client._name = "TestHost"
        client._task = None  # Not alive, so reconnect would trigger

        # Initially False (set in __init__)
        assert client._services_resolved == False

        # Mock connect to avoid asyncio issues in sync test
        with patch.object(client, 'connect'):
            # Simulate ServicesResolved = True
            variant = property_variant(True)
            client._on_properties_changed(
                "org.bluez.Device1",
                {"ServicesResolved": variant},
                []
            )

            assert client._services_resolved == True

            # Simulate ServicesResolved = False
            variant = property_variant(False)
            client._on_properties_changed(
                "org.bluez.Device1",
                {"ServicesResolved": variant},
                []
            )

            assert client._services_resolved == False

    def test_rssi_property_logged(self, property_variant, mock_logging, caplog):
        """Test RSSI property change is logged"""
        client = BtClient("AA:BB:CC:DD:EE:FF")
        client._name = "TestHost"

        # Set logging level to capture debug
        import logging
        caplog.set_level(logging.DEBUG)

        # Simulate RSSI update
        variant = property_variant(-50)
        client._on_properties_changed(
            "org.bluez.Device1",
            {"RSSI": variant},
            []
        )

        # RSSI should be logged but not trigger actions
        # (just check it doesn't crash)


class TestBtClientReconnectLogic:
    """Test reconnection trigger logic"""

    def test_reconnect_not_triggered_if_already_alive(self, property_variant, mock_logging):
        """ServicesResolved should not reconnect if already connected"""
        client = BtClient("AA:BB:CC:DD:EE:FF")
        client._name = "TestHost"
        client._task = AsyncMock()
        client._task.done = Mock(return_value=False)  # is_alive = True

        with patch.object(client, 'connect') as mock_connect:
            variant = property_variant(True)
            client._on_properties_changed(
                "org.bluez.Device1",
                {"ServicesResolved": variant},
                []
            )

            # Should NOT call connect() because already alive
            mock_connect.assert_not_called()

    def test_reconnect_not_triggered_if_stopped(self, property_variant, mock_logging):
        """ServicesResolved should not reconnect if stop_event set"""
        client = BtClient("AA:BB:CC:DD:EE:FF")
        client._name = "TestHost"
        client._stop_event = True

        with patch.object(client, 'connect') as mock_connect:
            variant = property_variant(True)
            client._on_properties_changed(
                "org.bluez.Device1",
                {"ServicesResolved": variant},
                []
            )

            # Should NOT reconnect because stopped
            mock_connect.assert_not_called()

    def test_reconnect_triggered_when_services_resolved(self, property_variant, mock_logging):
        """ServicesResolved=True should trigger reconnect if offline"""
        client = BtClient("AA:BB:CC:DD:EE:FF")
        client._name = "TestHost"
        client._stop_event = False
        client._task = None  # is_alive = False

        with patch.object(client, 'connect') as mock_connect:
            variant = property_variant(True)
            client._on_properties_changed(
                "org.bluez.Device1",
                {"ServicesResolved": variant},
                []
            )

            # Should trigger reconnect
            mock_connect.assert_called_once()


class TestBtClientConnectionRole:
    """Test Bluetooth master/slave role management"""

    @pytest.mark.asyncio
    async def test_get_connection_role_master(self, mock_logging):
        """Test parsing MASTER role from hcitool output"""
        client = BtClient("AA:BB:CC:DD:EE:FF")

        with patch('rpi_kvm.common.System.exec_cmd', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (
                0,
                b"Connections:\n\t< ACL AA:BB:CC:DD:EE:FF handle 42 state 1 lm MASTER\n",
                b""
            )

            role = await client._get_connection_role()
            assert role == BtConnectionRole.Master

    @pytest.mark.asyncio
    async def test_get_connection_role_slave(self, mock_logging):
        """Test parsing SLAVE role from hcitool output"""
        client = BtClient("AA:BB:CC:DD:EE:FF")

        with patch('rpi_kvm.common.System.exec_cmd', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (
                0,
                b"Connections:\n\t< ACL AA:BB:CC:DD:EE:FF handle 42 state 1 lm SLAVE\n",
                b""
            )

            role = await client._get_connection_role()
            assert role == BtConnectionRole.Slave

    @pytest.mark.asyncio
    async def test_get_connection_role_not_connected(self, mock_logging):
        """Test NotConnected role when device absent"""
        client = BtClient("AA:BB:CC:DD:EE:FF")

        with patch('rpi_kvm.common.System.exec_cmd', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (
                0,
                b"Connections:\n",
                b""
            )

            role = await client._get_connection_role()
            assert role == BtConnectionRole.NotConnected


class TestBtClientMessageQueue:
    """Test HID message queuing and sending"""

    def test_send_adds_to_queue(self, mock_logging):
        """Test that send() adds messages to queue"""
        client = BtClient("AA:BB:CC:DD:EE:FF")
        client._is_connected = True

        message = bytes([0x01, 0x02, 0x03])
        client.send(message)

        # Message should be in queue
        assert client._message_queue.qsize() == 1

    def test_send_ignored_when_disconnected(self, mock_logging):
        """Test that send() does nothing when disconnected"""
        client = BtClient("AA:BB:CC:DD:EE:FF")
        client._is_connected = False

        message = bytes([0x01, 0x02, 0x03])
        client.send(message)

        # Queue should remain empty
        assert client._message_queue.qsize() == 0


class TestBtClientLifecycle:
    """Test connection lifecycle"""

    def test_connect_creates_task(self, mock_logging):
        """Test connect() creates async tasks (run + reconnect loop)"""
        client = BtClient("AA:BB:CC:DD:EE:FF")

        with patch('asyncio.create_task') as mock_create_task:
            client.connect()
            assert mock_create_task.call_count == 2

    def test_stop_sets_stop_event(self, mock_logging):
        """Test stop() sets stop flag"""
        client = BtClient("AA:BB:CC:DD:EE:FF")
        client._stop_event = False

        client.stop()

        assert client._stop_event == True

    def test_disconnect_closes_sockets(self, mock_logging):
        """Test _disconnect() closes both sockets"""
        client = BtClient("AA:BB:CC:DD:EE:FF")

        # Mock sockets
        mock_ctrl = Mock()
        mock_intr = Mock()
        client._control_socket = mock_ctrl
        client._interrupt_socket = mock_intr
        client._is_connected = True

        client._disconnect()

        # Both sockets should be closed
        mock_ctrl.close.assert_called_once()
        mock_intr.close.assert_called_once()
        assert client._is_connected == False
        assert client._control_socket is None
        assert client._interrupt_socket is None


class TestBtClientRetryLoop:
    """Test the per-client reconnect loop (keyboard-like retry behaviour)"""

    def _make_client(self):
        client = BtClient("AA:BB:CC:DD:EE:FF")
        client._name = "TestHost"
        return client

    async def test_loop_retries_offline_client(self, monkeypatch, mock_logging):
        """Loop must keep calling connect() while the host stays offline"""
        monkeypatch.setattr(BtClient, "BT_RECONNECT_RETRY_INTERVAL", 0.01)
        client = self._make_client()

        with patch.object(client, "connect") as mock_connect:
            client._ensure_reconnect_loop()
            await asyncio.sleep(0.05)
            assert mock_connect.call_count >= 2

            client.stop()
            await asyncio.sleep(0.05)
            count_after_stop = mock_connect.call_count
            await asyncio.sleep(0.05)
            assert mock_connect.call_count == count_after_stop

    async def test_loop_does_not_retry_when_alive(self, monkeypatch, mock_logging):
        """Loop must not call connect() while the client task is running"""
        monkeypatch.setattr(BtClient, "BT_RECONNECT_RETRY_INTERVAL", 0.01)
        client = self._make_client()
        client._task = AsyncMock()
        client._task.done = Mock(return_value=False)  # is_alive = True

        with patch.object(client, "connect") as mock_connect:
            client._ensure_reconnect_loop()
            await asyncio.sleep(0.05)
            mock_connect.assert_not_called()

        client.stop()

    async def test_loop_independent_per_client(self, monkeypatch, mock_logging):
        """A connected client must not stop another client's retry loop"""
        monkeypatch.setattr(BtClient, "BT_RECONNECT_RETRY_INTERVAL", 0.01)
        online = self._make_client()
        online._task = AsyncMock()
        online._task.done = Mock(return_value=False)
        offline = self._make_client()

        with patch.object(online, "connect") as online_connect, \
             patch.object(offline, "connect") as offline_connect:
            online._ensure_reconnect_loop()
            offline._ensure_reconnect_loop()
            await asyncio.sleep(0.05)
            online_connect.assert_not_called()
            assert offline_connect.call_count >= 2

        online.stop()
        offline.stop()

    async def test_connect_starts_loop(self, monkeypatch, mock_logging):
        """connect() must ensure the retry loop is running"""
        client = self._make_client()
        with patch.object(client, "_run", new_callable=AsyncMock):
            client.connect()
            assert client._reconnect_task is not None
            assert not client._reconnect_task.done()
            client.stop()

    async def test_stop_cancels_loop(self, monkeypatch, mock_logging):
        """stop() must cancel the retry loop task"""
        monkeypatch.setattr(BtClient, "BT_RECONNECT_RETRY_INTERVAL", 0.01)
        client = self._make_client()
        with patch.object(client, "connect"):
            client._ensure_reconnect_loop()
            loop_task = client._reconnect_task
            client.stop()
            await asyncio.sleep(0.01)
            assert loop_task.done()

    async def test_loop_restarts_after_manual_reconnect(self, monkeypatch, mock_logging):
        """After a manual stop(), a manual connect() must restart the loop"""
        monkeypatch.setattr(BtClient, "BT_RECONNECT_RETRY_INTERVAL", 0.01)
        client = self._make_client()
        with patch.object(client, "_run", new_callable=AsyncMock):
            client.connect()
            first_loop = client._reconnect_task
            client.stop()
            await asyncio.sleep(0.01)
            assert first_loop.done()

            client.connect()
            assert client._reconnect_task is not first_loop
            assert not client._reconnect_task.done()
            client.stop()
