"""Import-all: registers every @tool. Keep imports lazy-friendly (no network at import)."""
from .sources import markets, hazards, intel, synth, practical  # noqa
from . import aoi  # noqa
from .core.registry import REG, describe, names

__all__ = ["REG", "describe", "names"]
