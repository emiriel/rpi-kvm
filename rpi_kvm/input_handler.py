#!/usr/bin/python3

import asyncio
import time
import logging
import evdev
from evdev import ecodes

from hid_scanner import HidScanner
from usb_hid_decoder import UsbHidDecoder
from hotkey import HotkeyAktion


class KeyboardHandler:
    def __init__(self, input_device, bt_server, hotkey_detector, host_switch_cb):
        self._idev = input_device
        self._bt_server = bt_server
        self._hotkey_detector = hotkey_detector
        self._host_switch_cb = host_switch_cb
        self._is_alive = False
        self._modifiers = [
            False,  # Right GUI
            False,  # Right Alt
            False,  # Right Shift
            False,  # Right Control
            False,  # Left GUI
            False,  # Left Alt
            False,  # Left Shift
            False,  # Left Control
        ]
        self._keys = [0, 0, 0, 0, 0, 0]
        logging.info(f"{self._idev.path}: Init KeyboardHandler - {self._idev.name}")

    @property
    def is_alive(self):
        return self._is_alive

    @property
    def path(self):
        return self._idev.path

    @property
    def name(self):
        return self._idev.name

    async def run(self):
        logging.info(f"{self._idev.path}: Starting keyboard event loop")
        self._is_alive = True
        try:
            await self._event_loop()
        except Exception as e:
            logging.error(f"{self._idev.path}: {e}")
        self._is_alive = False

    async def _event_loop(self):
        async for event in self._idev.async_read_loop():
            if event.type == ecodes.EV_KEY and event.value < 2:
                self._handle_event(event)
                self._send_state()  # synchronous — completes in microseconds, never blocks

    def _send_state(self):
        modifiers_int = UsbHidDecoder.convert_modifier_bit_mask_to_int(self._modifiers)
        logging.debug(f"{self._idev.path}: modifiers={modifiers_int:#04x} keys={self._keys}")

        action = self._hotkey_detector.evaluate_new_input([modifiers_int, *self._keys])
        if action == HotkeyAktion.SwitchToNextHost:
            logging.info(f"{self._idev.path}: Hotkey triggered - switching host")
            self._host_switch_cb()
            return

        telegram = [0xA1, 1, modifiers_int, 0, *self._keys]
        self._bt_server.send(telegram)

    def _handle_event(self, event):
        if event.code not in ecodes.KEY:
            logging.warning(f"{self._idev.path}: unsupported key press code: {event.code}")
            return
        evdev_code = ecodes.KEY[event.code]
        if UsbHidDecoder.is_modifier_key(evdev_code):
            modifier_index = UsbHidDecoder.encode_modifier_key_index(evdev_code)
            self._modifiers[modifier_index] = not self._modifiers[modifier_index]
        else:
            usb_key_code = UsbHidDecoder.encode_regular_key(evdev_code)
            for i in range(6):
                if self._keys[i] == usb_key_code and event.value == 0:
                    self._keys[i] = 0x00
                elif self._keys[i] == 0x00 and event.value == 1:
                    self._keys[i] = usb_key_code
                    break


class EventMouse:
    def __init__(self, input_device):
        self._idev = input_device
        logging.info(f"{self._idev.path}: Init Mouse - {self._idev.name}")
        self.send_state_cb = None
        self.__client_switch_button_index = 2
        self._is_alive = False

        self._buttons = [
            False,  # USB not defined
            False,  # USB not defined
            False,  # USB not defined. Not send via bluetooth -> placeholder for client switch
            False,  # Forward mouse button
            False,  # Backward mouse button
            False,  # Middle mouse button
            False,  # Right mouse button
            False,  # Left mouse button
        ]
        self._x_pos = 0
        self._y_pos = 0
        self._v_wheel = 0
        self._h_wheel = 0
        self._have_buttons_changed = False
        self._last_syn_event_time = 0
        self._update_rate = 20 / 1000

    @property
    def is_alive(self):
        return self._is_alive

    @property
    def path(self):
        return self._idev.path

    @property
    def name(self):
        return self._idev.name

    @property
    def buttons(self):
        return self._buttons

    async def run(self):
        self._is_alive = True
        logging.info(f"{self._idev.path}: Start sending mouse sync events continuously")
        asyncio.create_task(self._continuous_sync_event())
        logging.info(f"{self._idev.path}: Start listening to mouse event loop")
        try:
            await self._event_loop()
        except Exception as e:
            logging.error(f"{self._idev.path}: {e}")
        self._is_alive = False

    async def _event_loop(self):
        async for event in self._idev.async_read_loop():
            await self._handle_event(event)

    async def _continuous_sync_event(self):
        while self._is_alive:
            time_ns = time.time_ns()
            time_s = int(time_ns / 1_000_000_000)
            time_ms = int((time_ns - (time_s * 1_000_000_000)) / 1_000)
            basic_event = evdev.events.InputEvent(time_s, time_ms, ecodes.EV_SYN, 55, 55)
            await self._handle_event(basic_event)
            await asyncio.sleep(1)

    async def _handle_event(self, event):
        if event.type == ecodes.EV_SYN:
            current_time = time.monotonic()
            if current_time - self._last_syn_event_time < self._update_rate and not self._have_buttons_changed:
                return
            self._last_syn_event_time = current_time
            if self.send_state_cb:
                await self.send_state_cb(self._buttons, self._x_pos, self._y_pos, self._v_wheel, self._h_wheel)
            self._x_pos = 0
            self._y_pos = 0
            self._v_wheel = 0
            self._h_wheel = 0
            self._have_buttons_changed = False
        elif event.type == ecodes.EV_KEY:
            button_index = UsbHidDecoder.encode_mouse_button_index(event.code)
            if button_index >= 0 and event.value < 2:
                self._have_buttons_changed = True
                self._buttons[button_index] = (event.value == 1)
                if event.code in ecodes.BTN:
                    logging.debug(f"{self._idev.path}: Key event {ecodes.BTN[event.code]}: {event.value}")
                else:
                    logging.debug(f"{self._idev.path}: Key event {event.code}: {event.value}")
            elif event.code == 125:  # MX Master 3 - Gesture mouse button
                logging.debug(f"{self._idev.path}: Key event BTN_GESTURE: {event.value}")
                self._have_buttons_changed = True
                self._buttons[self.__client_switch_button_index] = (event.value == 1)
        elif event.type == ecodes.EV_REL:
            if event.code == 0:
                self._x_pos += event.value
            elif event.code == 1:
                self._y_pos += event.value
            elif event.code == 8:
                logging.debug(f"{self._idev.path}: V-Wheel movement: {event.value}")
                self._v_wheel += event.value
            elif event.code == 6:
                logging.debug(f"{self._idev.path}: H-Wheel movement: {event.value}")
                self._h_wheel -= event.value


class MouseHandler:
    def __init__(self, bt_server, hotkey_detector, host_switch_cb):
        self._bt_server = bt_server
        self._hotkey_detector = hotkey_detector
        self._host_switch_cb = host_switch_cb
        self.event_mice = {}

    async def send_state(self, buttons, x_pos, y_pos, v_wheel, h_wheel):
        common_buttons = [False, False, False, False, False, False, False, False]
        for event_mouse in self.event_mice.values():
            for i, button_val in enumerate(event_mouse.buttons):
                common_buttons[i] |= button_val

        action = self._hotkey_detector.evaluate_new_mouse_input(common_buttons)
        if action == HotkeyAktion.SwitchToNextHost:
            logging.info("Mouse: gesture button triggered - switching host")
            self._host_switch_cb()
            return

        buttons_byte = UsbHidDecoder.convert_modifier_bit_mask_to_int(common_buttons)

        # Log large movements before chunking
        if abs(x_pos) > 127 or abs(y_pos) > 127:
            logging.debug(f"Mouse: chunking large movement x={x_pos} y={y_pos}")

        # Chunk large movements into multiple reports (signed byte range: -127 to 127)
        # Send wheel only on first chunk
        v_byte = UsbHidDecoder.enshure_byte_size(v_wheel)
        h_byte = UsbHidDecoder.enshure_byte_size(h_wheel)

        while abs(x_pos) > 0 or abs(y_pos) > 0:
            # Clamp to signed byte range
            x_chunk = max(-127, min(127, x_pos))
            y_chunk = max(-127, min(127, y_pos))

            x_byte = x_chunk & 0xFF if x_chunk >= 0 else (256 + x_chunk) & 0xFF
            y_byte = y_chunk & 0xFF if y_chunk >= 0 else (256 + y_chunk) & 0xFF

            telegram = [0xA1, 2, buttons_byte, x_byte, y_byte, v_byte, h_byte]
            self._bt_server.send(telegram)

            # Subtract sent chunk from remaining movement
            x_pos -= x_chunk
            y_pos -= y_chunk

            # Only send wheel/buttons on first chunk
            v_byte = 0
            h_byte = 0
            buttons_byte = 0  # Don't repeat button state in subsequent chunks


class InputManager:
    def __init__(self, bt_server, hotkey_detector, host_switch_cb):
        self._bt_server = bt_server
        self._hotkey_detector = hotkey_detector
        self._host_switch_cb = host_switch_cb
        self._hid_scanner = HidScanner()
        self._keyboards = {}
        self._mouse_handler = MouseHandler(bt_server, hotkey_detector, host_switch_cb)
        self._stop_event = False

    def stop(self):
        self._stop_event = True

    async def run(self):
        logging.info("InputManager: Starting device scan loop")
        while not self._stop_event:
            await self._hid_scanner.scan()

            dead_kbs = [kb for kb in self._keyboards.values() if not kb.is_alive]
            for kb in dead_kbs:
                logging.info(f"InputManager: Removing dead keyboard: {kb.path}")
                del self._keyboards[kb.path]

            dead_mice = [em for em in self._mouse_handler.event_mice.values() if not em.is_alive]
            for em in dead_mice:
                logging.info(f"InputManager: Removing dead mouse: {em.path}")
                del self._mouse_handler.event_mice[em.path]

            for device in self._hid_scanner.keyboard_devices:
                if device.path not in self._keyboards:
                    logging.info(f"InputManager: New keyboard: {device.path} ({device.name})")
                    kb = KeyboardHandler(
                        device, self._bt_server, self._hotkey_detector, self._host_switch_cb)
                    self._keyboards[device.path] = kb
                    asyncio.create_task(kb.run())

            for device in self._hid_scanner.mouse_devices:
                if device.path not in self._mouse_handler.event_mice:
                    logging.info(f"InputManager: New mouse: {device.path} ({device.name})")
                    em = EventMouse(device)
                    em.send_state_cb = self._mouse_handler.send_state
                    self._mouse_handler.event_mice[device.path] = em
                    asyncio.create_task(em.run())

            if not self._hid_scanner.keyboard_devices:
                logging.warning("InputManager: No keyboard found")
            if not self._hid_scanner.mouse_devices:
                logging.warning("InputManager: No mouse found")

            await asyncio.sleep(5)

        logging.info("InputManager: Stopped")
