# AGENTS.md

Guidance for AI agents working in this repository.

## Project

rpi-kvm is a Bluetooth KVM relay for the Raspberry Pi: it captures USB keyboard/mouse input (evdev), routes it to the currently active Bluetooth HID host, and exposes a web UI for status and hotkey configuration. It runs as a set of systemd services on the Pi.

- `rpi_kvm/` — Python 3.7+ asyncio service (main orchestrator: `kvm_service.py`; D-Bus/BlueZ: `bt_client.py`, `bt_server.py`; input: `input_handler.py`, `usb_hid_decoder.py`, `hotkey.py`; web backend: `web.py`; LCD/Touch pHAT extras; `common.py` shared helpers)
- `web/` — Create React App frontend in TypeScript (React 17, Bootstrap). Talks to the Python web service on port 8080
- `tests/` — pytest suite (`tests/pytest.ini`); `conftest.py` adds repo root to `sys.path`
- `systemd/`, `conf/`, `scripts/` — deployment units, D-Bus/SDP config, install/start scripts (`rpi-kvm.sh` is the entry point)
- `docs/` — architecture, Bluetooth internals, development guides; check here before designing changes

## Commands

### Python tests

```bash
python3 -m pytest tests/ -v            # unit tests (mocked D-Bus, run anywhere)
python3 -m pytest tests/ -v -m integration   # needs real BlueZ + D-Bus system bus
./run_tests.sh                        # runs the suite inside the Vagrant VM (ubuntu/jammy64)
```

- Markers: `integration` (BlueZ/D-Bus required), `slow`, `hardware` (real BT hardware — skip by default)
- `asyncio_mode = auto`; async tests need no explicit marker
- Dependencies: `pytest`, `dbus-next` (install without `--break-system-packages` on Ubuntu 22.04)

### Web

```bash
cd web
npm start    # dev server on :3000
npm test     # jest via react-scripts
npm run build
```

Prettier config lives in `web/.prettierrc.js`.

### On the Pi

```bash
sudo ./rpi-kvm.sh install | start | restart | attach | kill
```

### Install and deploy over ssh

Two install approaches share the common on-Pi installer (`scripts/install.sh`)
and the ssh transport (`scripts/sync-to-pi.sh`):

- **ssh (from the dev machine, no GitHub)**: `./scripts/install-from-ssh.sh`
  syncs the working tree to the Pi and runs the installer remotely.
  `./deploy_to_rpi.sh` (gitignored, local) does the sync plus service restart
  for redeploying after each change.
- **git (on the Pi)**: after a clone/pull, `sudo ./rpi-kvm.sh install` runs
  `scripts/install-from-git.sh`, which aborts if the tree has modifications
  beyond the `__INSTALL_DIR__` placeholder substitutions.

`RPI_KVM_HOST` (default `rpi-kvm.home`) and `RPI_KVM_REMOTE_DIR`
(default `/root/tools/rpi-kvm`) configure both. The Pi's tree carries no
`.git` anymore: the ssh sync is the source of truth there, and the former
divergent Pi-side history is preserved locally under `refs/remotes/pi/main`.
`deployment/` on the Pi is Pi-local work (webhook receiver) absent from this
repo; sync excludes it — import it before removing the exclude.

## SSH access

This project runs in a container with a configured SSH client.

- Reachable machines are the `Host` blocks in `~/.ssh/config` (other than
  `jump`). That file is the source of truth — machines not listed there
  are NOT reachable; do not invent hostnames.
- `ssh <machine>` works directly: the jump is automatic (ProxyJump), no
  extra options needed. `scp` and `sftp` behave the same.
- `Host jump` is the bastion itself: direct login always fails by design.
  Never run `ssh jump`.
- Always connect with the plain machine name; do not bypass the config
  (`ssh -F /dev/null`, `ProxyJump=none`, raw IPs).
- `~/.ssh` is a read-only mount by design: `known_hosts` lives in
  `/tmp/ssh_known_hosts`. Never try to write to `~/.ssh`.

## Conventions and gotchas

- **Dual import pattern**: modules use `try: from . import common` / `except ImportError: import common`. Keep it — systemd runs `kvm_service.py` directly as a script (`WorkingDirectory=__INSTALL_DIR__`), so both package and flat imports must work. Follow this pattern for any new intra-package import.
- Most modules import siblings flat (`from settings import Settings`), matching the script-style deployment; don't refactor to package-only imports.
- `conf/rpi-kvm-settings.json` and `conf/rpi-kvm-client-order.json` are runtime-generated and gitignored; never edit or commit them.
- Python style: asyncio for concurrency, type hints preferred, descriptive names (see `docs/development/code-style.md`).
- Runtime dependencies (evdev, dbus-next, BlueZ) are Pi/hardware specific; unit tests must mock D-Bus and hardware, not require them.
- Target deployment is a Raspberry Pi (systemd units reference `__INSTALL_DIR__` placeholders filled by `scripts/install.sh`); don't assume a general Linux desktop environment.

