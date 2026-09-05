# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes
import contextlib
import importlib.metadata

# Literal fallback for source checkouts without dist-info (editable / git
# installs). Stamped by the release workflow together with Cargo.toml.
__version__ = "2026.9.18"
with contextlib.suppress(importlib.metadata.PackageNotFoundError):
    __version__ = importlib.metadata.version("xcorr-signals")
