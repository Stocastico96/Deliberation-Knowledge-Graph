# Collective Intelligence Project - Integration Complete ✅

**Date**: February 10, 2026
**Status**: Successfully Integrated

## Summary

The Collective Intelligence Project (CIP) Global Dialogue data has been successfully mapped to the Deliberation Knowledge Graph and merged into the main knowledge base.

## Datasets Integrated

### 1. Global Dialogue 2024 - "What future do you want?"
- **Participants**: 1,502
- **Contributions**: 19,669
- **Date**: September 4, 2024
- **Duration**: 11 days, 19:45:00
- **Questions**: Multiple elicitation questions about future visions
- **Platform**: Collective Intelligence Project
- **RDF File**: `knowledge_graph/cip_global_dialogue_2024.ttl` (11 MB)

### 2. Global Dialogue March 2025
- **Status**: Data structure created, awaiting full data
- **RDF File**: `knowledge_graph/cip_global_dialogue_march_2025.ttl`

## Statistics

| Metric | Value |
|--------|-------|
| Total RDF Triples Generated | 123,089 |
| Contributions Mapped | 19,669 |
| Participants Mapped | ~1,500 |
| Topics/Questions Mapped | ~20 |
| Knowledge Graph Size (Before) | 1,299,077 triples |
| Knowledge Graph Size (After) | 1,422,166 triples |
| **Growth** | **+9.5%** |

## Ontology Mapping

The CIP data has been mapped using the Deliberation Ontology:

- **DeliberationProcess** (`del:DeliberationProcess`)
  - URI: `resource:cip_global_dialogue_2024`
  - Platform: "Collective Intelligence Project"
  - Participant Count: 1502

- **Topics** (`del:Topic`)
  - Main topic: "What future do you want?"
  - Subtopics: Each elicitation question

- **Contributions** (`del:Contribution`)
  - 19,669 individual thoughts/responses
  - Each linked to participant, topic, and question
  - Full text preserved

- **Participants** (`del:Participant`, `foaf:Person`)
  - Anonymized participant IDs
  - Linked to their contributions

## Example SPARQL Queries

### Query 1: Count CIP Contributions
```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX resource: <https://svagnoni.linkeddata.es/resource/>

SELECT (COUNT(?contribution) AS ?count)
WHERE {
  resource:cip_global_dialogue_2024 del:hasContribution ?contribution .
}
```

### Query 2: Get Sample Contributions
```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX resource: <https://svagnoni.linkeddata.es/resource/>

SELECT ?contribution ?text ?question
WHERE {
  resource:cip_global_dialogue_2024 del:hasContribution ?contribution .
  ?contribution del:text ?text ;
                del:addresses ?topic .
  ?topic rdfs:label ?question .
}
LIMIT 10
```

### Query 3: Find Contributions by Topic
```sparql
PREFIX del: <https://w3id.org/deliberation/ontology#>
PREFIX resource: <https://svagnoni.linkeddata.es/resource/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?topic (COUNT(?contribution) AS ?count)
WHERE {
  resource:cip_global_dialogue_2024 del:hasContribution ?contribution .
  ?contribution del:addresses ?topic .
  ?topic rdfs:label ?topicLabel .
}
GROUP BY ?topic
ORDER BY DESC(?count)
```

## Files Created

### Mapping Scripts
1. `map_cip_to_kg.py` - Main mapping script
   - Processes CSV files from CIP Global Dialogue
   - Generates RDF triples following deliberation ontology
   - Handles participants, contributions, topics

2. `merge_cip_to_main_kg.py` - Merge script
   - Safely merges CIP data into main KG
   - Creates automatic backup
   - Validates merge integrity

### Data Files
- Source: `data/collective_intelligence_project/global dialogue data/`
  - `2024 GD1/verbatim_map.csv` (processed)
  - `2024 GD1/agreement.csv` (processed)
  - `2024 GD1/participants.csv`
  - `march 2025 GD/` (partially processed)

### Generated RDF
- `knowledge_graph/cip_global_dialogue_2024.ttl`
- `knowledge_graph/cip_global_dialogue_march_2025.ttl`

### Backup
- `knowledge_graph/deliberation_kg_backup_20260210_173714.ttl`

## Known Limitations

1. **Agreement Scores**: Not fully processed yet
   - Agreement data available but needs schema definition
   - Can be added in future update

2. **March 2025 Data**: Minimal structure created
   - Awaiting full dataset
   - Script ready to process when available

3. **Binary Preferences**: Not yet mapped
   - Data available in CSV files
   - Requires additional ontology properties

## Next Steps

### Immediate
- [x] Restart SPARQL server to load new data
- [ ] Test SPARQL queries
- [ ] Update web interface to highlight CIP data

### Future Enhancements
1. Add agreement score integration
2. Process March 2025 Global Dialogue when available
3. Add binary preference data
4. Create visualization specifically for CIP data
5. Cross-reference CIP contributions with other platforms

## Testing

To verify the integration:

```bash
# 1. Restart SPARQL server
cd /home/svagnoni/deliberation-knowledge-graph
./start_dkg_server.sh

# 2. Open SPARQL interface
https://svagnoni.linkeddata.es/sparql

# 3. Run test query
PREFIX del: <https://w3id.org/deliberation/ontology#>
SELECT ?process ?label WHERE {
  ?process a del:DeliberationProcess ;
           rdfs:label ?label .
  FILTER(CONTAINS(?label, "Global Dialogue"))
}
```

## Credits

- **Data Source**: Collective Intelligence Project
- **Dataset**: Global Dialogue 2024 - "What future do you want?"
- **Mapping**: Automated using custom Python scripts
- **Ontology**: Deliberation Ontology (https://w3id.org/deliberation/ontology#)
- **Integration Date**: February 10, 2026

## References

- Collective Intelligence Project: https://cip.org/
- Global Dialogue Platform: https://pol.is/
- Deliberation Knowledge Graph: https://svagnoni.linkeddata.es/

---

**Status**: ✅ Complete
**Last Updated**: February 10, 2026, 17:37 UTC
