# European Parliament Debates Conversion Tools

This directory contains tools for converting European Parliament verbatim debate transcripts into structured formats aligned with the Deliberation Knowledge Graph ontology.

## Overview

The European Parliament publishes verbatim reports of its plenary sessions in HTML format. These tools convert these HTML files into:

1. JSON format structured according to the deliberation ontology
2. RDF/OWL format that can be directly used with semantic web tools

## Files

- `convert_verbatim_to_json.py`: Converts full verbatim HTML files to JSON format
- `convert_verbatim_sample.py`: Converts a sample (first N lines) of verbatim HTML files to JSON format
- `convert_json_to_rdf.py`: Converts the JSON representation to RDF/OWL format
- `ep_debates/`: Directory containing the debate files
  - `verbatim_*.html`: Original verbatim HTML files
  - `debate_*.json`: Converted JSON files
  - `debate_*.rdf`: Converted RDF/OWL files

## Usage

### Converting Verbatim HTML to JSON

To convert a full verbatim HTML file to JSON:

```bash
python3 convert_verbatim_to_json.py ep_debates/verbatim_YYYY-MM-DD.html ep_debates/debate_YYYY-MM-DD.json
```

To convert only a sample (first N lines) of a verbatim HTML file:

```bash
python3 convert_verbatim_sample.py ep_debates/verbatim_YYYY-MM-DD.html ep_debates/debate_sample_YYYY-MM-DD.json --max-lines 150
```

### Converting JSON to RDF/OWL

To convert a JSON file to RDF/OWL format:

```bash
python3 convert_json_to_rdf.py ep_debates/debate_YYYY-MM-DD.json ep_debates/debate_YYYY-MM-DD.rdf
```

## Data Structure

### JSON Format

The JSON format follows this structure:

```json
{
  "@context": {
    "del": "https://w3id.org/deliberation/ontology#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
  },
  "@type": "del:DeliberationProcess",
  "del:identifier": "ep_debate_YYYYMMDD",
  "del:name": "European Parliament Debate - YYYY-MM-DD",
  "del:startDate": "YYYY-MM-DDT00:00:00Z",
  "del:endDate": "YYYY-MM-DDT23:59:59Z",
  "del:hasTopic": [
    {
      "@type": "del:Topic",
      "del:identifier": "topic_id",
      "del:name": "Topic Name"
    }
  ],
  "del:hasParticipant": [
    {
      "@type": "del:Participant",
      "del:identifier": "participant_id",
      "del:name": "Participant Name",
      "del:hasRole": {
        "@type": "del:Role",
        "del:name": "Role Name"
      },
      "del:isAffiliatedWith": {
        "@type": "del:Organization",
        "del:name": "Organization Name"
      }
    }
  ],
  "del:hasContribution": [
    {
      "@type": "del:Contribution",
      "del:identifier": "contribution_id",
      "del:text": "Contribution text",
      "del:timestamp": "YYYY-MM-DDThh:mm:ss",
      "del:madeBy": {"@id": "participant_id"}
    }
  ]
}
```

### RDF/OWL Format

The RDF/OWL format uses the following structure:

- `del:DeliberationProcess` for the debate
- `del:Topic` for debate topics
- `del:Participant` for speakers
- `del:Role` for participant roles
- `del:Organization` for political groups
- `del:Contribution` for speeches

## Ontology Alignment

The conversion process maps the verbatim HTML structure to the deliberation ontology:

- Debate → `del:DeliberationProcess`
- Topics → `del:Topic`
- Speakers → `del:Participant`
- Political Groups → `del:Organization`
- Speeches → `del:Contribution`

## Dependencies

- Python 3.6+
- BeautifulSoup4 (for HTML parsing)
- RDFLib (for RDF/OWL conversion)

Install dependencies:

```bash
pip install beautifulsoup4 rdflib
