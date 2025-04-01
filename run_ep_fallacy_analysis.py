#!/usr/bin/env python3
"""
Adapter script to run fallacy analysis on European Parliament debates.

This script:
1. Takes the existing European Parliament debate data
2. Runs the fallacy analysis using the ep_debates_fallacy_analysis.py script
3. Generates reports on the detected fallacies
"""

import os
import sys
import json
from datetime import datetime
from ep_debates_fallacy_analysis import DebateProcessingPipeline, DeliberationProcess, Topic, Participant, Contribution

def load_json_debate(json_file_path):
    """Load a debate from a JSON file in the DKG format."""
    print(f"Loading debate from JSON file: {json_file_path}")
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract basic process info
    process_id = data.get("dkg:identifier", "unknown_process")
    process_name = data.get("dkg:name", "Unknown Debate")
    
    # Parse dates
    start_date_str = data.get("dkg:startDate", datetime.now().isoformat())
    end_date_str = data.get("dkg:endDate", datetime.now().isoformat())
    
    try:
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
    except ValueError:
        start_date = datetime.now()
    
    try:
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
    except ValueError:
        end_date = datetime.now()
    
    # Create process object
    process = DeliberationProcess(
        id=process_id,
        name=process_name,
        start_date=start_date,
        end_date=end_date,
        topics=[],
        participants=[],
        contributions=[]
    )
    
    # Extract topics
    for topic_data in data.get("dkg:hasTopic", []):
        topic = Topic(
            id=topic_data.get("dkg:identifier", f"topic_{len(process.topics) + 1}"),
            name=topic_data.get("dkg:name", "Unknown Topic")
        )
        process.topics.append(topic)
    
    # Extract participants
    for participant_data in data.get("dkg:hasParticipant", []):
        # Get role if available
        role = None
        if "dkg:hasRole" in participant_data:
            role = participant_data["dkg:hasRole"].get("dkg:name")
        
        # Get affiliation if available
        affiliation = None
        if "dkg:isAffiliatedWith" in participant_data:
            affiliation = participant_data["dkg:isAffiliatedWith"].get("dkg:name")
        
        participant = Participant(
            id=participant_data.get("dkg:identifier", f"participant_{len(process.participants) + 1}"),
            name=participant_data.get("dkg:name", "Unknown Participant"),
            role=role,
            affiliation=affiliation
        )
        process.participants.append(participant)
    
    # Extract contributions
    for contribution_data in data.get("dkg:hasContribution", []):
        # Parse timestamp
        timestamp_str = contribution_data.get("dkg:timestamp", datetime.now().isoformat())
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            timestamp = datetime.now()
        
        # Get participant ID
        participant_id = None
        if "dkg:madeBy" in contribution_data and "@id" in contribution_data["dkg:madeBy"]:
            participant_id = contribution_data["dkg:madeBy"]["@id"]
        
        # Get topic ID
        topic_id = None
        if "dkg:hasTopic" in contribution_data and "@id" in contribution_data["dkg:hasTopic"]:
            topic_id = contribution_data["dkg:hasTopic"]["@id"]
        
        contribution = Contribution(
            id=contribution_data.get("dkg:identifier", f"contribution_{len(process.contributions) + 1}"),
            text=contribution_data.get("dkg:text", ""),
            timestamp=timestamp,
            participant_id=participant_id or "unknown_participant",
            topic_id=topic_id
        )
        process.contributions.append(contribution)
    
    return process

def main():
    """Main function to run the fallacy analysis."""
    if len(sys.argv) < 2:
        print("Usage: python run_ep_fallacy_analysis.py <json_file> [output_report]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_report = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(json_file):
        print(f"Error: File not found: {json_file}")
        sys.exit(1)
    
    # Initialize pipeline
    pipeline = DebateProcessingPipeline()
    
    # Load debate from JSON
    process = load_json_debate(json_file)
    
    # Analyze fallacies
    print(f"Analyzing fallacies in {len(process.contributions)} contributions...")
    for i, contribution in enumerate(process.contributions):
        print(f"Analyzing contribution {i+1}/{len(process.contributions)}: {contribution.id}")
        fallacies = pipeline.fallacy_detector.analyze_text(contribution.text)
        contribution.fallacies = fallacies
        if fallacies:
            print(f"Found {len(fallacies)} fallacies in contribution {contribution.id}")
            for fallacy in fallacies:
                print(f"  - {fallacy.type}: '{fallacy.segment}' (confidence: {fallacy.confidence})")
    
    # Store in database
    print("Storing process in database...")
    pipeline.db.store_deliberation_process(process)
    
    # Generate report
    if output_report or True:  # Always generate a report
        output_file = output_report or f"{os.path.splitext(json_file)[0]}_fallacy_report.json"
        print(f"Generating fallacy report: {output_file}")
        report = pipeline.generate_fallacy_report(process.id, output_file)
        
        # Print summary
        stats = report["statistics"]
        print("\nFallacy Analysis Summary:")
        print(f"Total contributions: {stats['total_contributions']}")
        print(f"Contributions with fallacies: {stats['contributions_with_fallacies']} ({stats['percentage_with_fallacies']:.2f}%)")
        
        if stats["fallacy_types"]:
            print("\nFallacy types detected:")
            for ft in stats["fallacy_types"]:
                print(f"  - {ft['type']}: {ft['count']} occurrences")
        
        if stats["participants_with_most_fallacies"]:
            print("\nParticipants with most fallacies:")
            for p in stats["participants_with_most_fallacies"]:
                print(f"  - {p['name']}: {p['fallacy_count']} fallacies")
    
    print("\nAnalysis completed successfully!")

if __name__ == "__main__":
    main()
