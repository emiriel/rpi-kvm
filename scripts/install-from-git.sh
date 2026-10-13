#!/bin/bash
# Git-approach installer: run ON the Pi inside a git checkout, after a
# 'git clone' or 'git pull'. Calls the common installer
# (scripts/install.sh), then restores the git working tree, because the
# installer substitutes __INSTALL_DIR__ placeholders in tracked files.
# Aborts if the tree contains other local modifications, so it can not
# destroy changes deployed by other means (e.g. the ssh-based install).

set -euo pipefail

cd "$(dirname "$0")/.."

if [ -d .git ]; then
    UNEXPECTED=$(git status --porcelain \
        | grep -vE 'systemd/|rpi_kvm/web\.py' || true)
    if [ -n "$UNEXPECTED" ]; then
        echo "Refusing to install: working tree has changes beyond the" >&2
        echo "install-time placeholder substitutions:" >&2
        echo "$UNEXPECTED" >&2
        echo "Commit or stash them, or use the ssh-based install" >&2
        echo "(scripts/install-from-ssh.sh) instead." >&2
        exit 1
    fi
fi

sudo bash ./scripts/install.sh

# Restore the placeholder files so a future 'git pull' stays clean.
# This is git-specific cleanup: it must not run on ssh-deployed trees.
if [ -d .git ]; then
    git reset --hard
fi
