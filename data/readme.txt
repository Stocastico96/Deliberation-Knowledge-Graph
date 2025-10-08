# European Parliament Debates Dataset

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
