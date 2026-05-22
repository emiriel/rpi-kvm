# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # Use Ubuntu 22.04 LTS
  config.vm.box = "ubuntu/jammy64"

  # VM naming
  config.vm.hostname = "rpi-kvm-test"

  # Port forwarding for test result server
  config.vm.network "forwarded_port", guest: 8080, host: 8080, host_ip: "127.0.0.1"

  # Sync project folder
  config.vm.synced_folder ".", "/vagrant"

  # VM resources
  config.vm.provider "virtualbox" do |vb|
    vb.name = "rpi-kvm-test"
    vb.memory = "2048"
    vb.cpus = 2
  end

  # Provisioning script
  config.vm.provision "shell", inline: <<-SHELL
    set -e

    echo "=== Installing system packages ==="
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
      bluez \
      bluez-tools \
      python3 \
      python3-pip \
      python3-venv \
      dbus \
      kmod \
      net-tools

    echo "=== Loading vhci kernel module for virtual Bluetooth ==="
    modprobe hci_vhci || echo "Warning: hci_vhci module not available"

    echo "=== Setting up Python environment ==="
    cd /vagrant

    # Install Python dependencies
    pip3 install --break-system-packages \
      dbus-next \
      pytest \
      pytest-asyncio \
      pytest-cov \
      flask

    echo "=== Starting D-Bus system bus ==="
    service dbus start || systemctl start dbus

    echo "=== Starting BlueZ ==="
    service bluetooth start || systemctl start bluetooth

    # Wait for services to be ready
    sleep 2

    echo "=== Checking service status ==="
    systemctl is-active dbus && echo "D-Bus: OK" || echo "D-Bus: FAILED"
    systemctl is-active bluetooth && echo "BlueZ: OK" || echo "BlueZ: FAILED"

    echo ""
    echo "=== VM provisioning complete ==="
    echo "Run 'vagrant ssh' to access the VM"
    echo "Run unit tests: cd /vagrant && python3 -m pytest tests/test_bt_client.py -v"
    echo "Run integration tests: cd /vagrant && python3 -m pytest tests/test_bt_integration.py -v -m integration"
  SHELL
end
