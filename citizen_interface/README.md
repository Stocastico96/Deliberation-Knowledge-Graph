# DKG Citizen Interface

Web interface for citizens to explore the Deliberation Knowledge Graph through semantic search, graph navigation, and data download.

## Features

### 🔍 Hybrid Retrieval
- **Semantic Search**: Uses BGE-M3 embeddings for multilingual similarity search
- **BM25**: Classic keyword-based retrieval (excellent for technical terms)
- **SPARQL**: Direct full-text search on the knowledge graph
- **Reciprocal Rank Fusion**: Combines results from all three methods

### 📊 Interactive Navigation
- Explore deliberation processes
- Navigate contributions, arguments, and fallacies
- Graph visualization with D3.js
- Information about participants and political parties

### 💾 Data Download
Supported formats:
- RDF/Turtle (`.ttl`)
- JSON-LD (`.jsonld`)
- JSON (`.json`)
- CSV (`.csv`)

## Architecture

```
citizen_interface/
├── backend/
│   ├── api_server.py          # Flask API server
│   ├── retrieval_system.py    # Hybrid retrieval system
│   └── __init__.py
├── frontend/
│   ├── citizen.html           # Main page
│   ├── css/
│   │   └── citizen.css        # Custom styles
│   └── js/
│       └── citizen.js         # Frontend logic
├── data/
│   └── indexes/              # FAISS and BM25 indexes (auto-generated)
├── requirements.txt          # Python dependencies
├── start_citizen_interface.sh # Startup script
└── README.md                 # This file
```

## Installation

### Prerequisites
- Python 3.8+
- DKG knowledge graph in Turtle format (`.ttl`)

### Setup

1. **Navigate to directory**:
```bash
cd /home/svagnoni/deliberation-knowledge-graph/citizen_interface
```

2. **Create virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

## Startup

### Method 1: Automatic script
```bash
./start_citizen_interface.sh
```

### Method 2: Manual
```bash
source venv/bin/activate
cd backend
python api_server.py --kg-path ../../knowledge_graph/deliberation_kg.ttl --port 5001
```

The interface will be available at: **http://localhost:5001**

## Usage

### Search
1. Enter keywords (e.g., "chat control", "privacy", "climate change")
2. Select retrieval methods to use (Semantic/BM25/SPARQL)
3. Choose number of results
4. Click "Search"

### Navigation
- Click on a result to view full details
- Explore contributions, fallacies, and participants
- Visualize the relationship graph
- Return to results with "Back to results" button

### Download
In the "Download Data" section you can download:
- **Complete snapshot** of the knowledge graph
- **Specific data** in various formats

## API Endpoints

### `POST /api/search`
Hybrid search in the knowledge graph

**Request**:
```json
{
  "query": "chat control",
  "top_k": 10,
  "use_semantic": true,
  "use_bm25": true,
  "use_sparql": true
}
```

**Response**:
```json
{
  "results": [...],
  "query": "chat control",
  "total_results": 10
}
```

### `GET /api/process/<uri>`
Get complete process details

**Response**:
```json
{
  "uri": "https://...",
  "title": "...",
  "description": "...",
  "contributions": [...],
  "fallacies": [...],
  "participants": [...]
}
```

### `POST /api/download/<format>`
Download data (format: ttl, jsonld, json, csv)

**Request**:
```json
{
  "full_dump": true
}
```

### `GET /api/stats`
General KG statistics

**Response**:
```json
{
  "total_processes": 150,
  "total_contributions": 5000,
  "total_fallacies": 234,
  "platforms": [...]
}
```

### `GET /api/autocomplete?q=<query>`
Autocomplete suggestions

### `GET /api/health`
Health check

## Retrieval System

### BGE-M3 (Semantic Search)
- Model: `BAAI/bge-m3`
- Embedding dimension: 1024
- Multilingual (IT/EN/ES/FR/DE)
- Dense + sparse embeddings
- FAISS index for similarity search

### BM25 (Sparse Retrieval)
- TF-IDF based ranking
- Excellent for technical/legal terminology
- Complementary to embeddings

### SPARQL (Direct Search)
- Keyword search in knowledge graph
- Full-text on titles, descriptions, contributions
- Fast for precise queries

### Reciprocal Rank Fusion
Combines results from three methods using formula:
```
RRF(d) = Σ 1/(k + rank_i(d))
```
where `k=60` (standard parameter)

## Configuration

### Environment variables
```bash
export DKG_KG_PATH="/path/to/knowledge_graph.ttl"
export DKG_API_PORT=5001
export DKG_API_HOST="0.0.0.0"
```

### Performance
First run:
- Process extraction from KG: ~2-5 min
- Embedding generation (BGE-M3): ~5-10 min per 1000 processes
- FAISS index creation: ~1 min
- BM25 index creation: <1 min

Indexes are saved in `data/indexes/` and reused in subsequent runs.

## Integration with existing DKG

The citizen interface integrates seamlessly with existing DKG:
- Uses same tech stack (Flask + RDFLib + D3.js)
- Same CSS styling (color palette, components)
- Same namespaces and ontology
- Can be served as subdomain: `citizen.svagnoni.linkeddata.es`

## Deploy to citizen.svagnoni.linkeddata.es

When sysadmin configures the subdomain on port 80:

1. **Configure Nginx/Apache** to serve port 5001 on `citizen.svagnoni.linkeddata.es`

2. **Use systemd for auto-start**:
```bash
sudo cp citizen_interface.service /etc/systemd/system/
sudo systemctl enable citizen_interface
sudo systemctl start citizen_interface
```

3. **Configure SSL** with Let's Encrypt:
```bash
sudo certbot --nginx -d citizen.svagnoni.linkeddata.es
```

## Troubleshooting

### Error: "Knowledge graph not loaded"
- Verify `.ttl` file path is correct
- Check file permissions

### Slow embeddings
- First run requires time to generate embeddings
- Use GPU if available (install `faiss-gpu` instead of `faiss-cpu`)

### Out of memory
- Reduce batch size in `retrieval_system.py`
- Use lighter model (e.g., `all-MiniLM-L6-v2` instead of BGE-M3)

## Future Development

### TODO
- [ ] Add filters for date, platform, topic
- [ ] Implement semantic clustering for topics
- [ ] Add timeline visualization
- [ ] Custom export (select specific processes)
- [ ] Multilingual query expansion
- [ ] Cross-encoder reranking for complex queries
- [ ] Cache for frequent queries
- [ ] External API integration for platform mapping

## Author

Simone Vagnoni
CIRSFID, University of Bologna - OEG, Universidad Politecnica de Madrid

## License

See LICENSE in main DKG repository.
