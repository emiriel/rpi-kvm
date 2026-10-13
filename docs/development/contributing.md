# Contributing Guidelines

## Getting Started

1. Fork and clone the repository
2. Set up the test environment: `vagrant up` then `./run_tests.sh`
   (see [testing-setup.md](testing-setup.md))
3. Read [AGENTS.md](../../AGENTS.md) for the repository conventions and the
   [System Overview](../architecture/system-overview.md) for the architecture

## Workflow

1. Create a feature branch
2. Make your change; keep diffs minimal and behavior-preserving where the
   task is a fix
3. Add or update unit tests (mocked D-Bus, no real hardware — see
   [code-style.md](code-style.md))
4. Run the suite: `python3 -m pytest tests/ -v` (Vagrant VM is the
   reference environment)
5. Commit with a Conventional Commits message (`feat:`, `fix:`, `docs:`...)
6. If a commit was produced with an LLM agent, append `(vibe-coded)` to the
   subject line — intellectual honesty is the project's policy
7. Open a PR describing the why, not the what

## Testing Requirements

- New `BtClient`/`BtServer` behavior ships with unit tests
- D-Bus/BlueZ dependent tests are marked `integration` and must not run in
  the default unit-test pass
- Changes deployed on a real Pi should be smoke-tested there
  (`./deploy_to_rpi.sh` from the dev machine)

## Commit Attribution

Commits written by an LLM agent carry `(vibe-coded)` in the subject.
Fully hand-written commits carry no marker. Don't mix attribution within a
commit — split the work instead.
