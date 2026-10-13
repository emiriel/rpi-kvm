# Data Flow

How data moves through rpi-kvm. See [System Overview](system-overview.md)
for the big picture and [bluetooth-auto-connection.md](../bluetooth/bluetooth-auto-connection.md)
for the connection flows.

## Input Flow (USB → Bluetooth host)

```
USB keyboard/mouse
  │ evdev events (/dev/input/event*)
  ▼
InputManager (input_handler.py)          hotkey matched? ──► HotkeyDetector
  ▼                                            │
UsbHidDecoder (usb_hid_decoder.py)              └─► KvmDbusService:
  ▼                                             switch active host
HID report bytes (keyboard/mouse)
  ▼
BtServer.send() → active BtClient message queue
  ▼
L2CAP interrupt channel (PSM 19) → active host
```

Every connected host gets its own `BtClient`; only the active host's queue
is fed. The hotkey check happens on the decoded stream, before the report
is forwarded, so switch hotkeys never leak to the host.

## Connection Flows

### Host connects to the Pi (pairing)

```
Host OS "add device" → pairs → SDP sees HID record (conf/sdp_record.xml)
  → host opens L2CAP 17/19 → BtServer accept → BtClient.accept_connection()
```

### Pi connects to the host (auto-reconnect)

```
Fast path:  host pages Pi → BlueZ ServicesResolved=True → BtClient.connect()
Safety net: host silent  → per-client retry loop every 5s → BtClient.connect()
  → both: L2CAP 17/19 to host → role switch to Master → keepalive every 4s
```

## Control Flow (web UI → core)

```
Browser (web/build, served on :8080)
  │ REST / WebSocket
  ▼
WebService (web.py)
  │ D-Bus (org.rpi.kvmservice)
  ▼
KvmDbusService (kvm_service.py)
  │                        ┌──► D-Bus signal (clients/host change)
  ▼                        ▼
BtServer (bt_server.py)   InfoHub (LCD), Touch pHAT listeners
  ▼
BtClient connect / stop / order change
```

The web UI receives live updates over the `/bt-clients-socket` WebSocket,
fed by the D-Bus signals the core service emits when the connected-client
set or active host changes.

## Switching Logic

1. Hotkey detected (or web UI / Touch pHAT button) → `SwitchActiveHost` or
   `SwitchToNextConnectedHost`.
2. `BtServer.switch_active_host_to()` / next-in-order from
   `PersistentClientOrder`.
3. Subsequent HID reports are routed to the new active client; D-Bus
   signals propagate the change to web UI and LCD.
4. If the active host goes offline, the auto-switch task waits 3s, then
   falls back to the next connected host (the offline host keeps retrying
   in the background and rejoins automatically when it returns).
