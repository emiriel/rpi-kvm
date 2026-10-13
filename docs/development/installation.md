# Installation Guide

See main [README.md](../../README.md#getting-started) for the standard
installation on the Pi itself (git clone + `sudo ./rpi-kvm.sh install`).

## Install Approaches

Both approaches run the same on-Pi installer (`scripts/install.sh`) and differ
only in how the sources reach the Pi. The ssh transport they share lives in
`scripts/sync-to-pi.sh`.

### 1. Git (on the Pi)

```bash
git clone <your-fork-url>
cd rpi-kvm
sudo ./rpi-kvm.sh install
```

`rpi-kvm.sh install` calls `scripts/install-from-git.sh`, which restores the
git working tree after install (the installer substitutes `__INSTALL_DIR__`
placeholders in tracked files). It aborts if the tree holds other local
modifications, so it can not destroy work deployed by other means.

### 2. SSH (from the dev machine, no GitHub required)

```bash
./scripts/install-from-ssh.sh
```

This syncs the local working tree to the Pi (tar over ssh, then rsync on the
Pi side) and runs the installer remotely. Configuration via environment:

- `RPI_KVM_HOST` (default `rpi-kvm.home`)
- `RPI_KVM_REMOTE_DIR` (default `/root/tools/rpi-kvm`)

## Deploying After Each Change

For development iterations, deploy the working tree and restart the services
without a full install:

```bash
./deploy_to_rpi.sh
```

The sync preserves runtime state (gitignored `conf/*.json` files) and the
Pi-local `deployment/` directory.

## Additional Setup

### Development Environment

```bash
# Clone repository
git clone <your-fork-url>
cd rpi-kvm

# Setup test environment
vagrant up

# Run tests
./run_tests.sh
```

See [Testing Setup](testing-setup.md) for details.
