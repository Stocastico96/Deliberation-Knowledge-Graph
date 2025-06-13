#!/usr/bin/env python3
"""
Script to create a unified knowledge graph from all available datasets.
This script:
1. Runs all the conversion scripts to convert datasets to RDF format
2. Combines all RDF data into a single knowledge graph
3. Saves the unified knowledge graph in various formats (RDF/XML, Turtle, JSON-LD)
"""

import os
import sys
import subprocess
import glob
import argparse
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS

def run_conversion_script(script_path, *args):
    """Run a conversion script with the given arguments"""
    print(f"Running {script_path} {' '.join(args)}")
    try:
        subprocess.run([sys.executable, script_path] + list(args), check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}")
        return False

def convert_all_datasets(output_dir):
    """Convert all datasets to RDF format"""
    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    
    # Dictionary of datasets and their conversion scripts
    datasets = {
        "EU_parliament_debates": {
            "script": "data/EU_parliament_debates/convert_json_to_rdf.py",
            "input": "data/EU_parliament_debates/ep_debates/debate_2025-03-10.json",
            "output": f"{output_dir}/eu_parliament_debates.rdf"
        },
        "US_supreme_court_arguments": {
            "script": "data/US_supreme_court_arguments/convert_to_rdf.py",
            "input": "data/US_supreme_court_arguments/dataset.csv",
            "output": f"{output_dir}/us_supreme_court"
        },
        "decide_madrid": {
            "script": "data/decide_Madrid/convert_to_rdf.py",
            "input": "--debates data/decide_Madrid/data/debates.csv --comments data/decide_Madrid/data/comments.csv",
            "output": f"{output_dir}/decide_madrid"
        },
        "delidata": {
            "script": "data/delidata/convert_to_rdf.py",
            "input": "data/delidata/data/combined",
            "output": f"{output_dir}/delidata",
            "max_files": "--max-files 10"  # Limit to 10 files for performance
        },
        "habermas_machine": {
            "script": "data/habermas_machine/convert_to_rdf.py",
            "input": "data/habermas_machine/data",
            "output": f"{output_dir}/habermas_machine",
            "max_sessions": "--max-sessions 5"  # Limit to 5 sessions for performance
        },
        "eu_have_your_say": {
            "script": "data/EU_have_your_say/convert_to_rdf.py",
            "input": "data/EU_have_your_say/sample/sample.csv",  # Using sample as fallback
            "output": f"{output_dir}/eu_have_your_say"
        },
        "decidim_barcelona": {
            "script": "data/decidim_barcelona/convert_to_rdf.py",
            "input": "data/decidim_barcelona/data",
            "output": f"{output_dir}/decidim_barcelona"
        }
    }
    
    # Run each conversion script
    success_count = 0
    for dataset_name, dataset_info in datasets.items():
        print(f"\n=== Converting {dataset_name} ===")
        
        # Check if script exists
        if not os.path.exists(dataset_info["script"]):
            print(f"Script {dataset_info['script']} not found, skipping {dataset_name}")
            continue
        
        # Check if input exists (for simple paths)
        input_path = dataset_info["input"].split()[0] if " " in dataset_info["input"] else dataset_info["input"]
        if not os.path.exists(input_path):
            print(f"Input {input_path} not found, skipping {dataset_name}")
            continue
        
        # Prepare arguments
        args = []
        if " " in dataset_info["input"]:  # Handle complex arguments
            args.extend(dataset_info["input"].split())
        else:
            args.append(dataset_info["input"])
        
        args.append(dataset_info["output"])
        
        # Add optional arguments if present
        if "max_files" in dataset_info:
            args.append(dataset_info["max_files"])
        if "max_sessions" in dataset_info:
            args.append(dataset_info["max_sessions"])
        
        # Run the conversion script
        if run_conversion_script(dataset_info["script"], *args):
            success_count += 1
    
    print(f"\nSuccessfully converted {success_count} out of {len(datasets)} datasets")
    return success_count > 0

def combine_rdf_files(input_dir, output_file):
    """Combine all RDF files in the input directory into a single RDF file"""
    print(f"\n=== Combining RDF files from {input_dir} ===")
    
    # Create a new RDF graph
    g = Graph()
    
    # Define namespaces
    DEL = Namespace("https://w3id.org/deliberation/ontology#")
    g.bind("del", DEL)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    
    # Find all RDF files
    rdf_files = []
    for ext in ["*.rdf", "*.xml", "*.ttl", "*.n3", "*.jsonld"]:
        rdf_files.extend(glob.glob(os.path.join(input_dir, "**", ext), recursive=True))
    
    if not rdf_files:
        print(f"No RDF files found in {input_dir}")
        return False
    
    # Parse each RDF file
    for rdf_file in rdf_files:
        print(f"Parsing {rdf_file}")
        try:
            g.parse(rdf_file)
        except Exception as e:
            print(f"Error parsing {rdf_file}: {e}")
    
    # Save the combined graph in different formats
    base_name = os.path.splitext(output_file)[0]
    
    # RDF/XML
    xml_file = f"{base_name}.rdf"
    print(f"Saving combined graph to {xml_file}")
    g.serialize(destination=xml_file, format="xml")
    
    # Turtle
    ttl_file = f"{base_name}.ttl"
    print(f"Saving combined graph to {ttl_file}")
    g.serialize(destination=ttl_file, format="turtle")
    
    # JSON-LD
    jsonld_file = f"{base_name}.jsonld"
    print(f"Saving combined graph to {jsonld_file}")
    g.serialize(destination=jsonld_file, format="json-ld")
    
    print(f"Combined graph contains {len(g)} triples")
    return True

def main():
    parser = argparse.ArgumentParser(description='Create a unified knowledge graph from all available datasets')
    parser.add_argument('--output-dir', default='knowledge_graph', help='Directory to save the output files')
    parser.add_argument('--skip-conversion', action='store_true', help='Skip dataset conversion and use existing RDF files')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Convert datasets to RDF
    if not args.skip_conversion:
        rdf_dir = os.path.join(args.output_dir, "rdf")
        if not convert_all_datasets(rdf_dir):
            print("Error converting datasets to RDF")
            sys.exit(1)
    else:
        rdf_dir = os.path.join(args.output_dir, "rdf")
        if not os.path.exists(rdf_dir):
            print(f"RDF directory {rdf_dir} not found. Run without --skip-conversion first.")
            sys.exit(1)
    
    # Combine RDF files
    output_file = os.path.join(args.output_dir, "deliberation_kg")
    if not combine_rdf_files(rdf_dir, output_file):
        print("Error combining RDF files")
        sys.exit(1)
    
    print("\n=== Knowledge Graph Creation Complete ===")
    print(f"Unified knowledge graph saved to {args.output_dir}/deliberation_kg.*")
    print("You can now visualize the knowledge graph using the visualize_kg.html page")

if __name__ == "__main__":
    main()
