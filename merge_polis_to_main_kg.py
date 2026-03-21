#!/usr/bin/env python3
"""
Merge Pol.is public conversations into main Knowledge Graph
Creates backup before merging
"""

from rdflib import Graph
from datetime import datetime
import shutil

# Paths
MAIN_KG = "/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/deliberation_kg.ttl"
POLIS_KG = "/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/polis_public_kg.ttl"
BACKUP_DIR = "/home/svagnoni/deliberation-knowledge-graph/knowledge_graph/backups"

def main():
    print("="*60)
    print("MERGING POL.IS PUBLIC DATA INTO MAIN KNOWLEDGE GRAPH")
    print("="*60)

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{BACKUP_DIR}/deliberation_kg_before_polis_{timestamp}.ttl"

    print(f"\n1. Creating backup: {backup_file}")
    shutil.copy(MAIN_KG, backup_file)
    print("   ✓ Backup created")

    # Load main KG
    print(f"\n2. Loading main knowledge graph...")
    main_g = Graph()
    main_g.parse(MAIN_KG, format='turtle')
    print(f"   ✓ Loaded {len(main_g):,} triples from main KG")

    # Load Pol.is KG
    print(f"\n3. Loading Pol.is knowledge graph...")
    polis_g = Graph()
    polis_g.parse(POLIS_KG, format='turtle')
    print(f"   ✓ Loaded {len(polis_g):,} triples from Pol.is KG")

    # Merge
    print(f"\n4. Merging graphs...")
    initial_count = len(main_g)
    main_g += polis_g
    final_count = len(main_g)
    added = final_count - initial_count

    print(f"   ✓ Merged successfully")
    print(f"   • Initial: {initial_count:,} triples")
    print(f"   • Added:   {added:,} triples")
    print(f"   • Final:   {final_count:,} triples")
    print(f"   • Growth:  +{(added/initial_count*100):.1f}%")

    # Save merged graph
    print(f"\n5. Saving merged knowledge graph...")
    main_g.serialize(destination=MAIN_KG, format='turtle')
    print(f"   ✓ Saved to {MAIN_KG}")

    print("\n" + "="*60)
    print("POL.IS MERGE COMPLETE!")
    print("="*60)
    print(f"Final knowledge graph: {final_count:,} triples")
    print(f"Backup location: {backup_file}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
