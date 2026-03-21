#!/usr/bin/env python3
"""
Merge Collective Intelligence Project (CIP) data into the main Deliberation Knowledge Graph.

This script safely merges the newly generated CIP RDF files into the main knowledge graph,
creating a backup first and validating the merge.
"""

from rdflib import Graph
from pathlib import Path
from datetime import datetime
import sys

def create_backup(kg_file):
    """Create a timestamped backup of the knowledge graph."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = kg_file.parent / f"{kg_file.stem}_backup_{timestamp}.ttl"

    print(f"Creating backup: {backup_file.name}")

    # Copy file
    import shutil
    shutil.copy2(kg_file, backup_file)

    return backup_file

def merge_graphs(main_kg_file, cip_files):
    """Merge CIP graphs into the main knowledge graph."""

    # Load main knowledge graph
    print(f"\n[1/3] Loading main knowledge graph: {main_kg_file}")
    main_g = Graph()
    main_g.parse(str(main_kg_file), format='turtle')
    print(f"  Loaded {len(main_g)} triples")

    # Merge CIP files
    print(f"\n[2/3] Merging CIP data files...")
    total_new_triples = 0

    for cip_file in cip_files:
        if not cip_file.exists():
            print(f"  ⚠ File not found: {cip_file}")
            continue

        print(f"  Loading {cip_file.name}...")
        cip_g = Graph()
        cip_g.parse(str(cip_file), format='turtle')

        before_count = len(main_g)

        # Merge into main graph
        for triple in cip_g:
            main_g.add(triple)

        after_count = len(main_g)
        new_triples = after_count - before_count
        total_new_triples += new_triples

        print(f"    Added {new_triples} new triples ({len(cip_g)} total in file)")

    print(f"\n  Total new triples added: {total_new_triples}")
    print(f"  Final graph size: {len(main_g)} triples")

    return main_g, total_new_triples

def save_merged_graph(graph, output_file):
    """Save the merged graph to file."""
    print(f"\n[3/3] Saving merged graph to: {output_file}")
    graph.serialize(destination=str(output_file), format='turtle')
    print(f"  ✓ Saved successfully")

def validate_merge(original_count, new_count, added_triples):
    """Validate that the merge was successful."""
    print(f"\n{'='*60}")
    print("Validation:")
    print(f"  Original graph: {original_count:,} triples")
    print(f"  New triples added: {added_triples:,}")
    print(f"  Expected size: {original_count + added_triples:,}")
    print(f"  Actual size: {new_count:,}")

    if new_count >= original_count + added_triples:
        print(f"  ✓ Merge validated successfully!")
        return True
    else:
        print(f"  ✗ WARNING: Unexpected graph size!")
        return False

def main():
    """Main execution function."""
    print("="*60)
    print("Merging CIP Data into Main Deliberation Knowledge Graph")
    print("="*60)

    # Define file paths
    main_kg_file = Path("knowledge_graph/deliberation_kg.ttl")
    cip_files = [
        Path("knowledge_graph/cip_global_dialogue_2024.ttl"),
        Path("knowledge_graph/cip_global_dialogue_march_2025.ttl")
    ]

    # Verify main KG exists
    if not main_kg_file.exists():
        print(f"\n✗ ERROR: Main knowledge graph not found: {main_kg_file}")
        print("  Please ensure the file exists before merging.")
        sys.exit(1)

    # Get original size
    print(f"\nChecking original graph size...")
    original_g = Graph()
    original_g.parse(str(main_kg_file), format='turtle')
    original_count = len(original_g)
    print(f"  Original size: {original_count:,} triples")

    # Create backup
    backup_file = create_backup(main_kg_file)

    try:
        # Merge graphs
        merged_g, added_triples = merge_graphs(main_kg_file, cip_files)

        # Save merged graph
        save_merged_graph(merged_g, main_kg_file)

        # Validate
        if validate_merge(original_count, len(merged_g), added_triples):
            print(f"\n{'='*60}")
            print("✓ SUCCESS! CIP data merged into main knowledge graph")
            print(f"{'='*60}")
            print(f"\nBackup saved to: {backup_file.name}")
            print(f"\nYou can now:")
            print(f"  1. Test SPARQL queries on the updated KG")
            print(f"  2. Restart the SPARQL server to load new data")
            print(f"  3. Explore CIP contributions via the web interface")
        else:
            print(f"\n{'='*60}")
            print("⚠ WARNING: Validation failed!")
            print(f"{'='*60}")
            print(f"\nThe merge completed but validation showed unexpected results.")
            print(f"Backup is available at: {backup_file.name}")
            print(f"\nRecommended actions:")
            print(f"  1. Review the merged file manually")
            print(f"  2. If issues found, restore from backup")
            print(f"  3. Contact maintainer if problem persists")

    except Exception as e:
        print(f"\n✗ ERROR during merge: {e}")
        print(f"\nThe original file has been preserved.")
        print(f"Backup is available at: {backup_file.name}")
        sys.exit(1)

if __name__ == "__main__":
    main()
