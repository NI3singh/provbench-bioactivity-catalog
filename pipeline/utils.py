"""Shared helpers for the ProvBench pipeline."""
from __future__ import annotations

import hashlib
import logging
import math
import sys
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    try:  # Windows consoles default to cp1252; force UTF-8 so arrows/apostrophes log fine
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    return logging.getLogger(name)


def value_to_nm(value, units, unit_map) -> Optional[float]:
    """Convert a (value, units) pair to nanomolar, or None if not convertible."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    factor = unit_map.get((str(units) if units is not None else "").strip())
    if factor is None:
        return None
    return v * factor


def to_p_activity(value_nm: Optional[float]) -> Optional[float]:
    """pActivity = -log10(value in M) = 9 - log10(value_nM)."""
    if value_nm is None or value_nm <= 0:
        return None
    return 9.0 - math.log10(value_nm)


def agreement_label(spread_log: Optional[float], strong: float, moderate: float) -> str:
    if spread_log is None:
        return "single"
    if spread_log < strong:
        return "strong"
    if spread_log < moderate:
        return "moderate"
    return "weak"


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
