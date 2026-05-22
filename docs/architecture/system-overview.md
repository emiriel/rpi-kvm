# System Overview

## High-Level Architecture

rpi-kvm is a Bluetooth HID relay that enables one physical keyboard/mouse to control multiple computers.

```
┌─────────────────┐
│   USB Keyboard  │
│   USB Mouse     │
└────────┬────────┘
         │ USB HID
         │
┌────────▼─────────────────────────────────────┐
│  Raspberry Pi (rpi-kvm)                       │
│  ┌──────────────────────────────────────┐    │
│  │  USB Input Handler (evdev)           │    │
│  │  - Captures keyboard/mouse events    │    │
│  │  - Decodes USB HID reports           │    │
│  └──────┬───────────────────────────────┘    │
│         │                                     │
│  ┌──────▼───────────────────────────────┐    │
│  │  KVM Service (main orchestrator)     │    │
│  │  - Manages active host               │    │
│  │  - Routes input to active client     │    │
│  │  - Handles hotkeys                   │    │
│  └──┬────────────┬──────────────────────┘    │
│     │            │                            │
│  ┌──▼────────┐   │  ┌──────────────────┐     │
│  │ BT Server │   │  │  Web Server      │     │
│  │ (Listen)  │   │  │  (HTTP/WS)       │     │
│  └──┬────────┘   │  └──────────────────┘     │
│     │            │                            │
│  ┌──▼────────────▼──────────────────────┐    │
│  │  BT Clients (one per paired host)    │    │
│  │  - Maintains HID connection          │    │
│  │  - Sends HID reports                 │    │
│  │  - Monitors D-Bus for auto-reconnect │    │
│  └──┬────────────────────────────────────┘    │
│     │ Bluetooth HID (L2CAP ports 17/19) │    │
└─────┼────────────────────────────────────┘    │
      │                                         │
      │                                         │
┌─────▼──────┐  ┌──────────┐  ┌──────────┐    │
│  Laptop 1  │  │ Laptop 2 │  │ Desktop  │    │
│  (Host)    │  │ (Host)   │  │ (Host)   │    │
└────────────┘  └──────────┘  └──────────┘    │
```

## Core Components

### 1. Input Handler (`input_handler.py`)

**Purpose**: Capture physical USB keyboard/mouse input

- Uses `evdev` to read from `/dev/input/event*`
- Decodes USB HID reports
- Forwards events to KVM Service
- Handles special hotkeys

### 2. KVM Service (`kvm_service.py`)

**Purpose**: Central orchestrator

- Manages list of connected Bluetooth clients
- Maintains "active client" (currently receiving input)
- Routes input events to active client
- Implements hotkey switching (e.g., Ctrl+Shift+1/2/3)
- Coordinates auto-switch logic

### 3. Bluetooth Server (`bt_server.py`)

**Purpose**: Accept incoming Bluetooth connections

- Listens for pairing requests
- Publishes HID service via SDP (Service Discovery Protocol)
- Creates `BtClient` instances for paired hosts
- Handles incoming L2CAP connections from hosts

### 4. Bluetooth Client (`bt_client.py`)

**Purpose**: Maintain HID connection to one host

- Opens L2CAP sockets (ports 17 control, 19 interrupt)
- Sends HID reports (keyboard/mouse data)
- Monitors D-Bus for BlueZ property changes
- Implements auto-reconnect when host comes online
- Ensures "master" role for stable connection

### 5. Web Server (`web.py`)

**Purpose**: Provide web UI and API

- HTTP server with REST API
- WebSocket for real-time updates
- Shows connected hosts, active host
- Allows switching between hosts
- Configuration UI for hotkeys, settings

### 6. Display Modules (Optional)

- `lcd.py`: HD44780 LCD display support
- `touch_phat.py`: Pimoroni Touch pHAT integration
- Show active host on physical display
- Hardware buttons for switching

## Data Flow

### Input Flow (USB → Bluetooth)

```
USB Device → evdev → Input Handler → KVM Service → Active BT Client → Host
```

### Switching Flow (User hotkey)

```
Hotkey detected → Input Handler → KVM Service → Set active client → Update displays
```

### Auto-Connect Flow (Host boots)

```
Host boots → BlueZ detects (RSSI) → BlueZ connects (ACL) → ServicesResolved signal
→ BT Client detects → Opens HID sockets → Connection established → KVM Service notified
```

## Key Technologies

### Linux

- **BlueZ**: Bluetooth stack
- **D-Bus**: IPC for BlueZ communication
- **evdev**: Input device access
- **systemd**: Service management
- **tmux**: Session management (optional)

### Python

- **asyncio**: Async event loop
- **dbus-next**: D-Bus client
- **evdev**: Input device library
- **aiohttp**: Web server
- **socket**: Low-level Bluetooth sockets

### Bluetooth Protocols

- **HID Profile**: Human Interface Device
- **L2CAP**: Logical Link Control and Adaptation Protocol
- **SDP**: Service Discovery Protocol

## State Management

### Client States

Each `BtClient` tracks:
- `is_alive`: Connection active
- `is_connected`: HID sockets open
- `_is_bluez_connected`: BlueZ ACL connection
- `_services_resolved`: Service discovery complete

### KVM States

`KvmService` tracks:
- Active client (which host receives input)
- Connected clients list
- Auto-switch enabled/disabled
- Last active client (for fallback)

## Concurrency Model

All components use Python `asyncio`:

- Single event loop per process
- Async I/O for sockets, D-Bus, input
- Tasks for each client connection
- Queues for message passing

Example:
```python
# Each BT client runs as async task
client = BtClient(address)
client.connect()  # Creates asyncio.Task

# KVM service routes input asynchronously
await active_client.send(hid_report)
```

## Configuration Files

- `/etc/bluetooth/main.conf`: BlueZ configuration
- `conf/sdp_record.xml`: HID service descriptor
- `systemd/rpi-kvm-core.service`: systemd unit file
- `web/`: Web UI static files

## Next Steps

- [Component Design](components.md) - Detailed component docs
- [Data Flow](data-flow.md) - Sequence diagrams
- [Bluetooth Details](../bluetooth/bluetooth-auto-connection.md)
