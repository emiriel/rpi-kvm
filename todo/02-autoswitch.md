# Bug: Autoswitch to next host does not trigger

## Symptom

When the active host goes offline and another host is already connected, the RPi
should automatically switch the active host after 7 seconds. This does not happen.

## Relevant files

- `rpi_kvm/kvm_service.py` — `on_clients_change`, `_auto_switch_after_delay`,
  `switch_to_next_connected_host_internal`
- `rpi_kvm/bt_server.py` — `_check_for_client_communication_change`,
  `_get_connected_client_addresses`, `get_connected_client_names`
- `rpi_kvm/bt_client.py` — `_on_properties_changed` (interaction)

---

## Root cause hypothesis A — autoconnect feature cancels the auto-switch task

This is the most likely cause. The autoswitch and the autoconnect feature (commit e69b613)
interact badly.

**The sequence:**

1. HostA (active) disconnects — its `_run()` task exits → `is_alive = False`.
2. `_check_for_client_communication_change()` runs → HostA removed from `_clients_connected`
   → `get_connected_client_names()` returns `["off: HostA", "HostB"]`
   → `on_clients_change(["off: HostA", "HostB"])` fires
   → `_auto_switch_task` is scheduled (7-second delay).
3. **BlueZ fires `Connected = True` for HostA** (the ACL link layer is still up even
   though the HID layer dropped). `_on_properties_changed` triggers `self.connect()`.
   A new `_run()` task starts → **`is_alive = True` again** (briefly).
4. `_check_for_client_communication_change()` runs again (within 5 seconds). HostA
   appears alive → `_clients_connected` re-includes HostA → `get_connected_client_names()`
   returns `["HostA", "HostB"]` (no "off:" prefix)
   → `on_clients_change(["HostA", "HostB"])` fires
   → **`_auto_switch_task.cancel()` is called** — the auto-switch is aborted.
5. The new `_run()` task for HostA fails (HID socket connect fails) → `is_alive = False`
   again. Steps 2–4 repeat in a loop.

The result is that `_auto_switch_task` is repeatedly scheduled and cancelled, never
surviving the full 7 seconds.

### Investigation steps

1. Watch the logs for interleaved patterns:
   ```
   journalctl -u rpi-kvm-core -f | grep -E "auto.switch|BlueZ reports|Connection established|Connection terminated"
   ```
   Look for "BlueZ reports device connected — attempting HID reconnect" appearing between
   "auto-switch" being scheduled and firing.

2. Add a log line in `on_clients_change` when the cancel branch runs:
   ```python
   else:
       if self._auto_switch_task and not self._auto_switch_task.done():
           logging.info("AutoSwitch: task cancelled because clients changed back to non-off")
           self._auto_switch_task.cancel()
   ```

### Fix direction

Option 1: In `on_clients_change`, only cancel the task if the active host is confirmed
`is_connected = True` (not just `is_alive`). `is_alive` reflects the task state;
`is_connected` reflects the actual socket state. A task can be "alive" while the
HID connection has already failed.

Option 2: Make `_auto_switch_after_delay` check `is_connected` (which it already does),
and simply re-schedule itself if cancelled, using a one-shot guard. I.e., don't cancel
on any `clients_change` — let the delay expire and do a live check.

Option 3: In `_on_properties_changed`, only call `connect()` if `_is_bluez_connected`
was previously False (i.e., only on a rising edge, not on re-assertion of an already-True
state). This would prevent spurious reconnect attempts that create brief `is_alive = True`
windows.

---

## Root cause hypothesis B — early return when no second host is connected

This applies when there is only ONE host total and it goes offline.

`_auto_switch_after_delay` calls `switch_to_next_connected_host_internal()`:
```python
def switch_to_next_connected_host_internal(self):
    client_addresses = self._bt_server._get_connected_client_addresses()
    if not client_addresses:
        return   # ← early return, no switch
```

`_get_connected_client_addresses()` returns `None` when `_clients_connected` is empty.
If there is only one host and it goes offline, there are no connected clients and the
function returns without doing anything. The task fires but has no target to switch to.

This is correct behavior (you cannot switch to nothing), but the user may observe the
auto-switch firing silently with no effect, which looks like a bug.

### Investigation steps

Add a log in `_auto_switch_after_delay` when no switch is possible:
```python
if active and not active.is_connected:
    client_addresses = self._bt_server._get_connected_client_addresses()
    if not client_addresses:
        logging.info("Auto-switch: no connected host available to switch to")
        return
    logging.info("Auto-switch: switching")
    self.switch_to_next_connected_host_internal()
```

---

## Root cause hypothesis C — `_clients_connected` not updated at switch time

`switch_to_next_connected_host_internal()` calls `_get_connected_client_addresses()`,
which reads `_clients_connected`. This snapshot is only updated inside
`_check_for_client_communication_change()`, which runs once per ~5-second loop iteration
of `_listen_for_incomming_requests`.

If HostA disconnects during the 5-second gap between two calls to
`_check_for_client_communication_change()`, the disconnect may not yet be reflected in
`_clients_connected` when the switch fires. In this case `_get_connected_client_addresses()`
still includes HostA (which is offline) and the switch logic behaves incorrectly.

The `_auto_switch_after_delay` check (`if active and not active.is_connected`) uses the
live `_is_connected` flag, which IS correct. But then it calls
`switch_to_next_connected_host_internal()` which uses the stale snapshot. If HostA is
still in the stale snapshot, `active_is_connected` evaluates to True, and the code
requires `len(client_addresses) > 1` to switch — which may fail if only HostB is available.

### Investigation steps

Add a log at the start of `switch_to_next_connected_host_internal`:
```python
logging.info(f"switch_internal: client_addresses={client_addresses}, active={active}, active_is_connected={active_is_connected}")
```
