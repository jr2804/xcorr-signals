---
title: Contributing
---

## Contributing

Contributions are welcome! Here's how you can help.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/jr2804/xcorr-signals.git
cd xcorr-signals

# Install dependencies
uv sync --dev

# Install mise tasks
mise install
```

### Running Tests

```bash
mise test
```

### Code Quality

```bash
# Lint and format
mise lint
mise format

# Type check
mise type-check
```

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Releasing

Releases are automated by `.github/workflows/release.yml`:

- Every push to `main` creates the next UTC CalVer tag (`YYYY.M.N`).
- The workflow builds one `manylinux_2_34` abi3 wheel for CPython 3.13+
  and an sdist, publishes both to PyPI with Trusted Publishing, then
  creates a GitHub release.
- Include `[skip release]` anywhere in the HEAD commit message to
  suppress a release. The post-release version-stamp commit includes it
  automatically. Because the whole message is scanned, avoid quoting the
  marker in the body of an otherwise normal release commit.

The first upload requires a PyPI pending trusted publisher with these
exact values:

| Field | Value |
|-------|-------|
| PyPI project name | `xcorr-signals` |
| Owner | `jr2804` |
| Repository name | `xcorr-signals` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |
