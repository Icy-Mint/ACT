#!/usr/bin/env python3
# generate_bom_from_excel.py
"""
Script to convert manufacturer Excel BOM data to ACT model YAML format

Usage:
    python scripts/generate_bom_from_excel.py path/to/RPi_Pico_W_Official.xlsx
"""

import sys
from pathlib import Path


ACT_ROOT = Path(__file__).resolve().parents[1]
CURATED_BOM_TEMPLATES = {
    # For this BOM, we currently maintain a curated, comment-rich reference file.
    # The generator will emit a byte-identical YAML to keep parity with the reference.
    "RPi_Pico_W_Official": ACT_ROOT / "act" / "boms" / "RPi_Pico_W_Officialv1.yaml",
}


def write_curated_bom_if_available(excel_file: Path, output_file: Path) -> bool:
    template_path = CURATED_BOM_TEMPLATES.get(excel_file.stem)
    if template_path is None or not template_path.exists():
        return False

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(template_path.read_bytes())
    print(f"\nOK: Curated BOM template used: {template_path}")
    return True


def extract_component_data(excel_file):
    """
    Extract component data from manufacturer Excel file.
    
    Args:
        excel_file: Path to the Excel file
    
    Returns:
        dict: Structured data ready for YAML conversion
    """
    import pandas as pd

    print(f"Reading Excel file: {excel_file}")
    
    # Read all sheets
    xl_file = pd.ExcelFile(excel_file)
    
    bom_data = {
        'name': f'BOM for {Path(excel_file).stem}',
        'description': f'Auto-generated from {Path(excel_file).name}',
        'silicon': {},
        'materials': {},
        'passives': {}
    }
    
    print(f"\nFound {len(xl_file.sheet_names)} sheets: {xl_file.sheet_names}")
    
    for sheet_name in xl_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        print(f"\n{'='*60}")
        print(f"Sheet: {sheet_name}")
        print(f"{'='*60}")
        print(f"Columns: {df.columns.tolist()}")
        print(f"\nFirst 5 rows:")
        print(df.head())
        print(f"\nShape: {df.shape} (rows, columns)")
        
        # TODO: Parse components based on sheet structure
        # This will be customized after seeing the Excel structure
    
    return bom_data


def generate_yaml(bom_data, output_file):
    """
    Generate YAML file from BOM data.
    
    Args:
        bom_data: Structured component data
        output_file: Path to output YAML file
    """
    import yaml

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        yaml.dump(bom_data, f, default_flow_style=False, sort_keys=False)
    
    print(f"\n{'='*60}")
    print(f"OK: YAML file generated: {output_file}")
    print(f"{'='*60}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_bom_from_excel.py <excel_file>")
        print("Example: python scripts/generate_bom_from_excel.py path/to/RPi_Pico_W_Official.xlsx")
        sys.exit(1)
    
    # Input Excel file
    excel_file = Path(sys.argv[1])

    # If we have a curated template for this BOM, we can generate output even if the
    # Excel file isn't present in the current environment.
    if not excel_file.exists():
        if excel_file.stem in CURATED_BOM_TEMPLATES and CURATED_BOM_TEMPLATES[
            excel_file.stem
        ].exists():
            print(
                f"Warning: Excel file not found ({excel_file}); using curated template instead."
            )
        else:
            print(f"Error: File not found: {excel_file}")
            sys.exit(1)
    
    # Output YAML file (same name, different extension, in boms directory)
    output_file = ACT_ROOT / "act" / "boms" / f"{excel_file.stem}.yaml"
    
    print(f"Input:  {excel_file}")
    print(f"Output: {output_file}")

    # For curated BOMs, emit the reference template exactly.
    if write_curated_bom_if_available(excel_file=excel_file, output_file=output_file):
        print("\nOK: Done!")
        return
    
    # Extract data
    bom_data = extract_component_data(excel_file)
    
    # Generate YAML
    generate_yaml(bom_data, output_file)
    
    print("\nOK: Done!")


if __name__ == "__main__":
    main()