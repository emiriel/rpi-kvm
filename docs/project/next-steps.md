# Next Steps & Roadmap

Current development priorities and future enhancements for rpi-kvm.

## Current Sprint: ServicesResolved Auto-Reconnect

### Status: In Progress

**Goal**: Fix auto-reconnect reliability by using proper BlueZ signals instead of hardcoded delays.

**Tasks**:
- [x] Stash current changes
- [x] Setup Vagrant test environment
- [x] Create test infrastructure
- [x] Refactor documentation
- [ ] Write unit tests for BtClient
- [ ] Write integration tests
- [ ] Apply ServicesResolved changes
- [ ] Test on real hardware
- [ ] Deploy to production

**Expected Benefits**:
- Faster reconnection (no arbitrary delays)
- More reliable (event-driven vs polling)
- Works across different devices/speeds
- Cleaner codebase

### Technical Details

See [bluetooth-auto-connection.md](../bluetooth/bluetooth-auto-connection.md) for implementation details.

**Key Change**: Replace hardcoded timers with D-Bus signal monitoring:
- Monitor `ServicesResolved` property
- React immediately when host ready
- Remove `call_later()` delays

---

## Short-Term Improvements (Next 1-2 Months)

### 1. Testing Infrastructure ⚡ High Priority

**Current State**: No automated tests

**Goals**:
- [ ] Mock-based unit tests for core logic
- [ ] Vagrant VM with virtual Bluetooth
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Test coverage >70%

**Benefits**:
- Catch regressions early
- Faster development cycle
- Contributor confidence

### 2. Mouse Performance Optimization

**Issue**: Mouse movement can be laggy (see `troubleshooting/04-mouse-performance.md`)

**Root Cause**: Individual HID reports for each micro-movement

**Proposed Solution**:
- Batch mouse movements within time window (5-10ms)
- Send one report with accumulated delta
- Reduce Bluetooth overhead

**Expected Improvement**: 50% reduction in reports, smoother cursor

### 3. Multi-Monitor Support

**Current**: Single cursor shared across hosts

**Proposed**:
- Detect screen edges on active host
- Auto-switch to adjacent host's screen
- Configure monitor layout in web UI

**Use Case**: Seamless cursor flow between multiple computers

### 4. Clipboard Sync

**Current**: Basic clipboard support exists (`clipboard.py`)

**Improvements Needed**:
- Bidirectional sync
- Large clipboard handling
- Format preservation (rich text, images)
- Security considerations

---

## Medium-Term Features (3-6 Months)

### 5. Audio Routing

**Goal**: Route audio between hosts

**Challenges**:
- Bluetooth bandwidth limits
- Latency requirements
- Simultaneous HID + Audio profiles

**Approach**:
- Use separate Bluetooth profiles
- Or: Network-based audio (PulseAudio/PipeWire)

### 6. Video Capture (True KVM)

**Goal**: Capture and display video from hosts

**Hardware**:
- HDMI capture card (USB or CSI)
- Pi 4 or Pi 5 recommended

**Software**:
- v4l2 video capture
- H.264 encoding
- Web-based viewer

**Use Case**: Full remote KVM functionality

### 7. File Transfer

**Goal**: Drag-and-drop files between hosts

**Approaches**:
- OBEX over Bluetooth
- HTTP upload via web UI
- Shared network folder

### 8. Mobile App

**Platforms**: iOS, Android

**Features**:
- Remote control of switching
- Status monitoring
- Quick connect/disconnect
- Configuration

**Technology**: React Native or Flutter

---

## Long-Term Vision (6-12 Months)

### 9. Multi-RPi Setup

**Scenario**: Enterprise use case with many hosts

**Architecture**:
- Multiple RPi units
- Centralized management server
- Synchronized state
- Load balancing

### 10. Extensibility / Plugin System

**Goal**: Community contributions without core changes

**Ideas**:
- Python plugin API
- Custom hotkey actions
- External integrations (Home Assistant, IFTTT)
- Custom displays

### 11. Security Hardening

**Current**: Relies on Bluetooth pairing security

**Enhancements**:
- Encrypted clipboard
- Authentication for web UI
- Audit logging
- Role-based access
- Certificate pinning

### 12. Commercial Support

**Potential**:
- Pre-configured hardware kits
- Professional support subscriptions
- Enterprise features
- Cloud management

---

## Technical Debt

### Code Quality

- [ ] Add type hints throughout codebase
- [ ] Comprehensive docstrings
- [ ] Refactor large functions (split bt_client._run)
- [ ] Centralize error handling
- [ ] Logging levels audit

### Documentation

- [x] Migrate to structured docs/ folder
- [ ] Architecture diagrams (draw.io or mermaid)
- [ ] API documentation (auto-generated)
- [ ] Video tutorials
- [ ] Internationalization (i18n)

### Dependencies

- [ ] Pin dependency versions
- [ ] Audit security vulnerabilities
- [ ] Migrate to maintained alternatives if needed
- [ ] Support Python 3.12+

---

## Community & Contribution

### Contribution Areas

**Good First Issues**:
- Documentation improvements
- Web UI enhancements
- Hardware guides (different Pi models)
- Testing different host OS (Windows, macOS, Linux)

**Advanced Contributions**:
- Core Bluetooth features
- Performance optimization
- New hardware support
- Protocol implementations

See [Contributing Guide](../development/contributing.md) for details.

### Community Building

- [ ] Discord/Matrix server
- [ ] Forum for discussions
- [ ] Showcase user setups
- [ ] Contributor recognition

---

## Research & Experiments

### Ideas to Explore

1. **eBPF for input capture**: Lower latency than evdev?
2. **Bluetooth 5.2 LE Audio**: Better audio quality/latency
3. **USB/IP**: Passthrough entire USB devices, not just HID
4. **Machine learning**: Auto-detect which host user is using
5. **Power management**: Wake hosts from Raspberry Pi

---

## How to Contribute

See specific tasks above and:

1. Check [GitHub Issues](https://github.com/BLeeEZ/rpi-kvm/issues)
2. Propose new features in Discussions
3. Submit PRs for any of the above
4. Improve documentation
5. Share your setup!

---

## Staying Updated

Follow project progress:
- GitHub repository
- Release notes
- Documentation updates
- Community discussions

---

Last updated: 2026-05-22
