#!/usr/bin/env python3
"""
Script to fetch debate data from the European Parliament Open Data API.
This script collects data for 5 debates and structures it according to the project's requirements.
"""

import requests
import json
import os
import time
from datetime import datetime, timedelta

# API base URL
BASE_URL = "https://data.europarl.europa.eu/api/v2"

# Headers for the API request
HEADERS = {
    "User-Agent": "deliberation-kg-dev-1.0.0",
    "Accept": "application/ld+json"
}

def fetch_speeches(params=None, max_pages=5):
    """Fetch speeches from the EP API with pagination support"""
    url = f"{BASE_URL}/speeches"
    
    # Default parameters if none provided
    if params is None:
        # Use a specific date range that should have data
        # Using dates from 2022 to ensure we have data
        params = {
            "parliamentary-term": "10",
            "activity-type": "PLENARY_DEBATE_SPEECH",
            "sitting-date": "2022-01-01",
            "sitting-date-end": "2022-12-31",
            "language": "en",
            "include-output": "xml_fragment",  # Get full text of speeches
            "limit": 50  # Reduced limit to avoid potential issues
        }
    
    all_data = {"data": []}
    current_page = 0
    offset = 0
    
    while current_page < max_pages:
        try:
            # Update offset for pagination
            current_params = params.copy()
            current_params["offset"] = offset
            
            print(f"Making request to: {url} (page {current_page + 1})")
            print(f"With headers: {HEADERS}")
            print(f"With params: {current_params}")
            
            # Add a longer timeout to avoid connection issues
            response = requests.get(url, headers=HEADERS, params=current_params, timeout=30)
            
            print(f"Response status code: {response.status_code}")
            print(f"Response headers: {response.headers}")
            
            # If no content, break the loop
            if response.status_code == 204:
                print("No content returned (204 status code)")
                break
            
            # Print the first 500 characters of the response
            print(f"Response content (first 500 chars): {response.text[:500]}")
            
            response.raise_for_status()
            
            # Try to parse the JSON
            try:
                page_data = response.json()
                
                # If no data or empty data array, break the loop
                if not page_data or "data" not in page_data or not page_data["data"]:
                    print("No more data available")
                    break
                
                # Add the data from this page to our collection
                all_data["data"].extend(page_data["data"])
                
                # Update offset for next page
                offset += len(page_data["data"])
                
                # If we got fewer results than the limit, we've reached the end
                if len(page_data["data"]) < params["limit"]:
                    print(f"Received {len(page_data['data'])} items, fewer than limit ({params['limit']}). Ending pagination.")
                    break
                
                # Increment page counter
                current_page += 1
                
                # Respect rate limits with a longer pause
                print(f"Waiting 2 seconds before next request...")
                time.sleep(2)
                
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Full response content: {response.text}")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching speeches: {e}")
            # If we get a rate limit error (429), wait longer and retry
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 10))
                print(f"Rate limited. Waiting {retry_after} seconds before retrying...")
                time.sleep(retry_after)
                continue
            else:
                break
    
    print(f"Fetched a total of {len(all_data['data'])} speeches across {current_page + 1} pages")
    return all_data

def fetch_speech_details(speech_id):
    """Fetch details for a specific speech"""
    url = f"{BASE_URL}/speeches/{speech_id}"
    
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching speech details for ID {speech_id}: {e}")
        return None

def group_speeches_by_debate(speeches_data):
    """Group speeches by debate/sitting date"""
    debates = {}
    
    if not speeches_data or "data" not in speeches_data:
        return debates
    
    for speech in speeches_data["data"]:
        # Extract sitting date as debate identifier
        sitting_date = None
        
        # Try different possible locations for the sitting date
        if "sittingDate" in speech:
            sitting_date = speech["sittingDate"]
        elif "properties" in speech and "sittingDate" in speech["properties"]:
            sitting_date = speech["properties"]["sittingDate"]
        elif "@graph" in speech:
            # Try to find sitting date in the graph structure
            for item in speech["@graph"]:
                if "sittingDate" in item:
                    sitting_date = item["sittingDate"]
                    break
        
        # If we still don't have a sitting date, try to extract it from other fields
        if not sitting_date and "id" in speech:
            # Sometimes the ID contains the date in format SPEECH-9-YYYY-MM-DD
            id_parts = speech["id"].split("-")
            if len(id_parts) >= 4:
                try:
                    # Try to construct a date from the ID parts
                    year, month, day = id_parts[2], id_parts[3], id_parts[4]
                    sitting_date = f"{year}-{month}-{day}"
                except (IndexError, ValueError):
                    pass
        
        if sitting_date:
            if sitting_date not in debates:
                debates[sitting_date] = []
            debates[sitting_date].append(speech)
    
    return debates

def save_debate_data(debate_date, speeches, output_dir="./debates"):
    """Save debate data to a JSON file"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Format date for filename
    formatted_date = debate_date.replace("-", "")
    filename = f"{output_dir}/debate_{formatted_date}.json"
    
    # Structure the data
    debate_data = {
        "debate_date": debate_date,
        "debate_id": f"ep_debate_{formatted_date}",
        "source": "European Parliament Plenary Debates",
        "speeches": speeches,
        "metadata": {
            "collected_at": datetime.now().isoformat(),
            "source_api": "European Parliament Open Data API v2",
            "language": "en"
        }
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(debate_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved debate data to {filename}")
    return filename

def create_sample_file(debate_files, sample_path):
    """Create a sample file with excerpts from the debates"""
    sample_data = {
        "source": "European Parliament Plenary Debates",
        "description": "Sample of debates from the European Parliament plenary sessions",
        "debates": []
    }
    
    for debate_file in debate_files:
        try:
            with open(debate_file, 'r', encoding='utf-8') as f:
                debate_data = json.load(f)
                
                # Extract a sample with limited speeches
                sample_debate = {
                    "debate_date": debate_data["debate_date"],
                    "debate_id": debate_data["debate_id"],
                    "speeches_count": len(debate_data["speeches"]),
                    "sample_speeches": debate_data["speeches"][:3] if len(debate_data["speeches"]) > 3 else debate_data["speeches"]
                }
                
                sample_data["debates"].append(sample_debate)
        except Exception as e:
            print(f"Error processing {debate_file}: {e}")
    
    with open(sample_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print(f"Created sample file at {sample_path}")

def create_readme(output_path):
    """Create a README file with information about the dataset"""
    readme_content = """# European Parliament Debates Dataset

## Overview
This dataset contains transcripts of debates from the European Parliament plenary sessions. The data is collected from the European Parliament Open Data API.

## Data Structure
Each debate is stored as a JSON file with the following structure:
- `debate_date`: The date of the plenary session
- `debate_id`: A unique identifier for the debate
- `source`: The source of the data
- `speeches`: An array of speeches made during the debate
  - Each speech contains information about the speaker, content, and timing
- `metadata`: Additional information about the data collection

## Source
European Parliament Open Data API v2
URL: https://data.europarl.europa.eu/api/v2/speeches

## License
The data is subject to the European Parliament's data usage terms. Attribution is required.

## Collection Methodology
The data was collected using a Python script that queries the European Parliament Open Data API. The script fetches plenary debate speeches and groups them by sitting date.

## Data Format
All files are in JSON format.

## Sample Data
A sample of the dataset is available in the `sample` directory.
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"Created README at {output_path}")

def create_dataset_link(output_path):
    """Create a symbolic link placeholder for the full dataset"""
    link_content = """This file represents a symbolic link to the full dataset.
In a production environment, this would link to the complete European Parliament debates dataset.
For the actual data, please refer to the European Parliament Open Data API:
https://data.europarl.europa.eu/api/v2/speeches
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(link_content)
    
    print(f"Created dataset link placeholder at {output_path}")

def main():
    # Create output directories
    debates_dir = "./debates"
    sample_dir = "../sample"
    os.makedirs(debates_dir, exist_ok=True)
    os.makedirs(sample_dir, exist_ok=True)
    
    # Try different parameter combinations
    parameter_combinations = [
        # Try with different activity types
        {
            "parliamentary-term": "10",
            "activity-type": "PLENARY_DEBATE_SPEECH",
            "sitting-date": "2023-01-01",
            "sitting-date-end": "2023-12-31",
            "language": "en",
            "include-output": "xml_fragment",
            "limit": 50
        },
        # Try with a different format
        {
            "parliamentary-term": "10",
            "activity-type": "PLENARY_DEBATE_SPEECH",
            "sitting-date": "2024-01-01",
            "sitting-date-end": "2024-12-31",
            "language": "en",
            "include-output": "xml_fragment",
            "format": "application/rdf+xml",
            "limit": 50
        },
        # Try with a different activity type
        {
            "parliamentary-term": "10",
            "activity-type": "PROCEEDING_ACTIVITY",
            "sitting-date": "2024-01-01",
            "sitting-date-end": "2024-12-31",
            "language": "en",
            "include-output": "xml_fragment",
            "limit": 50
        },
        # Try with minimal parameters
        {
            "parliamentary-term": "10",
            "sitting-date": "2024-01-01",
            "sitting-date-end": "2024-12-31",
            "limit": 50
        },
        # Try with a different parliamentary term
        {
            "parliamentary-term": "9",
            "activity-type": "PLENARY_DEBATE_SPEECH",
            "sitting-date": "2019-01-01",
            "sitting-date-end": "2019-12-31",
            "language": "en",
            "include-output": "xml_fragment",
            "limit": 50
        }
    ]
    
    speeches_data = None
    
    # Try each parameter combination until we get data
    for params in parameter_combinations:
        print(f"Trying parameters: {params}")
        
        # Fetch speeches from the API
        print("Fetching speeches from the European Parliament API...")
        speeches_data = fetch_speeches(params)
        
        # If we got data, break the loop
        if speeches_data and "data" in speeches_data and speeches_data["data"]:
            print(f"Successfully fetched {len(speeches_data['data'])} speeches")
            break
        else:
            print("No data found with these parameters, trying next combination...")
    
    if not speeches_data or "data" not in speeches_data or not speeches_data["data"]:
        print("Failed to fetch speeches data from all date ranges.")
        return
    
    # Group speeches by debate
    debates = group_speeches_by_debate(speeches_data)
    print(f"Found {len(debates)} debates")
    
    if not debates:
        print("No debates found in the fetched speeches.")
        return
    
    # Select up to 5 debates
    debate_dates = list(debates.keys())[:5]
    saved_files = []
    
    # Save each debate
    for debate_date in debate_dates:
        speeches = debates[debate_date]
        print(f"Processing debate from {debate_date} with {len(speeches)} speeches")
        saved_file = save_debate_data(debate_date, speeches, debates_dir)
        saved_files.append(saved_file)
        
        # Respect API rate limits with a longer pause
        print("Waiting 3 seconds before processing next debate...")
        time.sleep(3)
    
    # Create sample file
    sample_path = "../sample/sample.json"
    create_sample_file(saved_files, sample_path)
    
    # Create README
    create_readme("../readme.txt")
    
    # Create dataset link placeholder
    create_dataset_link("../dataset.zip.link")
    
    print("Data collection complete!")

if __name__ == "__main__":
    main()
