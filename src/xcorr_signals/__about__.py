# SPDX-License-Identifier: MIT
# Copyright 2026, Jan.Reimes
import importlib.metadata

__version__ = "0.0.0"
try:
    __version__ = importlib.metadata.version("xcorr-signals")
except importlib.metadata.PackageNotFoundError:  # pragma: no cover
    pass
