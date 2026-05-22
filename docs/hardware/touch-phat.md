# Touch pHAT Integration

rpi-kvm supports the Pimoroni Touch pHAT for physical host switching.

## Hardware

- [Pimoroni Touch pHAT](https://shop.pimoroni.com/products/touch-phat)
- Capacitive touch buttons
- I2C interface

## Setup

1. Attach Touch pHAT to GPIO header
2. Enable I2C:
   ```bash
   sudo raspi-config
   # Interface Options → I2C → Enable
   ```
3. Install Python library:
   ```bash
   pip3 install touchphat
   ```
4. rpi-kvm auto-detects Touch pHAT on startup

## Button Mapping

- Button 1: Switch to Host 1
- Button 2: Switch to Host 2
- Button 3: Switch to Host 3
- Button 4: Switch to Host 4
- Button Back: Previous host
- Button Enter: Confirm/toggle auto-switch

## Code

See `rpi_kvm/touch_phat.py` for implementation.

## Troubleshooting

**Touch pHAT not detected**:
```bash
# Check I2C devices
i2cdetect -y 1
# Should show device at 0x2B
```

**Permission errors**:
```bash
sudo usermod -a -G i2c pi
```
