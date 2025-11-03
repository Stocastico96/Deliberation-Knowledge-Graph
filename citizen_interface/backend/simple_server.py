#!/usr/bin/env python3
"""
Simple Flask API server for Citizen Interface (without ML dependencies)
Uses only SPARQL for search
"""

import os
import json
import logging
from pathlib import Path

from flask import Flask, request, jsonify, send_file, Response, redirect
from flask_cors import CORS
from rdflib import Graph, Namespace, URIRef
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")

app = Flask(__name__)
CORS(app)

# Global knowledge graph
kg = None
processes_cache = []


def load_knowledge_graph(kg_path):
    """Load knowledge graph from file"""
    global kg
    logger.info(f"Loading knowledge graph from {kg_path}...")
    kg = Graph()
    kg.bind("del", DEL)
    kg.bind("rdfs", RDFS)
    kg.bind("dcterms", DCTERMS)
    kg.bind("foaf", FOAF)

    kg.parse(kg_path, format="turtle")
    logger.info(f"Loaded {len(kg)} triples")

    # Extract processes
    extract_processes()


def extract_processes():
    """Extract all processes from KG"""
    global processes_cache

    # First get all processes with their basic info
    query = """
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dcterms: <http://purl.org/dc/terms/>

    SELECT DISTINCT ?process ?title ?description ?date ?platform
           (COUNT(DISTINCT ?contribution) as ?contributions)
    WHERE {
        ?process a del:DeliberationProcess .
        OPTIONAL { ?process del:name ?title }
        OPTIONAL { ?process del:title ?title }
        OPTIONAL { ?process rdfs:label ?title }
        OPTIONAL { ?process del:description ?description }
        OPTIONAL { ?process dcterms:description ?description }
        OPTIONAL { ?process del:date ?date }
        OPTIONAL { ?process dcterms:date ?date }
        OPTIONAL { ?process del:startDate ?date }
        OPTIONAL { ?process del:endDate ?date }
        OPTIONAL { ?process del:platform ?platform }
        OPTIONAL { ?process del:hasContribution ?contribution }
    }
    GROUP BY ?process ?title ?description ?date ?platform
    """

    processes_cache = []
    results = kg.query(query)

    for row in results:
        process_uri = str(row.process)

        # Get contribution count from aggregated query
        contributions_count = int(row.contributions) if row.contributions else 0

        # For now, set fallacies and participants to 0 to speed up loading
        # These can be counted on-demand when viewing a specific process

        # Infer platform from URI if not specified
        platform = str(row.platform) if row.platform else "Unknown"
        if platform == "Unknown":
            if "eu_hys" in process_uri or "haveyoursay" in process_uri:
                platform = "EU Have Your Say"
            elif "ep_debate" in process_uri or "europarl" in process_uri:
                platform = "European Parliament"
            elif "decidim" in process_uri:
                platform = "Decidim"
            elif "decide_madrid" in process_uri:
                platform = "Decide Madrid"

        # Generate description if missing
        description = str(row.description) if row.description else ""
        if not description and "ep_debate" in process_uri:
            title = str(row.title) if row.title else "Untitled Process"
            description = f"Parliamentary debate from {title}"

        process = {
            'uri': process_uri,
            'title': str(row.title) if row.title else "Untitled Process",
            'description': description,
            'date': str(row.date) if row.date else "",
            'platform': platform,
            'contributions_count': contributions_count,
            'fallacies_count': 0,  # Will count on-demand
            'participants_count': 0  # Will count on-demand
        }
        processes_cache.append(process)

    total_contributions = sum(p['contributions_count'] for p in processes_cache)
    logger.info(f"Extracted {len(processes_cache)} processes with {total_contributions} total contributions")


@app.route('/')
def index():
    """Serve main page"""
    try:
        html_path = Path(__file__).parent.parent / 'frontend' / 'citizen.html'
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return jsonify({'error': 'Frontend not found'}), 404


@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files"""
    from flask import make_response
    # First try frontend/css directory
    css_dir = Path(__file__).parent.parent / 'frontend' / 'css'
    css_path = css_dir / filename

    if css_path.exists():
        response = make_response(send_file(css_path, mimetype='text/css'))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    # Fallback to main DKG css directory
    dkg_css_dir = Path(__file__).parent.parent.parent / 'css'
    dkg_css_path = dkg_css_dir / filename

    if dkg_css_path.exists():
        response = make_response(send_file(dkg_css_path, mimetype='text/css'))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    return jsonify({'error': 'CSS file not found'}), 404


@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JS files"""
    from flask import make_response
    js_dir = Path(__file__).parent.parent / 'frontend' / 'js'
    response = make_response(send_file(js_dir / filename, mimetype='application/javascript'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/images/<path:filename>')
def serve_images(filename):
    """Serve image files"""
    frontend_dir = Path(__file__).parent.parent / 'frontend'
    file_path = frontend_dir / filename
    if file_path.exists():
        return send_file(file_path)
    return jsonify({'error': 'Image not found'}), 404


@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'kg_loaded': kg is not None,
        'processes_count': len(processes_cache)
    })


@app.route('/api/stats')
def stats():
    """Get statistics"""
    total_contributions = 0
    total_fallacies = 0
    platforms = set()

    for p in processes_cache:
        total_contributions += p.get('contributions_count', 0)
        total_fallacies += p.get('fallacies_count', 0)
        platforms.add(p.get('platform', 'Unknown'))

    return jsonify({
        'total_processes': len(processes_cache),
        'total_contributions': total_contributions,
        'total_fallacies': total_fallacies,
        'platforms': list(platforms)
    })


@app.route('/api/search', methods=['POST'])
def search():
    """Simple search using SPARQL"""
    data = request.get_json()
    query = data.get('query', '').lower()
    top_k = data.get('top_k', 10)

    if not query:
        return jsonify({'error': 'No query provided'}), 400

    # Simple keyword search in titles and descriptions
    results = []
    for process in processes_cache:
        title = process.get('title', '').lower()
        description = process.get('description', '').lower()

        # Calculate simple relevance score
        score = 0
        if query in title:
            score += 10
        if query in description:
            score += 5

        # Check for word matches
        query_words = query.split()
        for word in query_words:
            if word in title:
                score += 3
            if word in description:
                score += 1

        if score > 0:
            result = process.copy()
            result['relevance_score'] = min(score / 20.0, 1.0)  # Normalize to 0-1
            results.append(result)

    # Sort by score
    results.sort(key=lambda x: x['relevance_score'], reverse=True)

    return jsonify({
        'results': results[:top_k],
        'query': query,
        'total_results': len(results)
    })


@app.route('/api/process/<path:uri>')
def get_process_path(uri):
    """Get process details (path parameter - for backward compatibility)"""
    if not uri.startswith('http'):
        uri = f"https://svagnoni.linkeddata.es/resource/process/{uri}"
    return _get_process_details(uri)

@app.route('/api/process')
def get_process_query():
    """Get process details (query parameter - Apache-friendly)"""
    uri = request.args.get('uri', '')
    if not uri:
        return jsonify({'error': 'URI parameter required'}), 400
    return _get_process_details(uri)

def _get_process_details(uri):
    """Internal function to get process details"""
    # Find process in cache
    for p in processes_cache:
        if p['uri'] == uri:
            # Get detailed info from KG
            process = p.copy()

            # Get contributions
            contributions_query = f"""
            PREFIX del: <https://w3id.org/deliberation/ontology#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            SELECT ?contribution ?text ?participant ?participantName ?responseTo ?timestamp
            WHERE {{
                <{uri}> del:hasContribution ?contribution .
                OPTIONAL {{ ?contribution del:text ?text }}
                OPTIONAL {{ ?contribution rdfs:comment ?text }}
                OPTIONAL {{ ?contribution del:madeBy ?participant }}
                OPTIONAL {{ ?participant foaf:name ?participantName }}
                OPTIONAL {{ ?participant del:name ?participantName }}
                OPTIONAL {{ ?contribution del:responseTo ?responseTo }}
                OPTIONAL {{ ?contribution del:timestamp ?timestamp }}
                OPTIONAL {{ ?contribution dcterms:created ?timestamp }}
            }}
            LIMIT 1000
            """

            contributions = []
            seen_contributions = {}  # Track unique contributions

            for row in kg.query(contributions_query):
                contrib_uri = str(row.contribution)

                # Skip if we've already processed this contribution
                if contrib_uri in seen_contributions:
                    continue

                author_name = str(row.participantName) if row.participantName else (str(row.participant) if row.participant else "Unknown")
                text = str(row.text) if row.text else ""

                # Skip empty texts
                if not text or text.strip() == "":
                    continue

                contribution_obj = {
                    'uri': contrib_uri,
                    'text': text,
                    'author': author_name
                }

                # Add responseTo if it exists
                if row.responseTo:
                    contribution_obj['responseTo'] = str(row.responseTo)

                # Add timestamp if it exists
                if row.timestamp:
                    contribution_obj['timestamp'] = str(row.timestamp)

                contributions.append(contribution_obj)
                seen_contributions[contrib_uri] = True

            process['contributions'] = contributions
            process['contributions_count'] = len(contributions)

            # Get fallacies
            fallacies_query = f"""
            PREFIX del: <https://w3id.org/deliberation/ontology#>
            SELECT ?fallacy ?type ?location
            WHERE {{
                ?fallacy del:inProcess <{uri}> .
                OPTIONAL {{ ?fallacy a ?type }}
                OPTIONAL {{ ?fallacy del:location ?location }}
            }}
            LIMIT 50
            """

            fallacies = []
            for row in kg.query(fallacies_query):
                fallacies.append({
                    'uri': str(row.fallacy),
                    'type': str(row.type) if row.type else "Unknown",
                    'location': str(row.location) if row.location else "N/A"
                })

            process['fallacies'] = fallacies

            # Get participants
            participants_query = f"""
            PREFIX del: <https://w3id.org/deliberation/ontology#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            SELECT DISTINCT ?participant ?name
            WHERE {{
                <{uri}> del:hasParticipant ?participant .
                OPTIONAL {{ ?participant foaf:name ?name }}
                OPTIONAL {{ ?participant del:name ?name }}
            }}
            LIMIT 500
            """

            participants = []
            seen_participants = set()

            for row in kg.query(participants_query):
                participant_uri = str(row.participant)

                # Skip duplicates
                if participant_uri in seen_participants:
                    continue
                seen_participants.add(participant_uri)

                name = str(row.name) if row.name else "Unknown Participant"

                participants.append({
                    'uri': participant_uri,
                    'name': name
                })

            process['participants'] = participants

            return jsonify(process)

    return jsonify({'error': 'Process not found'}), 404


@app.route('/api/resource')
def get_resource():
    """Get details of any RDF resource"""
    uri = request.args.get('uri', '')
    if not uri:
        return jsonify({'error': 'URI parameter required'}), 400

    # Query all triples where this URI is the subject
    query = f"""
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT ?predicate ?object
    WHERE {{
        <{uri}> ?predicate ?object .
    }}
    """

    properties = {}
    rdf_type = None

    for row in kg.query(query):
        pred = str(row.predicate)
        obj = str(row.object)

        # Extract local name from predicate URI
        pred_name = pred.split('#')[-1] if '#' in pred else pred.split('/')[-1]

        # Check for rdf:type
        if pred == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type":
            rdf_type = obj
            pred_name = "type"

        # Store property (handle multiple values)
        if pred_name in properties:
            if isinstance(properties[pred_name], list):
                properties[pred_name].append(obj)
            else:
                properties[pred_name] = [properties[pred_name], obj]
        else:
            properties[pred_name] = obj

    if not properties:
        return jsonify({'error': 'Resource not found'}), 404

    # If this is a Participant, also fetch their contributions
    contributions = []
    if rdf_type and 'Participant' in rdf_type:
        contributions_query = f"""
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        SELECT ?contribution ?text ?timestamp
        WHERE {{
            ?contribution del:madeBy <{uri}> .
            OPTIONAL {{ ?contribution del:text ?text }}
            OPTIONAL {{ ?contribution del:timestamp ?timestamp }}
        }}
        LIMIT 50
        """

        for row in kg.query(contributions_query):
            contrib_text = str(row.text) if row.text else ""
            if contrib_text and contrib_text.strip():
                contributions.append({
                    'uri': str(row.contribution),
                    'text': contrib_text[:200] + '...' if len(contrib_text) > 200 else contrib_text,
                    'timestamp': str(row.timestamp) if row.timestamp else None
                })

    result = {
        'uri': uri,
        'type': rdf_type,
        'properties': properties
    }

    if contributions:
        result['contributions'] = contributions

    return jsonify(result)


@app.route('/resource/<path:resource_path>')
def dereference_uri(resource_path):
    """Dereference URI - serve RDF data for resource URIs"""
    # Reconstruct full URI
    uri = f"https://svagnoni.linkeddata.es/resource/{resource_path}"

    # Check Accept header for content negotiation
    accept = request.headers.get('Accept', 'text/html')

    # Query for resource triples
    query = f"""
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    CONSTRUCT {{
        <{uri}> ?p ?o .
        ?o ?p2 ?o2 .
    }}
    WHERE {{
        <{uri}> ?p ?o .
        OPTIONAL {{ ?o ?p2 ?o2 }}
    }}
    """

    # Create a graph with the resource data
    from rdflib import Graph as RDFGraph
    resource_graph = RDFGraph()
    for triple in kg.query(query):
        resource_graph.add(triple)

    if len(resource_graph) == 0:
        return jsonify({'error': 'Resource not found'}), 404

    # Content negotiation
    if 'text/turtle' in accept or 'ttl' in accept:
        data = resource_graph.serialize(format='turtle')
        return Response(data, mimetype='text/turtle')
    elif 'application/rdf+xml' in accept:
        data = resource_graph.serialize(format='xml')
        return Response(data, mimetype='application/rdf+xml')
    elif 'application/ld+json' in accept or 'json-ld' in accept:
        data = resource_graph.serialize(format='json-ld')
        return Response(data, mimetype='application/ld+json')
    else:
        # Default: redirect to citizen interface with modal
        # The citizen interface will handle the URI parameter
        return redirect(f'https://citizen.svagnoni.linkeddata.es/?show_resource={uri}')


@app.route('/api/download/<format>', methods=['POST'])
def download(format):
    """Download data"""
    if format == 'ttl':
        output_path = Path('/tmp/dkg_export.ttl')
        kg.serialize(destination=str(output_path), format='turtle')
        return send_file(output_path, as_attachment=True, download_name='dkg_export.ttl')

    elif format == 'jsonld':
        output_path = Path('/tmp/dkg_export.jsonld')
        kg.serialize(destination=str(output_path), format='json-ld')
        return send_file(output_path, as_attachment=True, download_name='dkg_export.jsonld')

    elif format == 'json':
        return jsonify({
            'processes': processes_cache,
            'total': len(processes_cache)
        })

    elif format == 'csv':
        df = pd.DataFrame([{
            'uri': p['uri'],
            'title': p['title'],
            'description': p['description'][:200],
            'platform': p['platform'],
            'date': p['date']
        } for p in processes_cache])

        output_path = Path('/tmp/dkg_export.csv')
        df.to_csv(output_path, index=False)
        return send_file(output_path, as_attachment=True, download_name='dkg_export.csv')

    return jsonify({'error': 'Unsupported format'}), 400


@app.route('/api/download/process/<format>')
def download_process(format):
    """Download data for a single process"""
    uri = request.args.get('uri', '')
    if not uri:
        return jsonify({'error': 'URI parameter required'}), 400

    # Find process
    process = None
    for p in processes_cache:
        if p['uri'] == uri:
            process = p
            break

    if not process:
        return jsonify({'error': 'Process not found'}), 404

    # Query for all triples related to this process
    query = f"""
    PREFIX del: <https://w3id.org/deliberation/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    CONSTRUCT {{
        <{uri}> ?p ?o .
        ?contribution ?cp ?co .
        ?participant ?pp ?po .
        ?fallacy ?fp ?fo .
    }}
    WHERE {{
        <{uri}> ?p ?o .
        OPTIONAL {{
            <{uri}> del:hasContribution ?contribution .
            ?contribution ?cp ?co .
            OPTIONAL {{
                ?contribution del:madeBy ?participant .
                ?participant ?pp ?po .
            }}
        }}
        OPTIONAL {{
            ?fallacy del:inProcess <{uri}> .
            ?fallacy ?fp ?fo .
        }}
    }}
    """

    from rdflib import Graph as RDFGraph
    process_graph = RDFGraph()
    for triple in kg.query(query):
        process_graph.add(triple)

    if format == 'ttl':
        data = process_graph.serialize(format='turtle')
        filename = f"process_{process['uri'].split('/')[-1]}.ttl"
        return Response(data, mimetype='text/turtle', headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        })
    elif format == 'jsonld':
        data = process_graph.serialize(format='json-ld')
        filename = f"process_{process['uri'].split('/')[-1]}.jsonld"
        return Response(data, mimetype='application/ld+json', headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        })
    elif format == 'json':
        # Get full process details
        contributions_query = f"""
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        SELECT ?contribution ?text ?participant ?participantName
        WHERE {{
            <{uri}> del:hasContribution ?contribution .
            OPTIONAL {{ ?contribution del:text ?text }}
            OPTIONAL {{ ?contribution del:madeBy ?participant }}
            OPTIONAL {{ ?participant foaf:name ?participantName }}
        }}
        """
        contributions = []
        for row in kg.query(contributions_query):
            contributions.append({
                'uri': str(row.contribution),
                'text': str(row.text) if row.text else "",
                'author': str(row.participantName) if row.participantName else "Unknown"
            })

        result = {
            **process,
            'contributions': contributions
        }

        return jsonify(result)

    return jsonify({'error': 'Unsupported format'}), 400


@app.route('/api/autocomplete')
def autocomplete():
    """Autocomplete suggestions"""
    query = request.args.get('q', '').lower()

    if len(query) < 2:
        return jsonify({'suggestions': []})

    suggestions = set()
    for p in processes_cache:
        title = p.get('title', '')
        if query in title.lower():
            suggestions.add(title)
            if len(suggestions) >= 5:
                break

    return jsonify({'suggestions': list(suggestions)})


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--kg-path', required=True)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', default=5001, type=int)
    parser.add_argument('--debug', action='store_true', help='Enable Flask debug mode with reloader')

    args = parser.parse_args()

    load_knowledge_graph(args.kg_path)

    logger.info(f"Starting server on {args.host}:{args.port} (debug={args.debug})")
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=args.debug
    )


if __name__ == '__main__':
    main()
