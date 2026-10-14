# Self-Update via Polling

rpi-kvm keeps itself current by polling its origin remote: no inbound
ports, no exposed services, no secrets to manage.

## How It Works

```
rpi-kvm-autoupdate.timer (every 5 min)
  → scripts/autoupdate.sh
      git fetch origin
      HEAD != origin/main?  → git reset --hard origin/main
                            → re-apply __INSTALL_DIR__ in web.py
                            → restart core/web/infohub/touchphat
```

The Pi initiates every connection, so this works behind any NAT without
port forwarding. Public repositories fetch anonymously over HTTPS; the
`origin` of the initial clone determines which repository is deployed.

## Configuration

| Setting | Default | Notes |
|---|---|---|
| `PROJECT_PATH` | `/root/tools/rpi-kvm` | Install directory |
| `AUTOPDATE_BRANCH` | `main` | Tracked branch |
| Poll interval | 5 min | `OnUnitActiveSec` in the timer unit |

## Manual Control

```bash
sudo systemctl start rpi-kvm-autoupdate.service   # run a check now
journalctl -t autoupdate                          # deploy history
```

## Why Polling Instead of a Webhook

The previous design used a Flask webhook receiver: it required the
repository owner to configure a webhook with a shared secret, and the Pi
to be reachable from the internet (port forwarding, static address or
DDNS). The polling design removes all three requirements at the cost of
a few minutes of deploy latency.
