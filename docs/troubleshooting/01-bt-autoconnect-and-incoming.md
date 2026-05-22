# Bug: Bluetooth autoconnect fails + incoming connections not recognized

## Symptoms

1. When a paired computer comes back online, the RPi does not automatically reconnect.
2. When the computer initiates the connection itself, the RPi either silently drops it
   or never updates `_clients_connected`, so the web UI shows the host as offline and
   the user cannot set it as the active host.

## Relevant files

- `rpi_kvm/bt_client.py` — `_on_properties_changed`, `accept_connection`, `_run`
- `rpi_kvm/bt_server.py` — `_listen_for_incomming_requests`, `_add_client`, `_check_for_client_communication_change`

---

## Root cause hypothesis A — autoconnect: timing mismatch between BlueZ ACL and HID layer

`_on_properties_changed` (bt_client.py:160) fires when BlueZ reports `Connected = True`.
This happens at the **ACL link layer** level — the Bluetooth radio link is established.
But the HID profile (L2CAP ports 17 and 19) may not be ready yet on the remote computer.

`self.connect()` (bt_client.py:85) immediately tries to open L2CAP sockets:
```python
self._control_socket.connect((self.address, self.BT_CONTROL_PORT))   # port 17
self._interrupt_socket.connect((self.address, self.BT_INTERRUPT_PORT))  # port 19
```

If the computer's HID service is not yet accepting connections, `_establish_socket_connection`
raises an exception → `_disconnect()` is called → `_run()` exits → `is_alive = False`.

There is **no retry**. If BlueZ does not fire another `Connected` event, the RPi never
tries again. In practice, BlueZ only fires one `Connected = True` per reconnection.

### Investigation steps

1. Add a log line at the top of `_on_properties_changed` to confirm the event fires:
   ```
   journalctl -u rpi-kvm-core -f | grep "D-Bus bluez property changed"
   ```
2. Check whether the connect attempt is logged right after:
   ```
   grep "attempting HID reconnect\|Exception during connect\|Connection established"
   ```
3. If "attempting HID reconnect" appears but "Connection established" does not,
   the socket connect is failing. Check the exception message in "Exception during connect".
4. Try adding a `asyncio.sleep(2)` delay before the socket connect attempt in
   `_establish_socket_connection` when pre-supplied sockets are absent — this gives the
   remote HID service time to start.

### Fix direction

Add a retry loop inside `_on_properties_changed` or inside `_run()` itself.
When `_establish_socket_connection` fails AND `_is_bluez_connected` is True,
sleep a few seconds and try again, up to N retries.

Alternatively: after `_run()` exits with `_is_connected = False`, check
`_is_bluez_connected` and schedule a deferred `connect()` call.

---

## Root cause hypothesis B — autoconnect: `asyncio.create_task()` context

`_on_properties_changed` is a **synchronous** method registered as a dbus-next signal
callback. The call chain is:
```
dbus-next message dispatch → _on_properties_changed (sync) → self.connect() → asyncio.create_task(self._run())
```

`asyncio.create_task()` requires the call to happen **from a coroutine or from a callback
scheduled on the event loop** (not from an arbitrary thread). Depending on how dbus-next
dispatches signal callbacks internally (which varies by version), this may fail silently:
the `create_task()` call might return a task that was never actually scheduled, or raise
a RuntimeError that is swallowed.

### Investigation steps

1. Check the dbus-next version:
   ```
   pip show dbus-next
   ```
2. Add explicit error handling around `self.connect()` in `_on_properties_changed`:
   ```python
   try:
       self.connect()
       logging.info(f"{self._name}: connect() called successfully from property change callback")
   except Exception as e:
       logging.error(f"{self._name}: connect() failed in callback: {e}")
   ```
3. Alternatively, change the implementation to use `asyncio.get_event_loop().call_soon_threadsafe(self.connect)`
   to ensure it is safe regardless of which thread dbus-next uses.

---

## Root cause hypothesis C — incoming connections: `accept_connection()` silent guard

`accept_connection` (bt_client.py:90):
```python
def accept_connection(self, control_socket, interrupt_socket):
    if not self._task or self._task.done():
        ...
```

If the old `_task` is still running (i.e., the previous disconnection has not been
detected yet), this guard silently does nothing. The accepted sockets are neither stored
nor closed — they are leaked. The computer thinks it connected successfully but the RPi
ignores the new sockets.

**When does this happen?** `_send_periodic_alive_messages` (bt_client.py:214) sends a
keepalive every **4 seconds**. The socket error is only detected on the NEXT send attempt
after the connection drops. So there is a window of up to 4 seconds where `_task` is
still alive (no error yet) but the remote connection is already dead. If the computer
reconnects during those 4 seconds, the new connection is dropped.

### Investigation steps

1. Add a log at the top of `accept_connection` to check whether it is being called
   and whether the guard fires:
   ```python
   logging.info(f"{self._name}: accept_connection called — task alive: {not (not self._task or self._task.done())}")
   ```
2. If the guard fires, check the task age by logging `self._task` state.

### Fix direction

When `accept_connection` is called for an already-running task, explicitly stop the old
task before starting the new one. The computer is attempting a fresh connection — honor it:
```python
def accept_connection(self, control_socket, interrupt_socket):
    if self._task and not self._task.done():
        logging.info(f"{self._name}: Incoming connection while task alive — stopping old task")
        self._stop_event = True
        self._disconnect()
    self._control_socket = control_socket
    self._interrupt_socket = interrupt_socket
    self._stop_event = False
    self._task = asyncio.create_task(self._run())
```

---

## Root cause hypothesis D — incoming connections: control/interrupt socket mismatch

`_listen_for_incomming_requests` (bt_server.py:103):
```python
client_control_socket, (client_address, _) = await asyncio.wait_for(
    self._loop.sock_accept(self.control_socket), timeout=2)
client_interrupt_socket, (client_address, _) = await asyncio.wait_for(
    self._loop.sock_accept(self.interrupt_socket), timeout=2)
```

If the control accept succeeds but the interrupt accept times out (TimeoutError):
- The accepted control socket is abandoned (not closed, not stored).
- The server sleeps 3 seconds.
- On the next iteration it tries to accept a **new** control socket.

Meanwhile, the computer's interrupt socket connection is sitting in the listen backlog.
On the next iteration: a second control attempt might arrive → accepted as "control".
Then the **first** interrupt socket (from the previous attempt) is popped off the backlog
and accepted as "interrupt". The two sockets now belong to **different connection attempts**
and may have different client addresses.

### Investigation steps

1. Log `client_address` for both accept calls and confirm they match:
   ```python
   logging.debug(f"Server: Accepted control from {ctrl_addr}, interrupt from {intr_addr}")
   if ctrl_addr != intr_addr:
       logging.error(f"Server: MISMATCH control={ctrl_addr} interrupt={intr_addr}")
   ```
2. Check whether the computer's two sockets always arrive close together or if
   there is a delay between them.

### Fix direction

Accept both sockets in the same wait_for call or use a longer timeout for the interrupt
accept. If addresses mismatch, close both sockets and try again. Alternatively, use
a coroutine that accepts both in a single pass with a combined timeout.

---

## Root cause hypothesis E — `_clients_connected` stale at notification time

`_add_client` (bt_server.py:150) calls `_notify_on_clients_change()` which calls
`get_connected_client_names()`. At this point `_clients_connected` may not yet include
the new client because `_check_for_client_communication_change()` hasn't run since the
client was added.

For the **outgoing** path (`_connect_to_client`), `connect()` is called before
`_add_client()`, so the task is running when the notification fires — but
`_clients_connected` still has the old snapshot. Result: the first notification shows
the client as "off:" even though it is actually alive.

For the **incoming** path, `_add_client()` is called before `accept_connection()`, so
the task hasn't even started when the notification fires.

### Fix direction

Before calling `_notify_on_clients_change()` inside `_add_client()`, call
`_check_for_client_communication_change()` first to refresh the snapshot.

Or: update `_clients_connected` directly inside `_add_client()` if the client's task
is already alive.
