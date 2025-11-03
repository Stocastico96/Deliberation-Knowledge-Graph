#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

# Find all HTML files in debates_2024_2025 directory
html_files = sorted(Path('debates_2024_2025').glob('verbatim_*.html'))

print(f"Found {len(html_files)} HTML files to convert")

success_count = 0
for html_file in html_files:
    json_file = html_file.with_suffix('.json')
    print(f"Converting {html_file.name}...")

    try:
        result = subprocess.run(
            ['python3', 'convert_verbatim_to_json.py', str(html_file), str(json_file)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"  ✓ Success: {json_file.name}")
            success_count += 1
        else:
            print(f"  ✗ Error: {result.stderr}")
    except Exception as e:
        print(f"  ✗ Exception: {e}")

print(f"\nConverted {success_count}/{len(html_files)} files")
