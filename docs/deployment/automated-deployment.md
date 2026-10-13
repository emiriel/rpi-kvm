# Automated Deployment via Webhooks

Automated deployment system that triggers on git push to GitHub or Forgejo.

## Deployment Tiers

| Tier | Mechanism | When |
|---|---|---|
| **PROD** | Push to `main` → webhook → `deploy.sh` (git reset to `origin/main` + service restart) | Canonical releases |
| **Debug** | `./deploy_to_rpi.sh` from the dev machine (direct ssh sync, no GitHub) | Development iterations |

The PROD flow assumes the Pi tree is a **git checkout of `origin/main`**
with working fetch credentials (see
[Installation Guide](../development/installation.md)). Debug deploys
intentionally diverge the Pi tree from `main`; the next PROD deploy resets
it back to the pushed state.

## Architecture

```
GitHub/Forgejo Push → Webhook → RPi Receiver → Deploy Script → Service Restart
```

`deploy.sh` resets the tree to `origin/main`, re-applies the
`__INSTALL_DIR__` substitution in `rpi_kvm/web.py` (install-time
placeholder restored by the reset), then restarts the core, web, infohub
and touchphat services.

## Installation

### 1. Install Flask on RPi

```bash
pip3 install flask
```

### 2. Generate Webhook Secret

```bash
# Generate a strong secret
openssl rand -hex 32
```

Save this secret - you'll need it for both the service and GitHub/Forgejo configuration.

### 3. Configure Service

Edit `/root/tools/rpi-kvm/deployment/rpi-kvm-webhook.service`:

```ini
Environment="WEBHOOK_SECRET=your_generated_secret_here"
```

### 4. Install and Start Service

```bash
# Make scripts executable
chmod +x /root/tools/rpi-kvm/deployment/deploy.sh
chmod +x /root/tools/rpi-kvm/deployment/webhook_receiver.py

# Copy service file
cp /root/tools/rpi-kvm/deployment/rpi-kvm-webhook.service /etc/systemd/system/

# Enable and start
systemctl daemon-reload
systemctl enable rpi-kvm-webhook
systemctl start rpi-kvm-webhook

# Check status
systemctl status rpi-kvm-webhook
journalctl -u rpi-kvm-webhook -f
```

### 5. Configure Firewall (if needed)

```bash
# Allow webhook port
ufw allow 9000/tcp
```

## GitHub Configuration

### 1. Add Webhook

Go to: `Repository Settings → Webhooks → Add webhook`

**Payload URL:** `http://YOUR_RPI_IP:9000/webhook`

**Content type:** `application/json`

**Secret:** Your generated secret from step 2

**Which events:** Just the push event

**Active:** ✓ Checked

### 2. Test

Push a commit to main branch. Check webhook delivery in GitHub UI and RPi logs:

```bash
journalctl -u rpi-kvm-webhook -f
```

## Forgejo Configuration

### 1. Add Webhook

Go to: `Repository Settings → Webhooks → Add Webhook`

**Target URL:** `http://YOUR_RPI_IP:9000/webhook`

**HTTP Method:** POST

**POST Content Type:** `application/json`

**Secret:** Your generated secret from step 2

**Trigger On:** Push events

**Branch filter:** `main`

**Active:** ✓ Checked

### 2. Test

Push a commit to main branch. Check webhook delivery in Forgejo UI and RPi logs.

## Migrating from GitHub to Forgejo

When you migrate to self-hosted Forgejo:

### Option 1: Update Remote Origin (Recommended)

1. **On RPi**, update git remote:

```bash
cd /root/tools/rpi-kvm
git remote set-url origin https://your-forgejo.com/youruser/rpi-kvm.git
git remote -v  # Verify
```

2. **Configure Forgejo webhook** (see above)

3. **Disable GitHub webhook** (Settings → Webhooks → Edit → Uncheck Active)

### Option 2: Automated Migration Script

Create commit before migration that updates remote:

```bash
#!/bin/bash
# Migration script to update origin to Forgejo

NEW_ORIGIN="https://your-forgejo.com/youruser/rpi-kvm.git"

cd /root/tools/rpi-kvm
git remote set-url origin "$NEW_ORIGIN"
echo "Updated origin to: $NEW_ORIGIN"
git remote -v
```

Add to deployment script or run manually during migration.

## Security Notes

- **Secret required**: Without `WEBHOOK_SECRET`, signatures aren't verified
- **Network**: RPi must be reachable from GitHub/Forgejo (port 9000)
- **Firewall**: Only allow webhook port from trusted IPs if possible
- **HTTPS**: Consider nginx reverse proxy with Let's Encrypt for production

## Troubleshooting

### Webhook Not Triggering

1. Check service status:
```bash
systemctl status rpi-kvm-webhook
```

2. Check logs:
```bash
journalctl -u rpi-kvm-webhook -f
```

3. Test webhook endpoint:
```bash
curl http://localhost:9000/health
```

4. Check GitHub/Forgejo webhook delivery logs (shows HTTP response)

### Deployment Failing

1. Check deployment logs:
```bash
journalctl -u rpi-kvm-webhook -f
```

2. Test deploy script manually:
```bash
/root/tools/rpi-kvm/deployment/deploy.sh
```

3. Check service can restart:
```bash
systemctl restart rpi-kvm-core
```

### Permission Issues

Webhook service runs as root to restart systemd services. If changing user, grant sudo permissions:

```bash
visudo
# Add: webhookuser ALL=(ALL) NOPASSWD: /bin/systemctl restart rpi-kvm-core
```

## Advanced Configuration

### Custom Port

Edit `webhook_receiver.py` line:
```python
app.run(host='0.0.0.0', port=9000)
```

Or set environment variable in service file:
```ini
Environment="PORT=8080"
```

### Multiple Branches

Edit service file:
```ini
Environment="DEPLOY_BRANCH=develop"
```

### Custom Deployment Logic

Edit `/root/tools/rpi-kvm/deployment/deploy.sh` to add:
- Database migrations
- Dependency updates
- Health checks
- Rollback on failure

## Monitoring

View deployment history:
```bash
journalctl -u rpi-kvm-webhook --since "1 day ago"
```

Monitor service uptime:
```bash
systemctl status rpi-kvm-webhook
```
