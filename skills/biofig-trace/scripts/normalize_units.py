"""Conservative unit spelling normalization; never infers a missing unit."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any


UNIT_MAP: dict[str, tuple[str, str, str | None, float | None]] = {
    "um": ("µm", "length", "m", 1e-6),
    "μm": ("µm", "length", "m", 1e-6),
    "µm": ("µm", "length", "m", 1e-6),
    "nm": ("nm", "length", "m", 1e-9),
    "mm": ("mm", "length", "m", 1e-3),
    "uM": ("µM", "amount_concentration", "mol/m³", 1e-3),
    "μM": ("µM", "amount_concentration", "mol/m³", 1e-3),
    "µM": ("µM", "amount_concentration", "mol/m³", 1e-3),
    "umol/L": ("µM", "amount_concentration", "mol/m³", 1e-3),
    "μmol/L": ("µM", "amount_concentration", "mol/m³", 1e-3),
    "µmol/L": ("µM", "amount_concentration", "mol/m³", 1e-3),
    "nM": ("nM", "amount_concentration", "mol/m³", 1e-6),
    "nmol/L": ("nM", "amount_concentration", "mol/m³", 1e-6),
    "mM": ("mM", "amount_concentration", "mol/m³", 1.0),
    "mmol/L": ("mM", "amount_concentration", "mol/m³", 1.0),
    "M": ("M", "amount_concentration", "mol/m³", 1000.0),
    "mol/L": ("M", "amount_concentration", "mol/m³", 1000.0),
    "mg/mL": ("mg/mL", "mass_concentration", "kg/m³", 1.0),
    "mg/ml": ("mg/mL", "mass_concentration", "kg/m³", 1.0),
    "ug/mL": ("µg/mL", "mass_concentration", "kg/m³", 1e-3),
    "ug/ml": ("µg/mL", "mass_concentration", "kg/m³", 1e-3),
    "μg/mL": ("µg/mL", "mass_concentration", "kg/m³", 1e-3),
    "μg/ml": ("µg/mL", "mass_concentration", "kg/m³", 1e-3),
    "µg/mL": ("µg/mL", "mass_concentration", "kg/m³", 1e-3),
    "µg/ml": ("µg/mL", "mass_concentration", "kg/m³", 1e-3),
    "%": ("%", "fraction", "1", 0.01),
    "percent": ("%", "fraction", "1", 0.01),
    "h": ("h", "time", "s", 3600.0),
    "hr": ("h", "time", "s", 3600.0),
    "hours": ("h", "time", "s", 3600.0),
    "min": ("min", "time", "s", 60.0),
    "s": ("s", "time", "s", 1.0),
    "kDa": ("kDa", "molecular_mass", None, None),
}


def normalize(unit: str | None) -> dict[str, Any]:
    if unit is None or not str(unit).strip():
        return {
            "input": unit,
            "canonical": None,
            "dimension": "unknown",
            "si_unit": None,
            "scale_to_si": None,
            "recognized": False,
            "caution": "未提供单位；不得根据领域常识补全。",
        }
    original = str(unit).strip()
    key = re.sub(r"\s+", "", original)
    record = UNIT_MAP.get(key)
    if record is None:
        return {
            "input": original,
            "canonical": original,
            "dimension": "unknown",
            "si_unit": None,
            "scale_to_si": None,
            "recognized": False,
            "caution": "保留原始拼写；转换前需人工确认量纲与上下文。",
        }
    canonical, dimension, si_unit, scale = record
    return {
        "input": original,
        "canonical": canonical,
        "dimension": dimension,
        "si_unit": si_unit,
        "scale_to_si": scale,
        "recognized": True,
        "caution": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("unit", nargs="?", default=None)
    args = parser.parse_args()
    print(json.dumps(normalize(args.unit), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
