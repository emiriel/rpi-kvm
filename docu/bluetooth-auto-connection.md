# Bluetooth Auto-Connection: How It Works

This document explains how Bluetooth connections work in the rpi-kvm project, particularly the auto-connection feature that allows hosts to automatically connect when they boot or wake from sleep.

## Table of Contents

1. [Bluetooth Basics](#bluetooth-basics)
2. [BlueZ and D-Bus](#bluez-and-d-bus)
3. [How Bluetooth Connection Happens](#how-bluetooth-connection-happens)
4. [The Auto-Connection Problem](#the-auto-connection-problem)
5. [The Solution: ServicesResolved Signal](#the-solution-servicesresolved-signal)
6. [Implementation Details](#implementation-details)
7. [Key Takeaways](#key-takeaways)

---

## Bluetooth Basics

### What is Bluetooth Pairing?

When you pair two Bluetooth devices, they:
1. Exchange cryptographic keys
2. Store each other's information (name, address, capabilities)
3. Remember each other for future connections

After pairing, devices don't need to go through the pairing process again.

### Connection vs. Pairing

- **Pairing**: One-time setup where devices establish trust (exchange keys)
- **Connection**: Active communication session between paired devices

Think of pairing like exchanging phone numbers, and connection like actually making a call.

### Bluetooth Roles

In Bluetooth, there are different roles:

- **HID Device** (Human Interface Device): Keyboard, mouse, game controller, etc.
  - In our case: **rpi-kvm acts as a HID device** (it emulates a keyboard/mouse)

- **HID Host**: Computer, phone, tablet that receives input
  - In our case: **Your laptop/desktop is the HID host**

### The Challenge

Normally:
- Hosts (computers) **connect TO** HID devices (keyboards/mice)
- HID devices **wait for** hosts to connect to them

This means when your computer boots up, it expects the keyboard to be waiting. But for auto-connection, we need the **keyboard (rpi-kvm) to proactively connect to the computer** when it detects the computer is available.

---

## BlueZ and D-Bus

### What is BlueZ?

**BlueZ** is the official Linux Bluetooth stack. It handles all the low-level Bluetooth operations:
- Managing the Bluetooth adapter (hci0)
- Discovering nearby devices
- Pairing and connecting
- Managing Bluetooth profiles (HID, audio, etc.)

### What is D-Bus?

**D-Bus** is an inter-process communication (IPC) system on Linux. It allows different programs to communicate with each other.

BlueZ exposes its functionality through D-Bus, which means:
- You can control BlueZ from Python (or any language)
- You can monitor Bluetooth events in real-time
- You get **signals** (notifications) when things change

### D-Bus Properties and Signals

**Properties** are values you can read/watch:
- `Connected`: Is the device currently connected?
- `ServicesResolved`: Has service discovery completed?
- `RSSI`: Signal strength (how close is the device?)
- `Name`: Device name
- `Address`: Bluetooth MAC address

**Signals** are events that BlueZ sends when something changes:
- `PropertiesChanged`: A property value changed
- Example: When a device connects, BlueZ sends a signal saying `Connected` changed from `False` to `True`

---

## How Bluetooth Connection Happens

Here's the **complete sequence** when a host (your computer) boots or wakes from sleep:

### Step 1: Device Powers On
```
Your laptop boots
    ↓
Bluetooth radio turns on
    ↓
Starts advertising its presence
```

### Step 2: Discovery
```
rpi-kvm's Bluetooth adapter (BlueZ) detects the signal
    ↓
RSSI property updates (signal strength detected)
    ↓
BlueZ says: "I see a device nearby!"
```

### Step 3: Recognition
```
BlueZ checks: "Is this a paired device?"
    ↓
Yes! It's a known device
    ↓
BlueZ initiates base-level Bluetooth connection
```

### Step 4: Connection Established
```
Base Bluetooth connection established
    ↓
Connected property changes to True
    ↓
BlueZ says: "We have a connection!"
```

### Step 5: Service Discovery
```
BlueZ performs "Service Discovery"
    ↓
Queries: "What services does this device support?"
    ↓
Discovers: HID, Audio, Network, etc.
    ↓
ServicesResolved property changes to True
    ↓
BlueZ says: "Device is ready for use!"
```

### Step 6: HID Connection
```
rpi-kvm detects ServicesResolved = True
    ↓
Opens HID control socket (port 17)
    ↓
Opens HID interrupt socket (port 19)
    ↓
HID connection established!
    ↓
Keyboard/mouse input can now flow
```

---

## The Auto-Connection Problem

### The Original Approach (Didn't Work Well)

**Problem**: When your computer boots, it doesn't automatically connect to the rpi-kvm.

**Why?**:
- Computers expect keyboards to wait for them
- They don't proactively connect to paired keyboards
- The rpi-kvm needs to initiate the connection instead

### First Attempt: Hardcoded Delays

The initial implementation used **timers** with hardcoded delays:

```python
# When we detect RSSI (device nearby)
asyncio.get_event_loop().call_later(2.0, try_reconnect)

# When we detect Connected=True
asyncio.get_event_loop().call_later(1.0, try_reconnect)

# After disconnect
asyncio.get_event_loop().call_later(5.0, try_reconnect)
```

**Problems with this approach**:
1. **Arbitrary delays**: Why 2 seconds? Why not 1 or 3?
2. **Race conditions**: We might try to connect before the device is ready
3. **Slow**: We wait even when the device is already ready
4. **Unreliable**: Different devices might need different delays

---

## The Solution: ServicesResolved Signal

### The Proper Bluetooth Way

Instead of guessing with timers, we **listen to BlueZ signals** that tell us exactly when the device is ready.

### ServicesResolved Property

**`ServicesResolved`** is a boolean property that tells you:
- `False`: Service discovery not done yet (device not ready)
- `True`: Service discovery complete (device ready for connections!)

This is the **official signal** from BlueZ that means:
> "This device is fully connected and I know what it can do. You can now use its services."

### Why This is Better

1. **Event-driven**: React immediately when device is ready
2. **No guessing**: BlueZ tells us the exact moment
3. **Fast**: Connect as soon as possible
4. **Reliable**: Works for all devices, regardless of speed

---

## Implementation Details

### Code Structure

The implementation is in `rpi_kvm/bt_client.py`:

#### 1. Track the State

```python
def __init__(self, address):
    # ...
    self._is_bluez_connected = True
    self._services_resolved = False  # Track service discovery state
    # ...
```

#### 2. Query Initial State

When connecting to a device's D-Bus object:

```python
async def _connect_to_dbus_service(self):
    # Get current state
    self._is_bluez_connected = await self._bluez_itf.get_connected()
    self._services_resolved = await self._bluez_itf.get_services_resolved()

    # Monitor for changes
    self._bluez_props.on_properties_changed(self._on_properties_changed)
```

**Why query initial state?**
- When rpi-kvm starts, devices might already be connected
- We need to know the current state, not just future changes

#### 3. Listen for Property Changes

```python
def _on_properties_changed(self, interface_name, changed_properties, invalidated_properties):
    for changed, variant in changed_properties.items():
        if changed == "Connected":
            self._is_bluez_connected = variant.value

        elif changed == "ServicesResolved":
            self._services_resolved = variant.value
            # This is THE signal we care about!
            if variant.value and not self.is_alive and not self._stop_event:
                logging.info(f"{self._name}: Services resolved — initiating HID reconnect")
                self._try_reconnect_if_still_offline()

        elif changed == "RSSI":
            # Just log for debugging - device detected nearby
            logging.debug(f"{self._name}: Device detected nearby (RSSI: {variant.value})")
```

**Key points**:
- We monitor `Connected` to track basic connection state
- We monitor `ServicesResolved` to know when to act
- We monitor `RSSI` for debugging (seeing when device comes into range)

#### 4. Attempt HID Connection

```python
def _try_reconnect_if_still_offline(self):
    # Only connect if services are resolved and we're not already connected
    if self._services_resolved and not self.is_alive and not self._stop_event:
        logging.info(f"{self._name}: Attempting outgoing HID reconnect")
        self.connect()
```

**Safety checks**:
- `self._services_resolved`: Device is ready
- `not self.is_alive`: We're not already connected
- `not self._stop_event`: System isn't shutting down

### The Complete Flow

```
Host boots
    ↓
BlueZ detects RSSI
    ↓ (PropertiesChanged: RSSI=<value>)
rpi-kvm logs: "Device detected nearby"
    ↓
BlueZ establishes connection
    ↓ (PropertiesChanged: Connected=True)
rpi-kvm tracks: _is_bluez_connected = True
    ↓
BlueZ performs service discovery
    ↓ (PropertiesChanged: ServicesResolved=True)
rpi-kvm detects: _services_resolved = True
    ↓
rpi-kvm immediately calls: connect()
    ↓
Opens HID sockets (ports 17, 19)
    ↓
HID connection established!
    ↓
Host can now receive keyboard/mouse input
```

### What About Disconnection?

When a HID connection terminates:

**Before** (with delays):
```python
# After disconnect, wait 5 seconds then try to reconnect
asyncio.get_event_loop().call_later(5.0, self._try_reconnect_if_still_offline)
```

**After** (signal-based):
```python
# No delay needed!
# If device is still available, BlueZ will send ServicesResolved signal
# and we'll reconnect automatically
```

If the device is still there and connected to BlueZ, the `ServicesResolved` property is still `True`, so we could potentially check and reconnect. But if the device went away (like shutdown), BlueZ will send `Connected=False`, and no reconnection attempt happens.

---

## Key Takeaways

### Bluetooth Connection Lifecycle

1. **Discovery**: Device detected via RSSI (signal strength)
2. **Connection**: Base Bluetooth connection established (`Connected=True`)
3. **Service Discovery**: BlueZ learns device capabilities (`ServicesResolved=True`)
4. **Service Usage**: Applications can now use device services (HID, Audio, etc.)

### Event-Driven Programming with D-Bus

- **Don't poll**: Don't repeatedly check if something changed
- **Don't guess with timers**: Don't use arbitrary delays
- **Listen for signals**: React to events from the system

### The Right Signal to Use

For HID connections, wait for:
- ✅ **`ServicesResolved = True`**: Device is ready for service connections
- ❌ **Not `Connected = True`**: Too early, services not discovered yet
- ❌ **Not `RSSI` updates**: Just means device nearby, not ready yet

### Benefits of Signal-Based Approach

1. **Fast**: Connect immediately when ready (no waiting)
2. **Reliable**: Works for all devices at their own pace
3. **Clean code**: No hardcoded delays, no magic numbers
4. **Proper architecture**: Event-driven, reactive design

---

## Further Reading

- [BlueZ D-Bus API Documentation](https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc)
- [Service Discovery Protocol (SDP)](https://www.bluetooth.com/specifications/assigned-numbers/service-discovery/)
- [HID Profile Specification](http://www.yts.rdy.jp/pic/GB002/HID_SPEC_V10.pdf)
- See also: `docu/reading.md` for more Bluetooth resources
