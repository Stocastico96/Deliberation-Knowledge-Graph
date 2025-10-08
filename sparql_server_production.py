#!/usr/bin/env python3

import logging
import argparse
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from rdflib import Graph
import time
import threading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Abilita CORS per tutte le route
knowledge_graph = None
kg_file_path = None
graph_modified = False
last_save_time = None

@app.route('/')
def redirect_to_dkg():
    """Redirect root to /dkg"""
    from flask import redirect
    return redirect('/dkg')

@app.route('/dkg')
def index():
    """Pagina principale DKG"""
    try:
        with open('index_self_contained.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        # Fallback al file originale
        try:
            with open('index.html', 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except FileNotFoundError:
            return jsonify({'error': 'File index non trovato'}), 404
    except Exception as e:
        logger.error(f"Errore nel servire l'index: {str(e)}")
        return jsonify({'error': f'Errore nel servire l\'index: {str(e)}'}), 500

@app.route('/contributions')
@app.route('/dkg/contributions')
def contributions():
    """Pagina per esplorare le contribution"""
    try:
        with open('contributions_self_contained.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        # Fallback al file originale
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
@app.route('/dkg/visualize')
def visualize():
    """Pagina di visualizzazione del knowledge graph"""
    try:
        with open('visualize_kg_self_contained.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        # Fallback al file originale
        try:
            with open('visualize_kg.html', 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except FileNotFoundError:
            return jsonify({'error': 'File di visualizzazione non trovato'}), 404
    except Exception as e:
        logger.error(f"Errore nel servire la visualizzazione: {str(e)}")
        return jsonify({'error': f'Errore nel servire la visualizzazione: {str(e)}'}), 500

@app.route('/sparql_interface')
@app.route('/sparql_page')
@app.route('/dkg/sparql')
def sparql_interface():
    """Pagina interfaccia SPARQL"""
    try:
        with open('sparql_self_contained.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        # Fallback al file originale
        try:
            with open('sparql.html', 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except FileNotFoundError:
            return jsonify({'error': 'File SPARQL interface non trovato'}), 404
    except Exception as e:
        logger.error(f"Errore nel servire SPARQL interface: {str(e)}")
        return jsonify({'error': f'Errore nel servire SPARQL interface: {str(e)}'}), 500

@app.route('/api/stats')
@app.route('/dkg/api/stats')
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
@app.route('/dkg/api/contributions')
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
        LIMIT 1000
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
@app.route('/dkg/api/export/<format>')
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

@app.route('/knowledge_graph/deliberation_kg.jsonld')
@app.route('/dkg/knowledge_graph/deliberation_kg.jsonld')
def knowledge_graph_jsonld():
    """Serve knowledge graph in JSON-LD format for visualization"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500

    try:
        # Serializza il knowledge graph in JSON-LD
        jsonld_data = knowledge_graph.serialize(format='json-ld')
        from flask import Response
        return Response(jsonld_data, mimetype='application/ld+json')
    except Exception as e:
        logger.error(f"Errore nella serializzazione JSON-LD: {str(e)}")
        return jsonify({'error': f'Errore nella serializzazione: {str(e)}'}), 500

@app.route('/sparql', methods=['GET', 'POST'])
@app.route('/dkg/sparql', methods=['GET', 'POST'])
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

@app.route('/images/<filename>')
def serve_images(filename):
    """Serve immagini dalla directory root o images"""
    try:
        return send_from_directory('.', filename)
    except FileNotFoundError:
        return jsonify({'error': f'File {filename} non trovato'}), 404

@app.route('/<filename>.png')
@app.route('/<filename>.jpg')
@app.route('/<filename>.jpeg')
@app.route('/<filename>.gif')
@app.route('/<filename>.svg')
@app.route('/<filename>.ico')
def serve_root_images(filename):
    """Serve immagini dalla directory root"""
    import os
    for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico']:
        full_filename = filename + ext
        if os.path.exists(full_filename):
            try:
                return send_from_directory('.', full_filename)
            except FileNotFoundError:
                continue
    return jsonify({'error': f'Immagine {filename} non trovata'}), 404

@app.route('/api/platforms', methods=['GET'])
@app.route('/dkg/api/platforms', methods=['GET'])
def get_platforms():
    """
    Endpoint che restituisce dinamicamente tutte le piattaforme presenti nel grafo
    """
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500

    try:
        from rdflib import Namespace

        DEL = Namespace("https://w3id.org/deliberation/ontology#")

        # Query per trovare tutte le piattaforme con statistiche
        query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?platformName (COUNT(DISTINCT ?contribution) as ?count)
        WHERE {
            ?contribution a del:Contribution .
            OPTIONAL { ?contribution del:platform ?platformName }
            FILTER(BOUND(?platformName))
        }
        GROUP BY ?platformName
        ORDER BY DESC(?count)
        """

        results = knowledge_graph.query(query)
        platforms = []

        # Mappa nomi da del:platform a ID standard
        platform_name_to_id = {
            'your priorities': 'yourpriorities',
            'your fallacious priorities': 'yourpriorities'
        }

        # Mappa nomi leggibili (definita PRIMA del loop)
        platform_names = {
            'habermas': 'Habermas Machine',
            'decidemadrid': 'Decide Madrid',
            'ep_debate': 'European Parliament Debates',
            'haveyoursay': 'EU Have Your Say',
            'yourpriorities': 'Your Fallacious Priorities',
            'scotus': 'US Supreme Court',
            'decidim_barcelona': 'Decidim Barcelona',
            'delidata': 'DeliData'
        }

        for row in results:
            platform_name = str(row.platformName) if row.platformName else None
            # Access the SPARQL variable using dict-style or attribute, but avoid calling count() method
            count_value = row[1] if len(row) > 1 else 0  # Second column is the count
            count = int(str(count_value)) if count_value else 0

            if platform_name:
                # Normalizza il nome per mapping a ID standard
                platform_name_lower = platform_name.lower()
                platform_id = platform_name_to_id.get(platform_name_lower,
                    platform_name_lower.replace(' ', '_').replace('.', '_'))

                platforms.append({
                    'id': platform_id,
                    'name': platform_names.get(platform_id, platform_name),  # USA nome mappato!
                    'count': count
                })

        # SEMPRE cerca anche per URI pattern per includere piattaforme senza del:platform
        query_fallback = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>

        SELECT ?contribution
        WHERE {
            ?contribution a del:Contribution .
        }
        """

        results_fallback = knowledge_graph.query(query_fallback)
        platform_counts = {}

        for row in results_fallback:
            uri = str(row.contribution)
            # Estrai la piattaforma dall'URI
            if 'yourpriorities' in uri.lower() or '/point-' in uri.lower():
                platform_counts['yourpriorities'] = platform_counts.get('yourpriorities', 0) + 1
            elif 'habermas' in uri.lower() or 'hm_' in uri.lower():
                platform_counts['habermas'] = platform_counts.get('habermas', 0) + 1
            elif 'decidemadrid' in uri.lower() or 'madrid' in uri.lower() or 'dm_' in uri.lower():
                platform_counts['decidemadrid'] = platform_counts.get('decidemadrid', 0) + 1
            elif 'haveyoursay' in uri.lower() or 'eu_hys' in uri.lower():
                platform_counts['haveyoursay'] = platform_counts.get('haveyoursay', 0) + 1
            elif 'scotus' in uri.lower() or 'sc_' in uri.lower():
                platform_counts['scotus'] = platform_counts.get('scotus', 0) + 1
            elif 'decidim' in uri.lower() or 'db_' in uri.lower():
                platform_counts['decidim_barcelona'] = platform_counts.get('decidim_barcelona', 0) + 1
            elif 'delidata' in uri.lower() or 'dd_' in uri.lower():
                platform_counts['delidata'] = platform_counts.get('delidata', 0) + 1
            else:
                # Tutti gli altri (principalmente European Parliament con URI w3id.org/deliberation/resource/contribution_*)
                platform_counts['ep_debate'] = platform_counts.get('ep_debate', 0) + 1

        # Converti in lista
        platforms_from_uri = [
            {
                'id': pid,
                'name': platform_names.get(pid, pid.title()),
                'count': count
            }
            for pid, count in platform_counts.items()
        ]

        # Merge con piattaforme da del:platform (se presenti)
        platform_dict = {p['id']: p for p in platforms}
        for p in platforms_from_uri:
            if p['id'] not in platform_dict:
                platform_dict[p['id']] = p
            else:
                # Se esiste già, NON sommare (evita doppio conteggio)
                # Prendi il count maggiore tra i due
                platform_dict[p['id']]['count'] = max(platform_dict[p['id']]['count'], p['count'])
                platform_dict[p['id']]['name'] = p['name']  # Usa nome da platform_names

        platforms = list(platform_dict.values())
        platforms.sort(key=lambda x: x['count'], reverse=True)

        logger.info(f"Found {len(platforms)} platforms in knowledge graph")
        return jsonify({'platforms': platforms})

    except Exception as e:
        logger.error(f"Errore nel recupero delle piattaforme: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/ingest/fallacy', methods=['POST'])
@app.route('/dkg/api/ingest/fallacy', methods=['POST'])
def ingest_fallacy():
    """
    Endpoint per ricevere contributi da Your Priorities
    e integrarli nel Deliberation Knowledge Graph

    Expected JSON format:
    {
        "contribution_id": "point-123",
        "text": "Il testo del commento",
        "timestamp": "2025-10-07T10:30:00Z",
        "user_id": 456,
        "user_name": "Mario Rossi",
        "post_id": 789,
        "post_name": "Proposta nuovo parco",
        "group_id": 101,
        "group_name": "Community Roma",
        "community_id": 12,
        "community_name": "Città di Roma",
        "fallacies": [
            {
                "type": "Ad Hominem",
                "score": 0.85,
                "rationale": "Attacco alla persona"
            }
        ]
    }
    """
    if not knowledge_graph:
        logger.error("Knowledge graph non caricato")
        return jsonify({'error': 'Knowledge graph non caricato'}), 500

    try:
        from rdflib import URIRef, Literal, Namespace, RDF, RDFS, XSD
        from datetime import datetime
        import uuid

        data = request.json
        if not data:
            return jsonify({'error': 'Nessun dato ricevuto'}), 400

        logger.info(f"Ricevuta richiesta ingest per contribution: {data.get('contribution_id')}")

        # Define namespaces
        DEL = Namespace("https://w3id.org/deliberation/ontology#")
        YP = Namespace("https://yourpriorities.org/")

        # Create contribution URI
        contrib_id = data.get('contribution_id', f"point-{uuid.uuid4()}")
        contrib_uri = URIRef(f"{YP}{contrib_id}")

        # Add contribution as both Contribution and Argument
        knowledge_graph.add((contrib_uri, RDF.type, DEL.Contribution))
        knowledge_graph.add((contrib_uri, RDF.type, DEL.Argument))

        # Add platform name
        knowledge_graph.add((contrib_uri, DEL.platform, Literal("Your Priorities")))

        # Add text content
        if data.get('text'):
            knowledge_graph.add((contrib_uri, DEL.text, Literal(data['text'], lang='it')))

        # Add timestamp
        if data.get('timestamp'):
            knowledge_graph.add((contrib_uri, DEL.hasTimestamp,
                               Literal(data['timestamp'], datatype=XSD.dateTime)))

        # Create and link Participant (user)
        if data.get('user_id'):
            user_uri = URIRef(f"{YP}user-{data['user_id']}")
            knowledge_graph.add((user_uri, RDF.type, DEL.Participant))
            if data.get('user_name'):
                knowledge_graph.add((user_uri, RDFS.label, Literal(data['user_name'])))
                knowledge_graph.add((user_uri, DEL.name, Literal(data['user_name'])))

            # Link contribution to participant
            knowledge_graph.add((contrib_uri, DEL.madeBy, user_uri))

        # Create Topic (post/proposal)
        if data.get('post_id'):
            topic_uri = URIRef(f"{YP}post-{data['post_id']}")
            knowledge_graph.add((topic_uri, RDF.type, DEL.Topic))
            if data.get('post_name'):
                knowledge_graph.add((topic_uri, RDFS.label, Literal(data['post_name'])))
                knowledge_graph.add((topic_uri, DEL.name, Literal(data['post_name'])))

            # Link contribution to topic
            knowledge_graph.add((contrib_uri, DEL.isAbout, topic_uri))

            # Add supports/attacks relationship based on value
            value = data.get('value', 0)
            if value == 1:
                # FOR = supports the topic/post
                knowledge_graph.add((contrib_uri, DEL.supports, topic_uri))
            elif value == -1:
                # AGAINST = attacks the topic/post
                knowledge_graph.add((contrib_uri, DEL.attacks, topic_uri))

        # Handle point-to-point responses (parent_point_id)
        if data.get('parent_point_id'):
            parent_uri = URIRef(f"{YP}point-{data['parent_point_id']}")
            # Link as response
            knowledge_graph.add((contrib_uri, DEL.respondsTo, parent_uri))

            # Add supports/attacks relationship based on value
            value = data.get('value', 0)
            if value == 1:
                knowledge_graph.add((contrib_uri, DEL.supports, parent_uri))
            elif value == -1:
                knowledge_graph.add((contrib_uri, DEL.attacks, parent_uri))

        # Create DeliberationProcess (group/community)
        process_created = False
        if data.get('group_id'):
            process_uri = URIRef(f"{YP}group-{data['group_id']}")
            knowledge_graph.add((process_uri, RDF.type, DEL.DeliberationProcess))
            if data.get('group_name'):
                knowledge_graph.add((process_uri, RDFS.label, Literal(data['group_name'])))
                knowledge_graph.add((process_uri, DEL.name, Literal(data['group_name'])))

            # Link contribution to process
            knowledge_graph.add((contrib_uri, DEL.partOf, process_uri))

            # Link topic to process
            if data.get('post_id'):
                knowledge_graph.add((process_uri, DEL.hasTopic, topic_uri))

            # Link participant to process
            if data.get('user_id'):
                knowledge_graph.add((process_uri, DEL.hasParticipant, user_uri))

            process_created = True

        # Add fallacies
        fallacy_count = 0
        for fallacy in data.get('fallacies', []):
            fallacy_id = f"fallacy-{uuid.uuid4()}"
            fallacy_uri = URIRef(f"{YP}{fallacy_id}")

            # Create fallacy instance
            knowledge_graph.add((fallacy_uri, RDF.type, DEL.FallacyType))
            knowledge_graph.add((fallacy_uri, RDFS.label, Literal(fallacy.get('type'))))

            # Add confidence score
            if 'score' in fallacy:
                knowledge_graph.add((fallacy_uri, DEL.hasConfidence,
                                   Literal(fallacy['score'], datatype=XSD.float)))

            # Add rationale
            if 'rationale' in fallacy:
                knowledge_graph.add((fallacy_uri, RDFS.comment,
                                   Literal(fallacy['rationale'], lang='it')))

            # Link fallacy to contribution
            knowledge_graph.add((contrib_uri, DEL.containsFallacy, fallacy_uri))
            fallacy_count += 1

        logger.info(f"Ingest completato per {contrib_id}: {fallacy_count} fallacies, participant: {data.get('user_id')}, topic: {data.get('post_id')}, process: {process_created}")
        logger.info(f"Knowledge graph ora contiene {len(knowledge_graph)} triple")

        # Mark graph as modified (will be saved periodically)
        mark_graph_modified()

        return jsonify({
            'status': 'success',
            'contribution_id': contrib_id,
            'fallacies_added': fallacy_count,
            'participant_created': bool(data.get('user_id')),
            'topic_created': bool(data.get('post_id')),
            'process_created': process_created,
            'total_triples': len(knowledge_graph)
        }), 201

    except Exception as e:
        logger.error(f"Errore nell'ingest di fallacy: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def mark_graph_modified():
    """Marca il grafo come modificato"""
    global graph_modified
    graph_modified = True

def save_knowledge_graph():
    """Salva il knowledge graph su file"""
    global knowledge_graph, kg_file_path, graph_modified, last_save_time
    import time

    try:
        if not knowledge_graph or not kg_file_path:
            logger.warning("Knowledge graph o path non disponibili per il salvataggio")
            return False

        # Create backup of current file
        import shutil
        import os

        backup_path = f"{kg_file_path}.backup"
        if os.path.exists(kg_file_path):
            shutil.copy2(kg_file_path, backup_path)

        # Save graph to file
        knowledge_graph.serialize(destination=kg_file_path, format='turtle')
        graph_modified = False
        last_save_time = time.time()
        logger.info(f"Knowledge graph salvato: {len(knowledge_graph)} triple in {kg_file_path}")
        return True

    except Exception as e:
        logger.error(f"Errore nel salvare il knowledge graph: {e}")
        return False

def periodic_save_worker():
    """Worker thread per salvare periodicamente il grafo se modificato"""
    import time
    global graph_modified

    while True:
        time.sleep(300)  # Salva ogni 5 minuti
        if graph_modified:
            logger.info("Salvataggio periodico del knowledge graph...")
            save_knowledge_graph()

def load_knowledge_graph(kg_file):
    """Carica il knowledge graph"""
    global knowledge_graph, kg_file_path

    try:
        logger.info(f"Caricamento knowledge graph da: {kg_file}")
        knowledge_graph = Graph()
        knowledge_graph.parse(kg_file, format='turtle')
        kg_file_path = kg_file  # Store path for saving later
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
    print(f"Salvataggio automatico ogni 5 minuti")

    # Avvia worker thread per salvataggio periodico
    import threading
    save_thread = threading.Thread(target=periodic_save_worker, daemon=True)
    save_thread.start()

    # Avvia il server Flask
    app.run(host=args.host, port=args.port, debug=False, threaded=True)

    return 0

if __name__ == '__main__':
    exit(main())