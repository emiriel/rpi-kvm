# Component Design

Overview of each rpi-kvm component. See [System Overview](system-overview.md)
for the high-level architecture.

## Core Service

### `kvm_service.py` — KvmDbusService (orchestrator)

Owns the whole runtime: instantiates `Settings`, `BtServer`,
`HotkeyDetector`, `UsbHidDecoder` and `InputManager`, registers the
`org.rpi.kvmservice` D-Bus name, and routes USB input to the active
Bluetooth host. Exposes the D-Bus API consumed by the web service
(connect/disconnect/remove clients, switch host, settings reload). Handles
auto-switch: when the active host stays offline for 3s, switches to the next
connected one.

### `bt_server.py` — BtServer (Bluetooth HID device)

Makes the Pi appear as a Bluetooth keyboard/mouse: sets adapter name and
class (`hciconfig`), registers the HID profile (UUID 0x1124) with BlueZ via
`ProfileManager1` using the SDP record in `conf/sdp_record.xml`, listens on
the HID L2CAP ports (control 17, interrupt 19), and manages one `BtClient`
per paired host. On startup it connects to all known devices. Maintains the
persistent client order (`client_order.py`).

### `bt_client.py` — BtClient (one host)

Represents one Bluetooth host. Establishes the outgoing HID channels
(L2CAP 17/19), or accepts incoming ones. Watches the BlueZ `Device1` D-Bus
properties: `ServicesResolved=True` triggers an immediate reconnect (fast
path), and a per-client retry loop attempts reconnection every 5s while the
host is offline (safety net — see
[bluetooth-auto-connection.md](../bluetooth/bluetooth-auto-connection.md)).
Forces the connection role to Master, sends keepalive reports, and queues
outgoing HID reports.

## Input

### `input_handler.py` — InputManager

Scans USB HID devices via evdev (`hid_scanner.py`), reads key/mouse events
and feeds them to the hotkey detector and HID decoder.

### `usb_hid_decoder.py` — UsbHidDecoder

Translates evdev keycodes into Bluetooth HID keyboard/mouse report bytes
(modifier bitmap + usage codes), the wire format sent to hosts.

### `hotkey.py` — HotkeyDetector / HotkeyConfig

Matches configured key combinations (from settings, editable via web UI)
against the input stream and triggers actions (switch to next host,
indicate host).

## Web

### `web.py` — WebService (aiohttp, port 8080)

REST + WebSocket API for the frontend: client list, connect/disconnect/
remove/order clients, switch host, settings, keyboard codes, update
check/perform, clipboard endpoints. Serves the built React app from
`web/build/`. Talks to the core service over D-Bus.

### `clipboard.py` — Clipboard

Shared clipboard history (max 5 entries, 5min expiration) exchanged with
hosts through the web UI.

## Extras

### `info_hub.py` — InfoHub / `lcd.py` — LcdDisplay

HD44780 LCD display showing previous/current/next hosts, driven via D-Bus
signals from the core service.

### `touch_phat.py` — Touch pHAT

Pimoroni Touch pHAT buttons mapped to actions (e.g. switch host), run as
its own systemd service.

### `settings.py` — Settings

JSON-backed settings (web port, hotkeys, touchphat mapping) stored in the
gitignored `conf/rpi-kvm-settings.json`.

### `client_order.py` — PersistentClientOrder

Persisted ordering of Bluetooth clients (gitignored
`conf/rpi-kvm-client-order.json`).

## Extension Points

- New hotkey actions: add to `HotkeyAktion` in `hotkey.py`, wire in
  `KvmDbusService`.
- New web API endpoints: add routes in `web.py` and a D-Bus method on
  `KvmDbusService` when core state is involved.
- New display/hardware: implement a handler registered on
  `BtServer.register_on_clients_change_handler` like `InfoHub` does.
