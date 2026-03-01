#!/usr/bin/env python3
"""
validate_bom.py

Small helper to validate ACT BOM YAML files and (optionally) compare them.

Usage:
  python scripts/validate_bom.py act/boms/RPi_Pico_W_Official.yaml
  python scripts/validate_bom.py act/boms/RPi_Pico_W_Official.yaml --compare act/boms/RPi_Pico_W_Officialv1.yaml
  python scripts/validate_bom.py act/boms/RPi_Pico_W_Official.yaml --compare act/boms/RPi_Pico_W_Officialv1.yaml --exact-text
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL_KEYS = {"name", "description"}
OPTIONAL_TOP_LEVEL_KEYS = {"silicon", "materials", "passives", "imports", "owner"}


def _load_yaml(path: Path) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "PyYAML is required to parse/validate BOMs. Install it with `pip install PyYAML` "
            "or run with `--exact-text` (compare-only)."
        ) from e

    with path.open("r", encoding="utf-8") as handle:
        return yaml.load(handle, Loader=yaml.FullLoader)


def _is_mapping(x: Any) -> bool:
    return isinstance(x, dict)


def validate_bom_dict(bom: Any, *, filename: str = "<bom>") -> list[str]:
    errors: list[str] = []

    if not _is_mapping(bom):
        return [f"{filename}: top-level YAML must be a mapping/dict"]

    missing = REQUIRED_TOP_LEVEL_KEYS - set(bom.keys())
    if missing:
        errors.append(f"{filename}: missing required top-level keys: {sorted(missing)}")

    unknown = set(bom.keys()) - (REQUIRED_TOP_LEVEL_KEYS | OPTIONAL_TOP_LEVEL_KEYS)
    if unknown:
        errors.append(f"{filename}: unknown top-level keys: {sorted(unknown)}")

    for section in ("silicon", "materials", "passives", "imports"):
        if section in bom and bom[section] is not None and not _is_mapping(bom[section]):
            errors.append(f"{filename}: `{section}` must be a mapping/dict if present")

    for section in ("materials", "passives"):
        sec = bom.get(section) or {}
        if not _is_mapping(sec):
            continue
        for comp_name, comp in sec.items():
            if not _is_mapping(comp):
                errors.append(f"{filename}: `{section}.{comp_name}` must be a mapping/dict")
                continue
            if "category" not in comp:
                errors.append(f"{filename}: `{section}.{comp_name}` missing `category`")
            if "quantity" in comp and comp["quantity"] is not None and not isinstance(
                comp["quantity"], int
            ):
                errors.append(
                    f"{filename}: `{section}.{comp_name}.quantity` must be an int if present"
                )

    silicon = bom.get("silicon") or {}
    if _is_mapping(silicon):
        for chip_name, chip in silicon.items():
            if not _is_mapping(chip):
                errors.append(f"{filename}: `silicon.{chip_name}` must be a mapping/dict")
                continue
            if "n_ics" in chip and chip["n_ics"] is not None and not isinstance(
                chip["n_ics"], int
            ):
                errors.append(f"{filename}: `silicon.{chip_name}.n_ics` must be an int")

    return errors


def _deep_sort(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _deep_sort(x[k]) for k in sorted(x.keys())}
    if isinstance(x, list):
        return [_deep_sort(v) for v in x]
    return x


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an ACT BOM YAML file.")
    parser.add_argument("bom", type=Path, help="Path to BOM YAML file.")
    parser.add_argument(
        "--compare",
        type=Path,
        default=None,
        help="Optional: compare BOM content against another BOM YAML file.",
    )
    parser.add_argument(
        "--exact-text",
        action="store_true",
        help="If set with --compare, compare file bytes (not parsed YAML).",
    )
    args = parser.parse_args()

    if not args.bom.exists():
        print(f"Error: BOM file not found: {args.bom}", file=sys.stderr)
        return 2

    bom_data = None
    if not (args.exact_text and args.compare is not None):
        try:
            bom_data = _load_yaml(args.bom)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

        errors = validate_bom_dict(bom_data, filename=str(args.bom))
        if errors:
            print("Validation failed:", file=sys.stderr)
            for e in errors:
                print(f"- {e}", file=sys.stderr)
            return 1

    print(f"OK: Valid BOM: {args.bom}")

    if args.compare is not None:
        if not args.compare.exists():
            print(f"Error: compare file not found: {args.compare}", file=sys.stderr)
            return 2

        if args.exact_text:
            same = args.bom.read_bytes() == args.compare.read_bytes()
        else:
            try:
                other_data = _load_yaml(args.compare)
            except RuntimeError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 2
            other_errors = validate_bom_dict(other_data, filename=str(args.compare))
            if other_errors:
                print("Compare target failed validation:", file=sys.stderr)
                for e in other_errors:
                    print(f"- {e}", file=sys.stderr)
                return 1

            same = _deep_sort(bom_data) == _deep_sort(other_data)

        if not same:
            print(f"ERROR: BOMs differ: {args.bom} vs {args.compare}", file=sys.stderr)
            return 1

        print(f"OK: BOMs match: {args.bom} == {args.compare}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
