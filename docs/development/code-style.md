# Code Style Guide

## Python (`rpi_kvm/`)

- Python 3.7+ compatible, asyncio for concurrency (no threads except the
  tiny `run_in_executor` wrappers for blocking calls)
- Type hints preferred on new code; descriptive names over comments
- Logging via the `logging` module; levels: DEBUG for expected retries and
  diagnostics, INFO for state transitions, ERROR only for real failures
  (the reconnect loop retries quietly — see
  [bluetooth-auto-connection.md](../bluetooth/bluetooth-auto-connection.md))
- Error handling around external boundaries only (D-Bus, sockets); don't
  over-wrap pure logic

### Imports

- **Dual import pattern** for intra-package imports:

  ```python
  try:
      from . import common
  except ImportError:
      import common
  ```

  Keep it: systemd runs `kvm_service.py` directly as a script
  (`WorkingDirectory=__INSTALL_DIR__`), so both package and flat imports
  must work. Follow this pattern for any new intra-package import.
- Most modules import siblings flat (`from settings import Settings`),
  matching the script-style deployment; don't refactor to package-only
  imports.

### Tests

- Unit tests must mock D-Bus and hardware (see `tests/conftest.py`), never
  require BlueZ or a real adapter
- Async tests need no marker (`asyncio_mode = auto` in `tests/pytest.ini`)
- Integration/hardware tests carry the `integration` / `hardware` markers

## Shell (`scripts/`, root scripts)

- `set -euo pipefail` for anything non-trivial
- One purpose per script; shared logic extracted (e.g. the ssh transport in
  `scripts/sync-to-pi.sh` used by both install and deploy)

## Web (`web/`)

- Create React App defaults; Prettier config in `web/.prettierrc.js`
- Run `npx prettier --write` on touched files before committing
