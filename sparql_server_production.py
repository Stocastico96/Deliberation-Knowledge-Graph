#!/usr/bin/env python3

import logging
import argparse
from flask import Flask, request, jsonify, send_from_directory
from rdflib import Graph
import time
import threading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
knowledge_graph = None

@app.route('/')
def index():
    """Pagina principale"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return jsonify({'error': 'File index.html non trovato'}), 404
    except Exception as e:
        logger.error(f"Errore nel servire l'index: {str(e)}")
        return jsonify({'error': f'Errore nel servire l\'index: {str(e)}'}), 500

@app.route('/contributions')
def contributions():
    """Pagina per esplorare le contribution"""
    try:
        with open('contributions.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return jsonify({'error': 'File contributions non trovato'}), 404
    except Exception as e:
        logger.error(f"Errore nel servire contributions: {str(e)}")
        return jsonify({'error': f'Errore nel servire contributions: {str(e)}'}), 500

@app.route('/visualize')
def visualize():
    """Pagina di visualizzazione del knowledge graph"""
    try:
        with open('visualize_kg.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return jsonify({'error': 'File di visualizzazione non trovato'}), 404
    except Exception as e:
        logger.error(f"Errore nel servire la visualizzazione: {str(e)}")
        return jsonify({'error': f'Errore nel servire la visualizzazione: {str(e)}'}), 500

@app.route('/api/stats')
def api_stats():
    """API per ottenere statistiche del knowledge graph"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500

    try:
        # Query semplificata per conteggi
        stats = {}

        # Total triples
        stats['totalTriples'] = len(knowledge_graph)

        # Count contributions
        query_contributions = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        SELECT (COUNT(DISTINCT ?contribution) AS ?count) WHERE {
            ?contribution a del:Contribution .
        }
        """
        result = list(knowledge_graph.query(query_contributions))
        stats['totalContributions'] = int(result[0][0]) if result and result[0][0] else 0

        # Count participants
        query_participants = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        SELECT (COUNT(DISTINCT ?participant) AS ?count) WHERE {
            ?participant a del:Participant .
        }
        """
        result = list(knowledge_graph.query(query_participants))
        stats['totalParticipants'] = int(result[0][0]) if result and result[0][0] else 0

        # Count processes
        query_processes = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        SELECT (COUNT(DISTINCT ?process) AS ?count) WHERE {
            ?process a del:DeliberationProcess .
        }
        """
        result = list(knowledge_graph.query(query_processes))
        stats['totalProcesses'] = int(result[0][0]) if result and result[0][0] else 0

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Errore nel calcolare le statistiche: {str(e)}")
        return jsonify({'error': f'Errore nel calcolare le statistiche: {str(e)}'}), 500

@app.route('/api/contributions')
def api_contributions():
    """API ottimizzata per ottenere contributions con platform organization"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500

    try:
        # Query semplificata e veloce
        query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        SELECT DISTINCT ?contribution ?text ?timestamp ?participantName ?processName ?platform WHERE {
            ?contribution a del:Contribution .
            OPTIONAL { ?contribution del:text ?text }
            OPTIONAL { ?contribution del:timestamp ?timestamp }
            OPTIONAL {
                ?contribution del:madeBy ?participant .
                ?participant del:name ?participantName
            }
            OPTIONAL {
                ?process del:hasContribution ?contribution .
                ?process del:name ?processName .
                OPTIONAL { ?process del:platform ?platform }
            }
        }
        ORDER BY ?processName ?timestamp
        LIMIT 100
        """

        results = knowledge_graph.query(query)

        # Organizza per platform
        platforms = {}

        for row in results:
            process_name = str(row.processName) if row.processName else 'Unknown Process'
            platform = str(row.platform) if row.platform else None

            # Determina platform dal nome se non definito esplicitamente
            if not platform:
                if 'madrid' in process_name.lower() or 'decide madrid' in process_name.lower():
                    platform = 'Decide Madrid'
                elif 'parliament' in process_name.lower() or 'ep_debate' in process_name.lower():
                    platform = 'European Parliament'
                elif 'decidim' in process_name.lower() or 'barcelona' in process_name.lower():
                    platform = 'Decidim Barcelona'
                elif 'delidata' in process_name.lower():
                    platform = 'DeliData'
                elif 'habermas' in process_name.lower():
                    platform = 'Habermas Machine'
                elif 'eu_have_your_say' in process_name.lower() or 'have your say' in process_name.lower():
                    platform = 'EU Have Your Say'
                elif 'supreme_court' in process_name.lower() or 'us_supreme' in process_name.lower():
                    platform = 'US Supreme Court'
                else:
                    platform = 'Other Platform'

            if platform not in platforms:
                platforms[platform] = {
                    'name': platform,
                    'processes': {}
                }

            if process_name not in platforms[platform]['processes']:
                platforms[platform]['processes'][process_name] = {
                    'name': process_name,
                    'contributions': []
                }

            contribution = {
                'uri': str(row.contribution) if row.contribution else None,
                'text': str(row.text) if row.text else '',
                'timestamp': str(row.timestamp) if row.timestamp else None,
                'participantName': str(row.participantName) if row.participantName else 'Unknown',
                'processName': process_name,
                'platform': platform
            }

            platforms[platform]['processes'][process_name]['contributions'].append(contribution)

        return jsonify({'platforms': platforms})

    except Exception as e:
        logger.error(f"Errore nell'API contributions: {str(e)}")
        return jsonify({'error': f'Errore nell\'API contributions: {str(e)}'}), 500

@app.route('/api/export/<format>')
def api_export(format):
    """API per esportare il knowledge graph"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500

    try:
        if format.lower() == 'ttl' or format.lower() == 'turtle':
            content = knowledge_graph.serialize(format='turtle')
            mimetype = 'text/turtle'
            filename = 'deliberation_kg.ttl'
        elif format.lower() == 'rdf' or format.lower() == 'xml':
            content = knowledge_graph.serialize(format='xml')
            mimetype = 'application/rdf+xml'
            filename = 'deliberation_kg.rdf'
        elif format.lower() == 'json' or format.lower() == 'jsonld':
            content = knowledge_graph.serialize(format='json-ld')
            mimetype = 'application/ld+json'
            filename = 'deliberation_kg.jsonld'
        elif format.lower() == 'nt' or format.lower() == 'ntriples':
            content = knowledge_graph.serialize(format='nt')
            mimetype = 'application/n-triples'
            filename = 'deliberation_kg.nt'
        else:
            return jsonify({'error': f'Formato non supportato: {format}. Supportati: ttl, rdf, json, nt'}), 400

        from flask import Response
        return Response(
            content,
            mimetype=mimetype,
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )

    except Exception as e:
        logger.error(f"Errore nell'export: {str(e)}")
        return jsonify({'error': f'Errore nell\'export: {str(e)}'}), 500

@app.route('/sparql', methods=['GET', 'POST'])
def sparql_endpoint():
    """Endpoint SPARQL standard"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500

    if request.method == 'GET':
        query = request.args.get('query', '')
    else:
        query = request.form.get('query', '') or request.get_json().get('query', '')

    if not query:
        return jsonify({'error': 'Query SPARQL mancante'}), 400

    try:
        results = knowledge_graph.query(query)

        # Format response as SPARQL JSON
        response_data = {
            'head': {'vars': []},
            'results': {'bindings': []}
        }

        results_list = list(results)
        if results_list and hasattr(results, 'vars'):
            response_data['head']['vars'] = [str(var) for var in results.vars]

            for row in results_list:
                binding = {}
                for i, var in enumerate(results.vars):
                    if i < len(row) and row[i] is not None:
                        value = row[i]
                        if hasattr(value, 'datatype') and value.datatype:
                            binding[str(var)] = {
                                'type': 'literal',
                                'value': str(value),
                                'datatype': str(value.datatype)
                            }
                        elif hasattr(value, 'language') and value.language:
                            binding[str(var)] = {
                                'type': 'literal',
                                'value': str(value),
                                'xml:lang': value.language
                            }
                        elif str(type(value)).find('Literal') >= 0:
                            binding[str(var)] = {
                                'type': 'literal',
                                'value': str(value)
                            }
                        else:
                            binding[str(var)] = {
                                'type': 'uri',
                                'value': str(value)
                            }
                response_data['results']['bindings'].append(binding)

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Errore nella query SPARQL: {str(e)}")
        return jsonify({'error': f'Errore nella query SPARQL: {str(e)}'}), 500

# Static file serving
@app.route('/js/<path:filename>')
def js_files(filename):
    return send_from_directory('js', filename)

@app.route('/css/<path:filename>')
def css_files(filename):
    return send_from_directory('css', filename)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

def load_knowledge_graph(kg_file):
    """Carica il knowledge graph"""
    global knowledge_graph

    try:
        logger.info(f"Caricamento knowledge graph da: {kg_file}")
        knowledge_graph = Graph()
        knowledge_graph.parse(kg_file, format='turtle')
        logger.info(f"Knowledge graph caricato: {len(knowledge_graph)} triple da {kg_file}")
        return True
    except Exception as e:
        logger.error(f"Errore nel caricare il knowledge graph: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='SPARQL Server per Deliberation Knowledge Graph - Production')
    parser.add_argument('--kg-file', required=True, help='Path del file knowledge graph (.ttl)')
    parser.add_argument('--port', type=int, default=8080, help='Porta del server (default: 8080)')
    parser.add_argument('--host', default='127.0.0.1', help='Host del server (default: 127.0.0.1)')

    args = parser.parse_args()

    print("=== DELIBERATION KNOWLEDGE GRAPH SERVER - PRODUCTION ===")

    # Carica il knowledge graph
    if not load_knowledge_graph(args.kg_file):
        print("Errore nel caricamento del knowledge graph")
        return 1

    print(f"Server avviato su http://{args.host}:{args.port}")
    print(f"Interfaccia principale: http://{args.host}:{args.port}/")
    print(f"Endpoint SPARQL: http://{args.host}:{args.port}/sparql")
    print(f"API Contributions: http://{args.host}:{args.port}/api/contributions")
    print(f"API Statistiche: http://{args.host}:{args.port}/api/stats")

    # Avvia il server Flask
    app.run(host=args.host, port=args.port, debug=False, threaded=True)

    return 0

if __name__ == '__main__':
    exit(main())