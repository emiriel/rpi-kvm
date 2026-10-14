# Diagnosing Mouse Stutter and Lost Clicks

Method guide distilled from the Oct 14 2026 investigation, where three
independent causes produced one confusing symptom: RF interference,
an update-rate throttle, and a chunking bug.

## First: Separate the Causes

The same complaint ("the mouse stutters / clicks are lost") can come from
three independent layers. Test them in this order — each has a cheap
decisive test:

| Layer | Symptom signature | Decisive test |
|---|---|---|
| Radio (2.4 GHz) | Comes and goes in episodes of 30 s to minutes, independent of code state; latency is sawtooth (alternating very low / very high) | Disable 2.4 GHz emitters in the room one by one |
| Input pipeline | Constant, reproducible with mouse speed, follows code changes | Telegram timeline from the journal (below) |
| Laptop side | Follows one specific host | Switch active host to another laptop mid-episode |

## The Telegram Timeline (Pipeline Exoneration)

The core service logs every mouse telegram at DEBUG level with
millisecond timestamps (`docs/bluetooth` explains the send path).
With persistent journald, this reconstructs the Pi's send history:

```bash
# Per-second send rate over a window (short-precise = ms timestamps)
sudo journalctl -u rpi-kvm-core --since "15:14:30" --until "15:15:50" \
    -o short-precise --no-pager | grep "sending telegram" \
    | awk '{print $3}' | cut -c1-8 | sort | uniq -c
```

Interpretation:

- **Regular bursts in both smooth and stutter phases, instant drop to the
  ~1/s keepalive when movement stops** → the Pi pipeline is fine; the
  disturbance is downstream (radio link or laptop). This also proves there
  is no send backlog: a backlog would flush as a burst after the episode.
- **Gaps or stalls during the stutter** → the Pi itself is starving; look
  at CPU (watch for per-telegram DEBUG logging on weak Pis — it can emit
  thousands of lines per second), event-loop starvation, USB issues.

Note: make journald persistent first (`/etc/systemd/journald.conf.d/`,
`Storage=persistent`) — the default volatile journal destroys the
evidence on every reboot.

## The RF A/B

The Zero 2 W shares one antenna between Bluetooth and wifi (BCM43430).
Anything transmitting in 2.4 GHz near the Pi competes with the HID link,
and a phone at 15 cm is a jammer even when "idle" (BLE scans, push,
background sync are bursty by nature).

Isolation procedure (each step: test a few minutes, note times with
`echo "stutter on/off"; date`):

1. Laptop hosts on Ethernet or 5 GHz wifi (2.4 GHz wifi on a nearby
   laptop was the dominant interferer in the 2026 investigation)
2. Phones and tablets at least 1 m away from the Pi
3. The Pi's own wifi: disable for a window with a scheduled restore —
   ```bash
   sudo systemd-run --on-active=300 --unit=wifi-restore \
       /usr/bin/nmcli radio wifi on
   sudo nmcli radio wifi off   # auto-restores in 5 min
   ```
4. Measure the Pi's own wifi activity to keep the test honest:
   ```bash
   while true; do echo "$(date +%H:%M:%S) rx=$(cat /sys/class/net/wlan0/statistics/rx_bytes) tx=$(cat /sys/class/net/wlan0/statistics/tx_bytes)"; sleep 1; done
   ```

Correlate the user's stutter timestamps with the traffic counters. In the
2026 case: stutter phases matched 2.4–4.6x higher wifi activity on a
nearby laptop; wifi-off windows were smooth.

If stutter persists with every controllable emitter off, suspect the
access point's other clients (check the box's device list), microwave
ovens, or capture the HCI side with `btmon -t` to see whether the
controller congests (ACL flow control) during episodes.

## Known Code-Level Pitfalls (fixed, kept here as history)

- The original mouse handler throttled updates to **20 ms** (50 Hz):
  fast movements visibly lost frames. Fixed by the 1 ms update rate.
- Sending on **every** SYN event with no throttle flooded the HID queue
  on the Zero 2 W and lost clicks. Keep a rate limit.
- Chunking large movements must carry **button state** through every
  chunk, or clicks during fast movement are lost.
- Per-telegram DEBUG logging is expensive at 1000 reports/s on a
  Zero 2 W; keep it out of production.

## Deployment Verification

Never trust "Deployment complete" alone — a checkout of a commit that
does not contain `scripts/sync-to-pi.sh` makes `deploy_to_rpi.sh` fail
before doing anything (the message is easy to miss through filters).
After every deploy, verify on the Pi:

```bash
grep <marker-of-the-expected-code> /root/tools/rpi-kvm/rpi_kvm/input_handler.py
systemctl show -p ActiveEnterTimestamp rpi-kvm-core   # must be fresh
```
