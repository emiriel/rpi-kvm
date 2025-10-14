import touchphat
import asyncio
import dbus_next
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface
import logging
import json

class TouchPhatHandler(object):
    def __init__(self):
        self._kvm_dbus_iface = None
        self._stop_event = False
        self._button_actions = {} # Will be loaded from settings

        touchphat.on_release(0, self._on_button_0_release)
        touchphat.on_release(1, self._on_button_1_release)
        touchphat.on_release(2, self._on_button_2_release)
        touchphat.on_release(3, self._on_button_3_release)
        touchphat.on_release(4, self._on_button_4_release)
        touchphat.on_release(5, self._on_button_5_release)

    def stop(self):
        self._stop_event = True

    async def _connect_to_dbus_service(self):
        while not self._kvm_dbus_iface:
            try:
                bus = await MessageBus(bus_type=dbus_next.BusType.SYSTEM).connect()
                introspection = await bus.introspect(
                    'org.rpi.kvmservice', '/org/rpi/kvmservice')
                kvm_service_obj = bus.get_proxy_object(
                    'org.rpi.kvmservice', '/org/rpi/kvmservice', introspection)
                self._kvm_dbus_iface = kvm_service_obj.get_interface('org.rpi.kvmservice')
                logging.info("TouchPhat: D-Bus service connected")
            except dbus_next.DBusError:
                logging.warning("TouchPhat: D-Bus service not available - reconnecting...")
                await asyncio.sleep(5)

    async def run(self):
        logging.info(f"TouchPhat: D-Bus service connecting...")
        await self._connect_to_dbus_service()
        await self._load_settings()
        logging.info("TouchPhat: Running in loop")
        while not self._stop_event:
            await asyncio.sleep(1)
        logging.info("TouchPhat: Shut down completed")

    async def _load_settings(self):
        try:
            settings_json = await self._kvm_dbus_iface.call_get_touch_phat_settings()
            self._button_actions = json.loads(settings_json)
            logging.info(f"TouchPhat: Loaded settings: {self._button_actions}")
        except dbus_next.DBusError:
            logging.warning(f"TouchPhat: D-Bus connection terminated - reconnecting...")
            await self._connect_to_dbus_service()
            await self._load_settings()

    async def _trigger_action(self, button_id):
        action = self._button_actions.get(button_id)
        if action == "switch_next_host":
            logging.info(f"TouchPhat: Button {button_id} pressed - Switching to next host")
            try:
                await self._kvm_dbus_iface.call_switch_to_next_connected_host()
            except dbus_next.DBusError:
                logging.warning(f"TouchPhat: D-Bus connection terminated - reconnecting...")
                await self._connect_to_dbus_service()
                await self._kvm_dbus_iface.call_switch_to_next_connected_host()
        else:
            logging.info(f"TouchPhat: Button {button_id} pressed - No action configured")

    def _on_button_0_release(self):
        asyncio.create_task(self._trigger_action(0))

    def _on_button_1_release(self):
        asyncio.create_task(self._trigger_action(1))

    def _on_button_2_release(self):
        asyncio.create_task(self._trigger_action(2))

    def _on_button_3_release(self):
        asyncio.create_task(self._trigger_action(3))

    def _on_button_4_release(self):
        asyncio.create_task(self._trigger_action(4))

    def _on_button_5_release(self):
        asyncio.create_task(self._trigger_action(5))

async def main():
    logging.basicConfig(format='TouchPhat %(levelname)s: %(message)s', level=logging.DEBUG)
    touch_phat_handler = TouchPhatHandler()
    await touch_phat_handler.run()

if __name__ == "__main__":
    asyncio.run(main())