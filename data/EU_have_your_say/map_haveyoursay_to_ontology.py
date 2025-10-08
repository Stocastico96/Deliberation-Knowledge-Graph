#!/usr/bin/env python3
"""
Map Have Your Say data to Deliberation Knowledge Graph Ontology
"""

import json
import csv
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime
import re

class HaveYourSayMapper:
    def __init__(self, input_dir, output_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def clean_text(self, text):
        """Clean text by removing special characters and normalizing whitespace"""
        if not text:
            return ""
        clean_text = re.sub(r'\s+', ' ', text)
        return clean_text.strip()

    def map_initiative_to_ontology(self, initiative_data):
        """Map a single initiative to the deliberation ontology format"""

        initiative_id = initiative_data.get('initiative_id', '')
        title = initiative_data.get('title', f'EU Consultation {initiative_id}')
        description = initiative_data.get('description', '')
        feedback_list = initiative_data.get('feedback', [])

        # Create deliberation process
        process = {
            "@context": {
                "del": "https://w3id.org/deliberation/ontology#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "dct": "http://purl.org/dc/terms/",
                "foaf": "http://xmlns.com/foaf/0.1/"
            },
            "@id": f"https://svagnoni.linkeddata.es/resource/process/eu_hys_{initiative_id}",
            "@type": "del:DeliberationProcess",
            "del:identifier": f"eu_hys_{initiative_id}",
            "del:name": self.clean_text(title),
            "dct:source": initiative_data.get('url', ''),
            "dct:created": initiative_data.get('scrape_date', datetime.now().isoformat()),
            "del:platform": "EU Have Your Say",
            "del:hasTopic": [],
            "del:hasParticipant": [],
            "del:hasContribution": []
        }

        # Add dates if available
        if initiative_data.get('consultation_start'):
            process["del:startDate"] = initiative_data['consultation_start']
        if initiative_data.get('consultation_end'):
            process["del:endDate"] = initiative_data['consultation_end']

        # Add description as topic
        if description:
            topic = {
                "@id": f"https://svagnoni.linkeddata.es/resource/topic/eu_hys_topic_{initiative_id}",
                "@type": "del:Topic",
                "del:identifier": f"eu_hys_topic_{initiative_id}",
                "del:name": self.clean_text(title),
                "del:description": self.clean_text(description)
            }
            process["del:hasTopic"].append(topic)

        # Add policy areas as additional topics
        for area in initiative_data.get('policy_areas', []):
            area_id = area.lower().replace(' ', '_')
            policy_topic = {
                "@id": f"https://svagnoni.linkeddata.es/resource/topic/policy_{area_id}",
                "@type": "del:Topic",
                "del:identifier": f"policy_{area_id}",
                "del:name": area
            }
            process["del:hasTopic"].append(policy_topic)

        # Process feedback/contributions
        participants_map = {}

        for i, feedback in enumerate(feedback_list):
            feedback_text = self.clean_text(feedback.get('text', ''))

            if not feedback_text or len(feedback_text) < 10:
                continue

            # Create participant
            country = feedback.get('country', '')
            org = feedback.get('organization', '')

            if org:
                participant_name = org
                participant_type = "del:Organization"
            else:
                participant_name = f"Participant_{country if country else i+1}"
                participant_type = "del:Participant"

            if participant_name not in participants_map:
                participant_id = f"eu_hys_participant_{initiative_id}_{len(participants_map)+1}"
                participant = {
                    "@id": f"https://svagnoni.linkeddata.es/resource/participant/{participant_id}",
                    "@type": participant_type,
                    "del:identifier": participant_id,
                    "del:name": participant_name
                }

                if country:
                    participant["del:country"] = country

                if org:
                    participant["foaf:name"] = org

                participants_map[participant_name] = participant
                process["del:hasParticipant"].append(participant)

            # Create contribution
            contribution_id = feedback.get('id', f"contrib_{initiative_id}_{i+1}")
            contribution = {
                "@id": f"https://svagnoni.linkeddata.es/resource/contribution/{contribution_id}",
                "@type": "del:Contribution",
                "del:identifier": contribution_id,
                "del:text": feedback_text,
                "del:madeBy": {"@id": participants_map[participant_name]["@id"]}
            }

            # Add date if available
            if feedback.get('date'):
                contribution["dct:created"] = feedback['date']

            # Link to main topic
            if process["del:hasTopic"]:
                contribution["del:hasTopic"] = {"@id": process["del:hasTopic"][0]["@id"]}

            process["del:hasContribution"].append(contribution)

        return process

    def convert_all_initiatives(self):
        """Convert all initiatives in the input directory"""

        # Find all initiative directories
        initiative_dirs = [d for d in self.input_dir.iterdir() if d.is_dir() and d.name.startswith('initiative_')]

        if not initiative_dirs:
            print(f"No initiative directories found in {self.input_dir}")
            return False

        print(f"Found {len(initiative_dirs)} initiatives to process")

        results = []
        all_processes = []

        for init_dir in initiative_dirs:
            try:
                # Load initiative JSON
                json_file = init_dir / "initiative.json"
                if not json_file.exists():
                    print(f"⚠ Skipping {init_dir.name}: No initiative.json found")
                    continue

                with open(json_file, 'r', encoding='utf-8') as f:
                    initiative_data = json.load(f)

                print(f"\nProcessing: {init_dir.name}")
                print(f"  Title: {initiative_data.get('title', 'N/A')[:80]}")
                print(f"  Feedback items: {len(initiative_data.get('feedback', []))}")

                # Map to ontology
                process = self.map_initiative_to_ontology(initiative_data)
                all_processes.append(process)

                # Save individual RDF/JSON-LD file
                initiative_id = initiative_data.get('initiative_id', init_dir.name.replace('initiative_', ''))
                output_file = self.output_dir / f"eu_hys_{initiative_id}.jsonld"

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(process, f, ensure_ascii=False, indent=2)

                print(f"  ✓ Saved to {output_file.name}")

                results.append({
                    'initiative_id': initiative_id,
                    'success': True,
                    'output_file': str(output_file)
                })

            except Exception as e:
                print(f"  ✗ Error processing {init_dir.name}: {e}")
                results.append({
                    'initiative_id': init_dir.name,
                    'success': False,
                    'error': str(e)
                })

        # Save combined file
        combined_file = self.output_dir / "eu_have_your_say_all.jsonld"
        with open(combined_file, 'w', encoding='utf-8') as f:
            json.dump({
                "@context": {
                    "del": "https://w3id.org/deliberation/ontology#",
                    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                    "xsd": "http://www.w3.org/2001/XMLSchema#",
                    "dct": "http://purl.org/dc/terms/",
                    "foaf": "http://xmlns.com/foaf/0.1/"
                },
                "@graph": all_processes
            }, f, ensure_ascii=False, indent=2)

        print(f"\n✓ Combined file saved to {combined_file}")

        # Save summary
        summary = {
            'total_initiatives': len(initiative_dirs),
            'successful': sum(1 for r in results if r.get('success', False)),
            'failed': sum(1 for r in results if not r.get('success', False)),
            'conversion_date': datetime.now().isoformat(),
            'output_directory': str(self.output_dir.absolute()),
            'results': results
        }

        summary_file = self.output_dir / "conversion_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print("CONVERSION COMPLETE")
        print(f"{'='*60}")
        print(f"Total initiatives: {summary['total_initiatives']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Output directory: {self.output_dir.absolute()}")
        print(f"{'='*60}")

        return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python map_haveyoursay_to_ontology.py <input_dir> [output_dir]")
        print("\nExample:")
        print("  python map_haveyoursay_to_ontology.py haveyoursay_data mapped_data")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "mapped_haveyoursay"

    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist")
        sys.exit(1)

    print(f"EU Have Your Say to Deliberation Ontology Mapper")
    print(f"{'='*60}")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*60}\n")

    mapper = HaveYourSayMapper(input_dir, output_dir)
    success = mapper.convert_all_initiatives()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()