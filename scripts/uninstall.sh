#!/bin/bash

echo "### RPI-KVM Uninstall ############"
if [ -f "./conf/bluetooth.service.bak" ] ; then
    echo "Restore bluetooth service config backup"
    sudo cp ./conf/bluetooth.service.bak /lib/systemd/system/bluetooth.service
    sudo systemctl daemon-reload
    echo "Restart bluetooth with the original config"
    sudo systemctl restart bluetooth
fi
if [ -f "/etc/systemd/system/rpi-kvm.target" ] ; then
    echo "Stop RPI-KVM target"
    sudo systemctl stop rpi-kvm.target
    echo "Disable RPI-KVM target"
    sudo systemctl disable rpi-kvm.target
    echo "Remove RPI-KVM services"
    sudo rm /etc/systemd/system/rpi-kvm-*.service
    sudo rm /etc/systemd/system/rpi-kvm.target
    sudo systemctl daemon-reload
fi
if [ -f "/etc/dbus-1/system.d/org.rpi.kvmservice.conf" ] ; then
    echo "Remove RPI-KVM D-Bus config"
    sudo rm /etc/dbus-1/system.d/org.rpi.kvmservice.conf
fi
echo "### RPI-KVM Uninstall Done #######"
