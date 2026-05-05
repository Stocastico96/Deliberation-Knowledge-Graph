# European Parliament Debates Fallacy Analysis

This project provides tools to convert European Parliament verbatim debates into the Deliberation Knowledge Graph (DKG) format and analyze them for logical fallacies using the OpenRouter API with the Deepseek model.

## Overview

The system consists of several components:

1. **Data Conversion**: Transforms European Parliament verbatim HTML debates into structured JSON-LD and RDF formats aligned with the Deliberation Knowledge Graph ontology.
2. **Fallacy Detection**: Analyzes speech contributions for logical fallacies using the Deepseek AI model via OpenRouter.
3. **Knowledge Graph Integration**: Stores the data in a structured format that connects debates, participants, contributions, and detected fallacies.
4. **Reporting**: Generates reports on detected fallacies, including statistics and detailed analysis.

## Files

- `ep_debates_fallacy_analysis.py`: Main script that handles parsing, conversion, fallacy detection, and storage.
- `run_ep_fallacy_analysis.py`: Adapter script to run fallacy analysis on existing JSON debate files.
- `data/EU_parliament_debates/`: Directory containing European Parliament debate data and conversion scripts.

## Requirements

- Python 3.8+
- Required packages:
  - beautifulsoup4
  - rdflib
  - pandas
  - pydantic
  - langchain
  - langchain_community
  - requests

Install dependencies:

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Or install packages individually
pip install beautifulsoup4 rdflib pandas pydantic langchain langchain_community requests
```

**Note**: The OpenRouter API key is required for fallacy detection. The script includes a default key, but you may need to provide your own key if the default one doesn't work.

## Usage

### Processing HTML Debates

To process a European Parliament debate HTML file, detect fallacies, and convert to DKG format:

```bash
python ep_debates_fallacy_analysis.py process path/to/debate.html
```

This will:
1. Parse the HTML file
2. Extract debate metadata, topics, participants, and contributions
3. Analyze each contribution for logical fallacies
4. Store the data in a SQLite database
5. Generate JSON-LD and RDF files

Options:
- `--no-fallacies`: Skip fallacy analysis (faster processing)

### Analyzing Existing JSON Debates

If you already have debate data in JSON-LD format (compatible with the Deliberation ontology), you can run:

```bash
python run_ep_fallacy_analysis.py path/to/debate.json [output_report.json]
```

This will:
1. Load the debate from the JSON file
2. Analyze each contribution for logical fallacies
3. Store the results in the database
4. Generate a fallacy report

### Generating Fallacy Reports

To generate a report for a previously processed debate:

```bash
python ep_debates_fallacy_analysis.py report process_id --output report.json
```

Where `process_id` is the identifier of the debate (e.g., `ep_debate_20250310`).

### Listing Available Debates

To see all debates stored in the database:

```bash
python ep_debates_fallacy_analysis.py list
```

## Fallacy Detection

The system uses the Deepseek AI model via OpenRouter to detect logical fallacies in debate contributions. The following fallacy types are detected:

- Ad Hominem
- Straw Man
- False Dilemma
- Appeal to Authority
- Slippery Slope
- Circular Reasoning
- Hasty Generalization
- Appeal to Emotion
- Red Herring
- Tu Quoque
- And many others...

For each detected fallacy, the system provides:
- The type of fallacy
- The specific text segment containing the fallacy
- A confidence score (0-1)

## Database Schema

The system stores data in a SQLite database with the following tables:

- `deliberation_processes`: Stores debate metadata
- `topics`: Stores debate topics
- `participants`: Stores information about speakers
- `contributions`: Stores speech contributions
- `fallacies`: Stores detected fallacies

## Output Formats

The system generates several output files:

- `.jsonld`: JSON-LD representation of the debate aligned with the Deliberation ontology
- `.rdf`: RDF/XML representation for semantic web applications
- `_fallacy_report.json`: Detailed report of detected fallacies

## Example

```bash
# Process a debate HTML file
python ep_debates_fallacy_analysis.py process data/EU_parliament_debates/ep_debates/verbatim_2025-03-10.html

# Generate a fallacy report
python ep_debates_fallacy_analysis.py report ep_debate_20250310 --output fallacy_report.json

# Analyze an existing JSON debate file
python run_ep_fallacy_analysis.py data/EU_parliament_debates/ep_debates/debate_2025-03-10.json
```

## Integration with Deliberation Knowledge Graph

The output of this system is fully compatible with the Deliberation ontology, allowing for:

- Cross-dataset analysis of deliberative processes
- Semantic querying of debates, participants, and arguments
- Integration with other deliberation datasets
- Visualization of argument structures and fallacy patterns

## License

This project is licensed under the MIT License.

## Acknowledgments

- Simone Vagnoni, CIRSFID, University of Bologna & OEG, Universidad Politecnica de Madrid
- OpenRouter API for providing access to the Deepseek AI model
