#!/usr/bin/python3
#
# Bluetooth D-Bus Service

import os
import sys
import asyncio
import dbus_next
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface
from dbus_next import Variant
import signal
import logging
import json
from settings import Settings
from bt_server import BtServer
from hotkey import HotkeyDetector, HotkeyConfig, HotkeyAktion
from usb_hid_decoder import UsbHidDecoder
from input_handler import InputManager

class KvmDbusService(ServiceInterface):
    def __init__(self, settings, hotkey_detector, bt_server):
        super().__init__("org.rpi.kvmservice")
        self._settings = settings
        self._hotkey_detector = hotkey_detector
        self._bt_server = bt_server
        self._stop_event = False

    def stop(self):
        self._stop_event = True

    def on_clients_change(self, clients):
        self.signal_clients_change(clients)

    async def run(self):
        logging.info("D-Bus: Register D-Bus service")
        await self._register_to_dbus()
        logging.info("D-Bus: Register notifier on Bluetooth server: on client change")
        self._bt_server.register_on_clients_change_handler(self)
        logging.info("D-Bus: Run in loop")
        while not self._stop_event:
            await asyncio.sleep(2)
        logging.info("D-Bus: Unregister notifier on Bluetooth server: on client change")
        self._bt_server.unregister_on_clients_change_handler(self)
        logging.info("D-Bus: D-Bus service finished")

    async def _register_to_dbus(self):
        self._bus = await MessageBus(bus_type=dbus_next.BusType.SYSTEM).connect()
        self._bus.export("/org/rpi/kvmservice", self)
        await self._bus.request_name("org.rpi.kvmservice")

    @dbus_next.service.method()
    def GetConnectedClientNames(self) -> 'as':
        return self._bt_server.get_connected_client_names()

    @dbus_next.service.method()
    def GetClientsInfo(self) -> 's':
        return json.dumps(self._bt_server.get_clients_info_dict())

    @dbus_next.service.method()
    def ConnectClient(self, client_address: 's') -> '':
        self._bt_server.connect_client(client_address)
        return

    @dbus_next.service.method()
    def DisconnectClient(self, client_address: 's') -> '':
        self._bt_server.disconnect_client(client_address)
        return

    @dbus_next.service.method()
    def RemoveClient(self, client_address: 's') -> '':
        self._bt_server.remove_client(client_address)
        return

    @dbus_next.service.method()
    def ChangeClientOrder(self, client_address: 's', order_type: 's') -> '':
        self._bt_server.change_client_order(client_address, order_type)
        return

    @dbus_next.service.method()
    def ReloadSettings(self) -> '':
        logging.info(f"D-Bus: Reload settings")
        self._hotkey_detector.reload_settings()
        return
    
    @dbus_next.service.method()
    def GetTouchPhatSettings(self) -> 's':
        return json.dumps(self._settings["touchphat"])

    @dbus_next.service.method()
    def RestartInfoHub(self) -> '':
        logging.info(f"D-Bus: Restart Info Hub")
        self.signal_restart_info_hub()
        return

    @dbus_next.service.method()
    def SwitchActiveHost(self, client_address: 's') -> '':
        self._bt_server.switch_active_host_to(client_address)
        client_names = self._bt_server.get_connected_client_names()
        logging.info(f"D-Bus: Switch active host to: {client_names[0]}")
        self.signal_host_change(client_names)

    def switch_to_next_connected_host_internal(self):
        client_addresses = self._bt_server._get_connected_client_addresses()
        if client_addresses and len(client_addresses) > 1:
            self.SwitchActiveHost(client_addresses[1])

    @dbus_next.service.method()
    def SwitchToNextConnectedHost(self) -> '':
        self.switch_to_next_connected_host_internal()

    @dbus_next.service.signal()
    def signal_host_change(self, client_names: 'as') -> 'as':
        return client_names

    @dbus_next.service.signal()
    def signal_clients_change(self, client_names: 'as') -> 'as':
        return client_names

    @dbus_next.service.signal()
    def signal_restart_info_hub(self) -> '':
        return

async def main():
    logging.basicConfig(format='BT %(levelname)s: %(message)s', level=logging.DEBUG)

    if not os.geteuid() == 0: # Check if user is root
        logging.error("Root permissions required: Execute as root or with sudo")
        return

    bt_server = BtServer()
    bt_server_task = asyncio.create_task( bt_server.run() )

    settings = Settings()
    settings.load_from_file()
    hotkey_config = HotkeyConfig(settings)
    hotkey_detector = HotkeyDetector(hotkey_config)
    kvm_dbus_service = KvmDbusService(settings, hotkey_detector, bt_server)
    kvm_dbus_service_task = asyncio.create_task( kvm_dbus_service.run() )

    input_manager = InputManager(
        bt_server,
        hotkey_detector,
        kvm_dbus_service.switch_to_next_connected_host_internal,
    )
    input_manager_task = asyncio.create_task( input_manager.run() )

    main_future = asyncio.Future()

    def signal_handler(sig, frame):
        logging.error("System: Ctrl+C has been pressed - Shut down")
        main_future.set_result("")
    signal.signal(signal.SIGINT, signal_handler)

    await main_future # wait until signal interrupts

    input_manager.stop()
    await input_manager_task
    kvm_dbus_service.stop()
    await kvm_dbus_service_task
    bt_server.stop()
    await bt_server_task
    logging.error("System: Shut down completed")

if __name__ == "__main__":
    asyncio.run( main() )

