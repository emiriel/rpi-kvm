# Quick Start

For production use, see main [README.md](../../README.md#getting-started).

For development:

```bash
# 1. Clone
git clone https://github.com/BLeeEZ/rpi-kvm.git
cd rpi-kvm

# 2. Test environment
vagrant up
./run_tests.sh

# 3. Make changes
# Edit code...

# 4. Test
vagrant ssh -c "cd /vagrant && python3 -m pytest tests/ -v"

# 5. Deploy to RPi
# See deployment docs (coming soon)
```
