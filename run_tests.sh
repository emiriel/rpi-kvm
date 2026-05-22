#!/bin/bash
# Test runner script for rpi-kvm project

set -e

echo "=== rpi-kvm Test Runner ==="
echo ""

# Check if Vagrant is installed
if ! command -v vagrant &> /dev/null; then
    echo "Error: Vagrant not installed"
    echo "Install: https://www.vagrantup.com/downloads"
    exit 1
fi

# Check VM status
VM_STATUS=$(vagrant status --machine-readable | grep "state," | cut -d',' -f4)

if [ "$VM_STATUS" != "running" ]; then
    echo "Starting test VM..."
    vagrant up
else
    echo "Test VM already running"
fi

echo ""
echo "=== Running tests in VM ==="
vagrant ssh -c "cd /vagrant && python3 -m pytest tests/ -v --color=yes"

echo ""
echo "=== Test run complete ==="
