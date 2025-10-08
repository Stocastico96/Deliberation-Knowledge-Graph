#!/usr/bin/env python3
"""
Script to convert US Supreme Court Arguments data to RDF format
compatible with the deliberation ontology.
"""

import os
import sys
import argparse
import subprocess

def convert_csv_to_rdf(csv_file, output_dir):
    """Convert CSV data to RDF format via JSON intermediate format"""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Step 1: Convert CSV to JSON
    json_dir = os.path.join(output_dir, "json")
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
    
    json_output = os.path.join(json_dir, "scotus_debates.json")
    
    # Get the path to the convert_csv_to_json.py script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_to_json_script = os.path.join(script_dir, "convert_csv_to_json.py")
    
    # Run the CSV to JSON conversion
    print(f"Converting CSV to JSON format...")
    try:
        subprocess.run([sys.executable, csv_to_json_script, csv_file, json_output], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error converting CSV to JSON: {e}")
        return False
    
    # Step 2: Convert JSON to RDF
    # Get the path to the convert_json_to_rdf.py script from EU Parliament debates
    parent_dir = os.path.dirname(script_dir)
    json_to_rdf_script = os.path.join(parent_dir, "EU_parliament_debates", "convert_json_to_rdf.py")
    
    # Check if the script exists
    if not os.path.exists(json_to_rdf_script):
        print(f"Error: JSON to RDF conversion script not found at {json_to_rdf_script}")
        return False
    
    # Find all JSON files in the json_dir (there might be multiple if cases were split)
    json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    
    if not json_files:
        print("Error: No JSON files found to convert to RDF")
        return False
    
    # Convert each JSON file to RDF
    for json_file in json_files:
        json_path = os.path.join(json_dir, json_file)
        rdf_file = os.path.splitext(json_file)[0] + ".rdf"
        rdf_path = os.path.join(output_dir, rdf_file)
        
        print(f"Converting {json_file} to RDF format...")
        try:
            subprocess.run([sys.executable, json_to_rdf_script, json_path, rdf_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error converting JSON to RDF: {e}")
            continue
    
    print(f"Conversion complete. RDF files saved to {output_dir}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Convert US Supreme Court Arguments data to RDF format')
    parser.add_argument('input_file', help='Path to the CSV file')
    parser.add_argument('output_dir', help='Directory to save the output RDF files')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist")
        sys.exit(1)
    
    success = convert_csv_to_rdf(args.input_file, args.output_dir)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
