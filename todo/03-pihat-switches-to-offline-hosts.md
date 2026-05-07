# Bug: piHat button switches to offline hosts

## Symptom

Pressing the piHat button (configured as `switch_next_host`) switches the active host
even when the target host is offline / disconnected.

## Relevant files

- `rpi_kvm/touch_phat.py` — `_trigger_action` → calls `SwitchToNextConnectedHost` D-Bus method
- `rpi_kvm/kvm_service.py` — `switch_to_next_connected_host_internal`
- `rpi_kvm/bt_server.py` — `_get_connected_client_addresses`, `switch_active_host_to`

---

## Root cause: stale `_clients_connected` snapshot

`switch_to_next_connected_host_internal` (kvm_service.py:119) calls
`_get_connected_client_addresses()` to get the list of reachable hosts:

```python
def _get_connected_client_addresses(self):
    if self._active_host and len(self._clients_connected) > 0:
        client_addresses = self._clients_order.sort_clients(list(self._clients_connected.keys()))
        ...
        return client_addresses
    else:
        return None
```

`_clients_connected` is a **snapshot** updated only inside
`_check_for_client_communication_change()` (bt_server.py:164), which is called at the
top of each iteration of `_listen_for_incomming_requests`. The loop has a cycle time of
up to **~5 seconds** (2-second accept timeout + 3-second sleep).

If a host goes offline just before the button is pressed, `_clients_connected` may still
include that host for up to 5 seconds. The button press then causes a switch to an offline
host.

`switch_active_host_to()` (bt_server.py:175) sets `_active_host` to the requested client
with no liveness check:
```python
def switch_active_host_to(self, client_address):
    if client_address in self._clients:
        self._active_host = self._clients[client_address]
    self._clients_order.active_client = self._active_host.address
```

The active host is set to the offline client. No HID data reaches the computer.
The web UI then shows the new active host as "off:".

---

## Secondary issue: switch logic can select an offline host even with live data

Even if `_clients_connected` were perfectly up-to-date, `switch_active_host_to()` has
no liveness guard. It will set the active host to any address in `self._clients`, connected
or not. This is by design — `SwitchActiveHost()` is meant to be a raw override — but
`switch_to_next_connected_host_internal()` is supposed to only switch to CONNECTED hosts.
The two functions have mismatched assumptions.

---

## Investigation steps

1. Add a log to `_get_connected_client_addresses` to print the snapshot at the time of
   the button press:
   ```python
   logging.info(f"_get_connected_client_addresses: connected snapshot = {list(self._clients_connected.keys())}")
   ```

2. Compare the snapshot addresses against live `is_alive` state at the same moment:
   ```python
   for addr, client in self._clients.items():
       logging.info(f"  {client.name} ({addr}): is_alive={client.is_alive} is_connected={client.is_connected}")
   ```

3. Check the time between the disconnect and the button press. If it is less than ~5
   seconds, the stale snapshot hypothesis is confirmed.

---

## Fix direction

**Option 1 (minimal): do a live `is_alive` check in `_get_connected_client_addresses`**

Instead of reading `_clients_connected`, iterate `_clients` directly:
```python
def _get_connected_client_addresses(self):
    live_connected = {addr: c for addr, c in self._clients.items() if c.is_alive}
    if not self._active_host or not live_connected:
        return None
    client_addresses = self._clients_order.sort_clients(list(live_connected.keys()))
    ...
    return client_addresses
```

This makes `_get_connected_client_addresses` always return live data.
`_clients_connected` can still exist for signaling purposes (detecting changes).

**Option 2: guard `switch_active_host_to` for the connected-switch case**

In `switch_to_next_connected_host_internal`, verify liveness before calling
`SwitchActiveHost`:
```python
target_client = self._bt_server._clients.get(client_addresses[0])
if target_client and target_client.is_alive:
    self.SwitchActiveHost(client_addresses[0])
else:
    logging.warning("switch_internal: target host is not alive, skipping switch")
```

**Recommended**: Option 1, because it fixes the root cause rather than patching the
call site. It also fixes the same stale-snapshot issue in `get_connected_client_names()`
and `on_clients_change`.
