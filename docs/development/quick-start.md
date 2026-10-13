# Quick Start

For production use, see main [README.md](../../README.md#getting-started).

For development:

```bash
# 1. Clone
git clone <your-fork-url>
cd rpi-kvm

# 2. Test environment
vagrant up
./run_tests.sh

# 3. Make changes
# Edit code...

# 4. Test
vagrant ssh -c "cd /vagrant && python3 -m pytest tests/ -v"

# 5. Deploy to RPi (over ssh, no GitHub push needed)
./deploy_to_rpi.sh

# 6. Full install on the RPi if install-level files changed
./scripts/install-from-ssh.sh
```

See [Installation Guide](installation.md) for the details of both install
approaches.
