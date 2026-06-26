"""Deterministic anti-fabrication guards for LLM-extracted assay metadata.

The LLM is NEVER trusted directly. Every field it returns must survive:
  1. source-span check  — the cited span must be an exact substring of the input
  2. unit validation     — units must be in a controlled vocabulary
  3. range check         — numeric values must be physically plausible
  4. no-evidence reject  — a field with no valid span is dropped

This mirrors ChEMBL's DATA_VALIDITY vocabulary and the project's whole thesis:
keep what's verifiable, flag what's suspect, reject what's fabricated.
"""
from __future__ import annotations

import re

UNIT_VOCAB = {
    "nm", "nmol/l", "um", "µm", "μm", "umol/l", "mm", "mmol/l", "m", "mol/l",
    "pm", "fm", "%", "ug/ml", "µg/ml", "mg/ml", "ng/ml",
}

# plausible numeric ranges per (lowercased) standard_type, in nM unless noted
PLAUSIBLE_NM = (1e-4, 1e9)


def _to_float(v):
    if v is None:
        return None
    try:
        return float(str(v).strip().lstrip("<>=~ ").split()[0])
    except (ValueError, IndexError):
        return None


def _unit_to_nm(value, unit):
    if value is None or unit is None:
        return None
    f = {"nm": 1, "nmol/l": 1, "um": 1e3, "µm": 1e3, "μm": 1e3, "umol/l": 1e3,
         "mm": 1e6, "mmol/l": 1e6, "m": 1e9, "mol/l": 1e9, "pm": 1e-3, "fm": 1e-6}
    return value * f[unit.lower()] if unit.lower() in f else None


def validate_fields(text: str, fields: list) -> dict:
    norm_text = re.sub(r"\s+", " ", text).strip().lower()
    extracted, rejected, flagged = [], [], []

    for f in fields or []:
        name = (f.get("field_name") or f.get("name") or "").strip()
        value = f.get("value")
        unit = (f.get("unit") or "").strip() or None
        span = (f.get("source_span") or "").strip()

        # 1) source-span check (anti-hallucination)
        if not span or re.sub(r"\s+", " ", span).lower() not in norm_text:
            rejected.append({"field": name, "value": value, "unit": unit,
                             "source_span": span,
                             "reason": "no exact source span found in text (possible hallucination)"})
            continue

        item = {"field": name, "value": value, "unit": unit, "source_span": span, "flag": None}

        # 2) unit validation
        if unit is not None and unit.lower() not in UNIT_VOCAB:
            item["flag"] = "Non standard unit for type"

        # 3) range check (only when we can interpret a concentration)
        num = _to_float(value)
        nm = _unit_to_nm(num, unit) if num is not None else None
        if nm is not None and not (PLAUSIBLE_NM[0] <= nm <= PLAUSIBLE_NM[1]):
            item["flag"] = "Outside typical range"

        (flagged if item["flag"] else extracted).append(item)

    return {
        "extracted": extracted,
        "flagged": flagged,
        "rejected": rejected,
        "n_returned": len(fields or []),
        "n_kept": len(extracted),
        "n_flagged": len(flagged),
        "n_rejected": len(rejected),
    }
