# Packaging & Install Options

## Option A (recommended): Dev Editable Install

```bash
cd /data/.openclaw/workspace/src/ralph-loop
./scripts/install-dev.sh
```

## Option B: pipx (isolated global install)

Install from local source:

```bash
pipx install /data/.openclaw/workspace/src/ralph-loop
```

Upgrade after local changes:

```bash
pipx reinstall /data/.openclaw/workspace/src/ralph-loop
```

## Option C: Homebrew (post-v1 path)

A Homebrew formula/tap can be added when publishing a tagged release tarball.

Suggested flow:
1. Tag release in git
2. Produce source archive
3. Create tap repo with formula pointing to release URL + sha256
4. `brew install <tap>/ralph-loop`

This path is intentionally deferred until public release cadence is stable.
