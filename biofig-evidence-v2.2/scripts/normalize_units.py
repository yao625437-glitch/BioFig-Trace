#!/usr/bin/env python3
"""Normalize common scientific units without changing the numeric value."""

from __future__ import annotations

import json
import sys


EXACT_UNITS = {
    "M": ("M", "molar_concentration", 1.0),
    "mM": ("mM", "molar_concentration", 1e-3),
    "µM": ("µM", "molar_concentration", 1e-6),
    "μM": ("µM", "molar_concentration", 1e-6),
    "uM": ("µM", "molar_concentration", 1e-6),
    "nM": ("nM", "molar_concentration", 1e-9),
    "pM": ("pM", "molar_concentration", 1e-12),
    "pA": ("pA", "current", 1e-12),
}


UNITS = {
    "pa": ("Pa", "pressure", 1.0), "kpa": ("kPa", "pressure", 1e3), "mpa": ("MPa", "pressure", 1e6),
    "n": ("N", "force", 1.0), "mn": ("mN", "force", 1e-3), "μn": ("µN", "force", 1e-6), "µn": ("µN", "force", 1e-6),
    "m": ("m", "length", 1.0), "cm": ("cm", "length", 1e-2), "mm": ("mm", "length", 1e-3), "μm": ("µm", "length", 1e-6), "µm": ("µm", "length", 1e-6),
    "m3": ("m³", "volume", 1.0), "m³": ("m³", "volume", 1.0), "mm3": ("mm³", "volume", 1e-9), "mm³": ("mm³", "volume", 1e-9), "μm3": ("µm³", "volume", 1e-18), "µm³": ("µm³", "volume", 1e-18),
    "s": ("s", "time", 1.0), "ms": ("ms", "time", 1e-3), "min": ("min", "time", 60.0), "h": ("h", "time", 3600.0),
    "d": ("d", "time", 86400.0), "day": ("d", "time", 86400.0), "days": ("d", "time", 86400.0),
    "g": ("g", "mass", 1e-3), "mg": ("mg", "mass", 1e-6), "μg": ("µg", "mass", 1e-9), "µg": ("µg", "mass", 1e-9), "ng": ("ng", "mass", 1e-12),
    "mol": ("mol", "amount", 1.0), "mmol": ("mmol", "amount", 1e-3), "μmol": ("µmol", "amount", 1e-6), "µmol": ("µmol", "amount", 1e-6), "nmol": ("nmol", "amount", 1e-9),
    "mg/ml": ("mg/mL", "mass_concentration", 1.0), "μg/ml": ("µg/mL", "mass_concentration", 1e-3), "µg/ml": ("µg/mL", "mass_concentration", 1e-3), "ng/ml": ("ng/mL", "mass_concentration", 1e-6),
    "°c": ("°C", "temperature", None), "℃": ("°C", "temperature", None), "k": ("K", "temperature", 1.0),
    "hz": ("Hz", "frequency", 1.0), "khz": ("kHz", "frequency", 1e3),
    "v": ("V", "voltage", 1.0), "mv": ("mV", "voltage", 1e-3), "μv": ("µV", "voltage", 1e-6), "µv": ("µV", "voltage", 1e-6),
    "a": ("A", "current", 1.0), "ma": ("mA", "current", 1e-3), "μa": ("µA", "current", 1e-6), "µa": ("µA", "current", 1e-6), "na": ("nA", "current", 1e-9),
    "%": ("%", "fraction", 0.01), "percent": ("%", "fraction", 0.01), "wt%": ("wt%", "mass_fraction", 0.01), "wt.%": ("wt%", "mass_fraction", 0.01),
    "ratio": ("ratio", "dimensionless", 1.0), "fold": ("fold", "dimensionless", 1.0), "×": ("fold", "dimensionless", 1.0),
}


def normalize(unit: str) -> dict[str, object]:
    exact = unit.strip()
    if exact in EXACT_UNITS:
        normalized, dimension, scale = EXACT_UNITS[exact]
        return {"status": "recognized", "input": unit, "normalized_unit": normalized, "dimension": dimension, "scale_to_si": scale}
    key = exact.replace("^3", "3").lower()
    if key not in UNITS:
        return {"status": "unknown_unit", "input": unit, "normalized_unit": None, "dimension": None, "scale_to_si": None}
    normalized, dimension, scale = UNITS[key]
    return {"status": "recognized", "input": unit, "normalized_unit": normalized, "dimension": dimension, "scale_to_si": scale}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: normalize_units.py <unit>", file=sys.stderr)
        return 2
    result = normalize(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "recognized" else 1


if __name__ == "__main__":
    raise SystemExit(main())
