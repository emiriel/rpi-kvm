# Bug: Mouse less smooth + movement signals lost on fast motion

## Symptoms

1. Mouse movement is noticeably less smooth than before the refactoring (commit 885b9bb).
2. On sudden fast movements, the cursor travels roughly half the expected distance
   (signals appear lost or clamped).

## Relevant files

- `rpi_kvm/input_handler.py` — `EventMouse`, `MouseHandler.send_state`
- `rpi_kvm/usb_hid_decoder.py` — `enshure_byte_size`
- `rpi_kvm/kvm_service.py` — main event loop, shared with BT and keyboard

---

## Root cause hypothesis A — shared event loop contention (smoothness regression)

**Before** (commit 884 and earlier): `mouse.py` was a **separate process** with its own
dedicated asyncio event loop. Mouse events were its only concern. The separate process
had its own GIL context, so BT socket operations, D-Bus reconnects, and keyboard events
running in kvm_service.py did not compete with mouse event processing.

**After**: `InputManager`, `KeyboardHandler`, `EventMouse`, `BtServer`, `BtClient`, and
`KvmDbusService` all run in the **same asyncio event loop** in a single process. Python's
asyncio is cooperative and single-threaded. Any task that holds the event loop for more
than ~20ms (the mouse update rate) will delay mouse event delivery.

Known tasks that could cause delays:
- `BtClient._switch_to_master()` calls `exec_cmd("hcitool sr ...")` via subprocess. While
  this runs in an executor thread (non-blocking), many concurrent executor calls can
  saturate the thread pool, delaying mouse event callbacks.
- `BtClient._send_periodic_alive_messages()` runs every 4 seconds per client and calls
  `sock_sendall` which may temporarily stall if the BT socket's send buffer is full.
- `_listen_for_incomming_requests()` has `await asyncio.sleep(3)` inside the TimeoutError
  handler, which is fine (yields the loop), but the surrounding try/except structure
  prevents overlapping BT work from running.

### Investigation steps

1. Add timing instrumentation to measure how long the event loop is actually blocked.
   A simple approach: in `EventMouse._event_loop()`, record `time.monotonic()` before and
   after each `await self._handle_event(event)`. If the gap between consecutive EV_REL
   events grows beyond 2–3ms, the event loop is being starved.

2. Run `asyncio.get_event_loop().set_debug(True)` and watch for "Executing ... took ... ms"
   warnings. asyncio slow-callback detection fires at 100ms by default but can be tuned:
   ```python
   import asyncio
   asyncio.get_event_loop().slow_callback_duration = 0.010  # warn at 10ms
   ```

3. Check if the issue disappears when only the mouse is connected (no BT clients) — this
   would confirm that BT client tasks are the source of contention.

### Fix direction

Option A: Run `InputManager` (and specifically `EventMouse.run()`) in a **dedicated
thread with its own event loop**, communicating with the main loop via
`asyncio.run_coroutine_threadsafe`. This restores the pre-refactoring isolation.

Option B: Increase the priority of the mouse-related asyncio tasks using a custom
event loop policy, or run the mouse in a `ProcessPoolExecutor` subprocess.

Option C (lighter): Pin the `async for event in self._idev.async_read_loop()` to run
more aggressively by adding explicit `await asyncio.sleep(0)` yields between processing
runs to give it higher scheduling priority. (This is a hack, not a real fix.)

---

## Root cause hypothesis B — `enshure_byte_size` clamping on fast movement

`MouseHandler.send_state` (input_handler.py:216):
```python
x_byte = UsbHidDecoder.enshure_byte_size(x_pos)
y_byte = UsbHidDecoder.enshure_byte_size(y_pos)
```

`x_pos` is the ACCUMULATED displacement since the last EV_SYN that was not throttled.
The USB HID mouse report uses a **signed byte** (−128 to 127). If the mouse moves quickly
enough that `x_pos` exceeds ±127 between two 20ms windows, `enshure_byte_size` clamps it.

This was the same behavior in the old code. However, the old `mouse.py` had an inherent
delay from the D-Bus round trip (~1–3ms per call). That delay meant `send_state_cb`
was awaited for 1–3ms, during which NEW mouse events arriving in the kernel buffer were
not yet processed. They would be accumulated in the NEXT `_x_pos` / `_y_pos` cycle.

In the new code, `send_state_cb` (= `MouseHandler.send_state`) is essentially instantaneous.
The event loop processes the next batch of EV_REL events immediately. This means
accumulation BETWEEN SYN events is smaller (each SYN triggers a faster flush), so each
`x_pos` is more likely to stay in range.

**However**: if hypothesis A is correct and the event loop is sometimes starved, the
opposite happens — EV_SYN events are delayed, `_x_pos` accumulates more than expected,
and clamping is MORE aggressive. This would explain "cursor makes half the distance."

### Investigation steps

1. Log `x_pos` and `y_pos` before clamping in `MouseHandler.send_state`:
   ```python
   if abs(x_pos) > 127 or abs(y_pos) > 127:
       logging.warning(f"Mouse: clamping large movement x={x_pos} y={y_pos}")
   ```
   If this fires frequently during fast movement, clamping is the direct cause of
   the lost distance.

2. Cross-reference with hypothesis A timing logs to see if clamping coincides with
   event loop stalls.

### Fix direction

The signed-byte limit is a constraint of the USB HID mouse report format (report ID 2).
The proper fix is to **split large movements into multiple reports**, each within the
±127 range, until the full distance is covered:

```python
async def send_state(self, buttons, x_pos, y_pos, v_wheel, h_wheel):
    ...
    while abs(x_pos) > 0 or abs(y_pos) > 0:
        x_chunk = max(-127, min(127, x_pos))
        y_chunk = max(-127, min(127, y_pos))
        telegram = [0xA1, 2, buttons_byte, x_chunk & 0xFF, y_chunk & 0xFF, v_byte, h_byte]
        self._bt_server.send(telegram)
        x_pos -= x_chunk
        y_pos -= y_chunk
        v_byte = 0  # only send wheel on first chunk
        h_byte = 0
```

Note: this should only be needed for sudden large bursts. Normal tracking at 50Hz
typically stays well within ±127 per frame.

---

## Root cause hypothesis C — `_continuous_sync_event` sleep interval interaction

`EventMouse._continuous_sync_event` (input_handler.py:149) sleeps for 1 second and then
injects a synthetic EV_SYN to flush any pending state. This is a failsafe for when
the mouse is idle or EV_SYN events stop arriving.

In the shared event loop, `asyncio.sleep(1)` might wake up slightly late if the loop is
busy. In practice this should not affect smoothness during active movement (where real
EV_SYN events arrive at the hardware rate).

However: the synthetic SYN has code 55 and value 55, which is unconventional.
`_handle_event` checks `event.type == ecodes.EV_SYN` but does NOT check `event.code`.
Verify that `ecodes.EV_SYN` is still the correct constant for the synthetic event type
(it should be 0). Code 55 is EV_SYN subtype SYN_MT_REPORT, not SYN_REPORT (0) — this
might not trigger the flush path correctly on all kernel versions.

### Investigation steps

Check whether the synthetic event reaches the flush path:
```python
if event.type == ecodes.EV_SYN:
    logging.debug(f"EV_SYN received: code={event.code} value={event.value}")
```

If code 55 (SYN_MT_REPORT) behaves differently from code 0 (SYN_REPORT) in terms of
how evdev async_read_loop generates it, there may be a mismatch. Use `ecodes.SYN_REPORT`
(= 0) for the synthetic event code instead.

---

## Summary: most likely cause chain

1. Event loop is occasionally starved by BT client tasks (hypothesis A).
2. During a stall, EV_REL events accumulate in the kernel buffer.
3. When the event loop resumes, EV_SYN arrives with a large accumulated `x_pos`/`y_pos`.
4. `enshure_byte_size` clamps the value → cursor moves less than expected (hypothesis B).

Fix hypothesis A (event loop isolation) and hypothesis B (chunked sending) together for
full resolution.
