#!/usr/bin/env python3
"""
Server web Python per servire il Deliberation Knowledge Graph
e gestire query SPARQL attraverso un'interfaccia web.
"""

import os
import json
import argparse
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from flask_cors import CORS
from rdflib import Graph, Namespace
from rdflib.plugins.sparql import prepareQuery
import logging

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inizializza Flask app
app = Flask(__name__)
CORS(app)  # Abilita CORS per richieste cross-origin

# Variabile globale per il knowledge graph
knowledge_graph = None

# Namespaces
DEL = Namespace("https://w3id.org/deliberation/ontology#")

def load_knowledge_graph(kg_file):
    """Carica il knowledge graph da file"""
    global knowledge_graph
    
    try:
        knowledge_graph = Graph()
        knowledge_graph.bind("del", DEL)
        
        # Determina il formato del file dall'estensione
        if kg_file.endswith('.ttl'):
            format_type = 'turtle'
        elif kg_file.endswith('.rdf') or kg_file.endswith('.xml'):
            format_type = 'xml'
        elif kg_file.endswith('.jsonld'):
            format_type = 'json-ld'
        elif kg_file.endswith('.n3'):
            format_type = 'n3'
        else:
            format_type = 'turtle'  # default
        
        knowledge_graph.parse(kg_file, format=format_type)
        logger.info(f"Knowledge graph caricato: {len(knowledge_graph)} triple da {kg_file}")
        return True
        
    except Exception as e:
        logger.error(f"Errore nel caricare il knowledge graph: {str(e)}")
        return False

@app.route('/')
def index():
    """Pagina principale del knowledge graph"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return jsonify({'error': 'File index.html non trovato'}), 404
    except Exception as e:
        logger.error(f"Errore nel servire index.html: {str(e)}")
        return jsonify({'error': f'Errore nel servire index.html: {str(e)}'}), 500

@app.route('/sparql-interface')
def sparql_interface():
    """Interfaccia SPARQL dedicata"""
    return render_template_string(WEB_INTERFACE_HTML)

@app.route('/sparql', methods=['GET', 'POST'])
def sparql_endpoint():
    """Endpoint SPARQL per eseguire query"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500
    
    if request.method == 'GET':
        query = request.args.get('query', '')
    else:
        # POST request
        content_type = request.headers.get('Content-Type', '')
        
        if 'application/sparql-query' in content_type:
            query = request.data.decode('utf-8')
        elif 'application/x-www-form-urlencoded' in content_type:
            query = request.form.get('query', '')
        else:
            data = request.get_json()
            query = data.get('query', '') if data else ''
    
    if not query:
        return jsonify({'error': 'Nessuna query fornita'}), 400
    
    try:
        # Esegui la query SPARQL
        results = knowledge_graph.query(query)
        
        # Converti i risultati in formato JSON compatibile con SPARQL
        response_data = {
            'head': {
                'vars': [str(var) for var in results.vars] if results.vars else []
            },
            'results': {
                'bindings': []
            }
        }
        
        # Converti i risultati in lista per gestirli meglio
        results_list = list(results)

        # Ottieni le variabili
        vars_list = []
        if hasattr(results, 'vars') and results.vars:
            vars_list = [str(var) for var in results.vars]
        elif results_list:
            # Fallback: usa la lunghezza della prima riga
            vars_list = [f'var{i}' for i in range(len(results_list[0]))]

        response_data['head']['vars'] = vars_list

        for row in results_list:
            binding = {}
            for i, var in enumerate(vars_list):
                if i < len(row) and row[i] is not None:
                    value = row[i]
                    try:
                        # Controlla se è un Literal
                        if hasattr(value, 'toPython') or str(type(value)).find('Literal') >= 0:
                            binding[var] = {
                                'type': 'literal',
                                'value': str(value)
                            }
                            # Controlla datatype solo se esiste l'attributo
                            if hasattr(value, 'datatype') and value.datatype:
                                binding[var]['datatype'] = str(value.datatype)
                            if hasattr(value, 'language') and value.language:
                                binding[var]['xml:lang'] = value.language
                        else:
                            # È un URIRef
                            binding[var] = {
                                'type': 'uri',
                                'value': str(value)
                            }
                    except Exception as ex:
                        # Fallback sicuro
                        binding[var] = {
                            'type': 'literal',
                            'value': str(value)
                        }
            response_data['results']['bindings'].append(binding)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Errore nell'esecuzione della query: {str(e)}")
        return jsonify({'error': f'Errore nella query: {str(e)}'}), 400

@app.route('/api/stats')
def api_stats():
    """API per ottenere statistiche del knowledge graph"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500
    
    try:
        # Query per ottenere statistiche
        stats_query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        
        SELECT 
            (COUNT(DISTINCT ?process) AS ?totalProcesses)
            (COUNT(DISTINCT ?participant) AS ?totalParticipants)
            (COUNT(DISTINCT ?contribution) AS ?totalContributions)
            (COUNT(DISTINCT ?topic) AS ?totalTopics)
            (COUNT(DISTINCT ?organization) AS ?totalOrganizations)
        WHERE {
            OPTIONAL { ?process a del:DeliberationProcess }
            OPTIONAL { ?participant a del:Participant }
            OPTIONAL { ?contribution a del:Contribution }
            OPTIONAL { ?topic a del:Topic }
            OPTIONAL { ?organization a del:Organization }
        }
        """
        
        results = knowledge_graph.query(stats_query)
        
        stats = {}
        for row in results:
            stats = {
                'totalTriples': len(knowledge_graph),
                'totalProcesses': int(row[0]) if row[0] else 0,
                'totalParticipants': int(row[1]) if row[1] else 0,
                'totalContributions': int(row[2]) if row[2] else 0,
                'totalTopics': int(row[3]) if row[3] else 0,
                'totalOrganizations': int(row[4]) if row[4] else 0
            }
            break
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Errore nel calcolare le statistiche: {str(e)}")
        return jsonify({'error': f'Errore nel calcolare le statistiche: {str(e)}'}), 500

@app.route('/api/processes')
def api_processes():
    """API per ottenere tutti i processi deliberativi"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500
    
    try:
        query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        
        SELECT ?process ?name ?startDate ?endDate
        WHERE {
            ?process a del:DeliberationProcess ;
                     del:name ?name .
            OPTIONAL { ?process del:startDate ?startDate }
            OPTIONAL { ?process del:endDate ?endDate }
        }
        ORDER BY ?startDate
        """
        
        results = knowledge_graph.query(query)
        
        processes = []
        for row in results:
            process = {
                'uri': str(row[0]),
                'name': str(row[1]),
                'startDate': str(row[2]) if row[2] else None,
                'endDate': str(row[3]) if row[3] else None
            }
            processes.append(process)
        
        return jsonify(processes)
        
    except Exception as e:
        logger.error(f"Errore nel recuperare i processi: {str(e)}")
        return jsonify({'error': f'Errore nel recuperare i processi: {str(e)}'}), 500

@app.route('/api/participants')
def api_participants():
    """API per ottenere tutti i partecipanti"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500
    
    try:
        query = """
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        
        SELECT ?participant ?name ?organization ?role
        WHERE {
            ?participant a del:Participant ;
                        del:name ?name .
            OPTIONAL { 
                ?participant del:isAffiliatedWith ?org .
                ?org del:name ?organization 
            }
            OPTIONAL { 
                ?participant del:hasRole ?r .
                ?r del:name ?role 
            }
        }
        ORDER BY ?name
        """
        
        results = knowledge_graph.query(query)
        
        participants = []
        for row in results:
            participant = {
                'uri': str(row[0]),
                'name': str(row[1]),
                'organization': str(row[2]) if row[2] else None,
                'role': str(row[3]) if row[3] else None
            }
            participants.append(participant)
        
        return jsonify(participants)
        
    except Exception as e:
        logger.error(f"Errore nel recuperare i partecipanti: {str(e)}")
        return jsonify({'error': f'Errore nel recuperare i partecipanti: {str(e)}'}), 500

@app.route('/api/search')
def api_search():
    """API per cercare nel knowledge graph"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500
    
    search_term = request.args.get('q', '').strip()
    if not search_term:
        return jsonify({'error': 'Termine di ricerca mancante'}), 400
    
    try:
        query = f"""
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        
        SELECT DISTINCT ?entity ?type ?name ?text
        WHERE {{
            {{
                ?entity a ?type ;
                       del:name ?name .
                FILTER(CONTAINS(LCASE(?name), LCASE("{search_term}")))
            }}
            UNION
            {{
                ?entity a del:Contribution ;
                       del:text ?text .
                FILTER(CONTAINS(LCASE(?text), LCASE("{search_term}")))
                BIND(del:Contribution AS ?type)
                OPTIONAL {{ ?entity del:name ?name }}
            }}
        }}
        LIMIT 50
        """
        
        results = knowledge_graph.query(query)
        
        search_results = []
        for row in results:
            result = {
                'uri': str(row[0]),
                'type': str(row[1]).split('#')[-1] if '#' in str(row[1]) else str(row[1]),
                'name': str(row[2]) if row[2] else None,
                'text': str(row[3])[:200] + '...' if row[3] and len(str(row[3])) > 200 else str(row[3]) if row[3] else None
            }
            search_results.append(result)
        
        return jsonify(search_results)
        
    except Exception as e:
        logger.error(f"Errore nella ricerca: {str(e)}")
        return jsonify({'error': f'Errore nella ricerca: {str(e)}'}), 500

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

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve file statici"""
    return send_from_directory('.', filename)

@app.route('/js/<path:filename>')
def js_files(filename):
    """Serve file JavaScript"""
    return send_from_directory('js', filename)

@app.route('/css/<path:filename>')
def css_files(filename):
    """Serve file CSS"""
    return send_from_directory('css', filename)

@app.route('/api/contributions')
def api_contributions():
    """API per ottenere contribution organizzate per piattaforma con contesto completo"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500

    try:
        # Query semplificata e ottimizzata per production
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
        LIMIT 200

            OPTIONAL { ?contribution del:text ?text }
            OPTIONAL { ?contribution del:timestamp ?timestamp }
            OPTIONAL { ?participant del:organization ?organization }
            OPTIONAL { ?process del:platform ?platform }
            OPTIONAL {
                ?process del:hasTopic ?topicUri .
                ?topicUri del:name ?topicName
            }

            BIND(?process AS ?processUri)
        }
        ORDER BY ?processName ?timestamp
        """

        results = knowledge_graph.query(query)

        # Organizza per piattaforma e processo
        platforms = {}

        for row in results:
            process_name = str(row.processName) if row.processName else 'Unknown Process'
            process_uri = str(row.processUri) if row.processUri else None

            # Determina piattaforma dal nome del processo
            platform = 'Unknown Platform'
            if 'madrid' in process_name.lower() or 'decide madrid' in process_name.lower():
                platform = 'Decide Madrid'
            elif 'parliament' in process_name.lower() or 'ep_debate' in str(process_uri).lower():
                platform = 'European Parliament'
            elif 'delidata' in process_name.lower() or 'delidata' in str(process_uri).lower():
                platform = 'DeliData'
            elif 'have your say' in process_name.lower() or 'eu_have_your_say' in str(process_uri).lower():
                platform = 'EU Have Your Say'
            elif 'habermas' in process_name.lower():
                platform = 'Habermas Machine'

            if platform not in platforms:
                platforms[platform] = {
                    'name': platform,
                    'processes': {}
                }

            if process_name not in platforms[platform]['processes']:
                platforms[platform]['processes'][process_name] = {
                    'name': process_name,
                    'uri': process_uri,
                    'contributions': [],
                    'topics': set()
                }

            # Aggiungi topic se presente
            if row.topicName:
                platforms[platform]['processes'][process_name]['topics'].add(str(row.topicName))

            contribution = {
                'uri': str(row.contribution) if row.contribution else None,
                'text': str(row.text) if row.text else '',
                'timestamp': str(row.timestamp) if row.timestamp else None,
                'participant': {
                    'name': str(row.participantName) if row.participantName else 'Unknown',
                    'organization': str(row.organization) if row.organization else None
                },
                'context': {
                    'platform': platform,
                    'process': process_name,
                    'topic': str(row.topicName) if row.topicName else None
                }
            }

            platforms[platform]['processes'][process_name]['contributions'].append(contribution)

        # Converte set in list per serializzazione JSON
        for platform in platforms.values():
            for process in platform['processes'].values():
                process['topics'] = list(process['topics'])

        return jsonify(platforms)

    except Exception as e:
        logger.error(f"Errore nella query contributions: {str(e)}")
        return jsonify({'error': f'Errore nella query contributions: {str(e)}'}), 500

@app.route('/api/contribution/<path:contribution_id>')
def api_contribution_detail(contribution_id):
    """API per ottenere dettagli di una contribution specifica"""
    if not knowledge_graph:
        return jsonify({'error': 'Knowledge graph non caricato'}), 500

    try:
        contribution_uri = f"https://w3id.org/deliberation/resource/{contribution_id}"

        query = f"""
        PREFIX del: <https://w3id.org/deliberation/ontology#>
        SELECT ?p ?o WHERE {{
            <{contribution_uri}> ?p ?o
        }}
        """

        results = knowledge_graph.query(query)
        properties = {}

        for row in results:
            prop = str(row.p).split('#')[-1] if '#' in str(row.p) else str(row.p).split('/')[-1]
            properties[prop] = str(row.o)

        return jsonify({
            'uri': contribution_uri,
            'properties': properties
        })

    except Exception as e:
        logger.error(f"Errore nella query contribution detail: {str(e)}")
        return jsonify({'error': f'Errore nella query contribution detail: {str(e)}'}), 500

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

def main():
    """Funzione principale"""
    parser = argparse.ArgumentParser(description='Server SPARQL per Deliberation Knowledge Graph')
    parser.add_argument('--kg-file', default='knowledge_graph/deliberation_kg.ttl', 
                       help='Path al file del knowledge graph')
    parser.add_argument('--host', default='localhost', help='Host del server')
    parser.add_argument('--port', type=int, default=5000, help='Porta del server')
    parser.add_argument('--debug', action='store_true', help='Modalità debug')
    
    args = parser.parse_args()
    
    print("=== DELIBERATION KNOWLEDGE GRAPH SERVER ===")
    print(f"Caricamento knowledge graph da: {args.kg_file}")
    
    if not os.path.exists(args.kg_file):
        print(f"Errore: File knowledge graph {args.kg_file} non trovato")
        print("Esegui prima lo script integrate_all_data_to_owl.py per creare il knowledge graph")
        return
    
    if not load_knowledge_graph(args.kg_file):
        print("Errore nel caricamento del knowledge graph")
        return
    
    print(f"Server avviato su http://{args.host}:{args.port}")
    print(f"Interfaccia SPARQL: http://{args.host}:{args.port}")
    print(f"Endpoint SPARQL: http://{args.host}:{args.port}/sparql")
    print(f"API statistiche: http://{args.host}:{args.port}/api/stats")
    
    app.run(host=args.host, port=args.port, debug=args.debug)

# Web Interface HTML Template
WEB_INTERFACE_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deliberation Knowledge Graph - Professional Platform (2025)</title>
    <meta name="description" content="Explore cross-platform deliberative democracy data with advanced visualization and SPARQL querying capabilities">
    <meta name="author" content="Linked Data Research Lab">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.6/dist/vis-network.min.js"></script>
    <style>
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --accent-color: #e74c3c;
            --success-color: #27ae60;
            --warning-color: #f39c12;
            --info-color: #8e44ad;
            --light-bg: #f8f9fa;
            --dark-bg: #2c3e50;
            --sidebar-width: 350px;
            --header-height: 70px;
        }

        /* WCAG AAA Accessibility Standards */
        * {
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #212529;
            margin: 0;
            padding: 0;
            background-color: var(--light-bg);
        }

        /* Skip to main content for screen readers */
        .skip-link {
            position: absolute;
            top: -40px;
            left: 6px;
            background: var(--primary-color);
            color: white;
            padding: 8px;
            text-decoration: none;
            z-index: 9999;
            border-radius: 4px;
        }

        .skip-link:focus {
            top: 6px;
        }

        /* Header */
        .header {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white;
            height: var(--header-height);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
        }

        .header .container-fluid {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .logo {
            display: flex;
            align-items: center;
            font-size: 1.5rem;
            font-weight: 700;
            text-decoration: none;
            color: white;
        }

        .logo:hover, .logo:focus {
            color: #ffffff;
            text-decoration: none;
        }

        .logo i {
            margin-right: 10px;
            font-size: 2rem;
        }

        /* Main Layout */
        .main-container {
            margin-top: var(--header-height);
            height: calc(100vh - var(--header-height));
            display: flex;
        }

        /* Sidebar */
        .sidebar {
            width: var(--sidebar-width);
            background: white;
            border-right: 1px solid #dee2e6;
            box-shadow: 2px 0 10px rgba(0,0,0,0.05);
            overflow-y: auto;
            flex-shrink: 0;
        }

        .sidebar-header {
            padding: 20px;
            background: var(--light-bg);
            border-bottom: 1px solid #dee2e6;
        }

        .sidebar-content {
            padding: 20px;
        }

        /* Network Visualization */
        .network-main {
            flex: 1;
            display: flex;
            flex-direction: column;
            position: relative;
        }

        .network-controls {
            background: white;
            padding: 15px 20px;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }

        .network-container {
            flex: 1;
            position: relative;
            background: #fafafa;
        }

        #network-visualization {
            width: 100%;
            height: 100%;
            border: none;
        }

        /* Info Panel */
        .info-panel {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            overflow: hidden;
        }

        .info-panel-header {
            background: var(--secondary-color);
            color: white;
            padding: 15px 20px;
            font-weight: 600;
            display: flex;
            align-items: center;
        }

        .info-panel-header i {
            margin-right: 10px;
        }

        .info-panel-body {
            padding: 20px;
        }

        /* Statistics Cards */
        .stat-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            border-left: 4px solid var(--secondary-color);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.12);
        }

        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--secondary-color);
            margin: 10px 0;
        }

        .stat-label {
            color: #666;
            font-size: 0.9rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Buttons */
        .btn-primary {
            background: var(--secondary-color);
            border-color: var(--secondary-color);
            font-weight: 600;
            padding: 10px 20px;
            border-radius: 6px;
            transition: all 0.2s;
        }

        .btn-primary:hover, .btn-primary:focus {
            background: #2980b9;
            border-color: #2980b9;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
        }

        .btn-outline-secondary {
            border-width: 2px;
            font-weight: 600;
        }

        /* Forms */
        .form-control, .form-select {
            border-radius: 6px;
            border: 2px solid #e9ecef;
            padding: 12px 15px;
            font-size: 0.95rem;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .form-control:focus, .form-select:focus {
            border-color: var(--secondary-color);
            box-shadow: 0 0 0 0.2rem rgba(52, 152, 219, 0.25);
        }

        /* Loading States */
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
            color: #666;
        }

        .spinner {
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid var(--secondary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 15px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Node Info Display */
        .node-info {
            background: #f8f9fa;
            border-radius: 6px;
            padding: 15px;
            margin-top: 10px;
            border-left: 4px solid var(--info-color);
        }

        .node-info h6 {
            color: var(--info-color);
            margin-bottom: 10px;
            font-weight: 700;
        }

        .property-item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            padding: 5px 0;
            border-bottom: 1px solid #e9ecef;
        }

        .property-label {
            font-weight: 600;
            color: #495057;
            flex: 0 0 40%;
        }

        .property-value {
            color: #212529;
            flex: 1;
            text-align: right;
            word-break: break-word;
        }

        /* Legend */
        .legend {
            background: white;
            border-radius: 6px;
            padding: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .legend-item {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }

        .legend-symbol {
            width: 20px;
            height: 20px;
            margin-right: 10px;
            border-radius: 3px;
            border: 2px solid #333;
        }

        .legend-label {
            font-size: 0.9rem;
            color: #495057;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .sidebar {
                width: 100%;
                position: absolute;
                z-index: 999;
                transform: translateX(-100%);
                transition: transform 0.3s;
            }

            .sidebar.show {
                transform: translateX(0);
            }

            .network-main {
                width: 100%;
            }

            .network-controls {
                padding: 10px;
            }
        }

        /* High Contrast Mode Support */
        @media (prefers-contrast: high) {
            .stat-card, .info-panel {
                border: 2px solid #000;
            }
        }

        /* Reduced Motion Support */
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }

        /* Focus Indicators for Accessibility */
        button:focus, .btn:focus, a:focus, input:focus, select:focus, textarea:focus {
            outline: 3px solid var(--secondary-color) !important;
            outline-offset: 2px !important;
        }

        /* Screen Reader Only Content */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }
    </style>
</head>
<body>
    <!-- Skip to main content for accessibility -->
    <a class="skip-link" href="#main-content">Skip to main content</a>

    <!-- Header -->
    <header class="header" role="banner">
        <div class="container-fluid">
            <a class="logo" href="#" role="img" aria-label="Deliberation Knowledge Graph Platform">
                <i class="fas fa-vote-yea" aria-hidden="true"></i>
                Deliberation Knowledge Graph
            </a>
            <nav role="navigation" aria-label="Main navigation">
                <button class="btn btn-outline-light d-md-none" type="button" data-bs-toggle="collapse" data-bs-target="#mobile-menu" aria-expanded="false" aria-controls="mobile-menu" aria-label="Toggle navigation">
                    <i class="fas fa-bars"></i>
                </button>
                <div class="collapse navbar-collapse d-md-block" id="mobile-menu">
                    <span class="text-white-50">Professional Platform - 2025</span>
                </div>
            </nav>
        </div>
    </header>

    <!-- Main Container -->
    <div class="main-container">
        <!-- Sidebar -->
        <aside class="sidebar" role="complementary" aria-label="Information panel">
            <div class="sidebar-header">
                <h2 class="h5 mb-0">
                    <i class="fas fa-info-circle text-primary"></i>
                    Knowledge Graph Explorer
                </h2>
            </div>

            <div class="sidebar-content">
                <!-- Statistics Panel -->
                <div class="info-panel">
                    <div class="info-panel-header">
                        <i class="fas fa-chart-bar"></i>
                        Statistics Overview
                    </div>
                    <div class="info-panel-body">
                        <div class="row g-3">
                            <div class="col-6">
                                <div class="stat-card">
                                    <div class="stat-number" id="stat-triples">-</div>
                                    <div class="stat-label">Triples</div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="stat-card">
                                    <div class="stat-number" id="stat-processes">-</div>
                                    <div class="stat-label">Processes</div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="stat-card">
                                    <div class="stat-number" id="stat-participants">-</div>
                                    <div class="stat-label">Participants</div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="stat-card">
                                    <div class="stat-number" id="stat-topics">-</div>
                                    <div class="stat-label">Topics</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Legend Panel -->
                <div class="info-panel">
                    <div class="info-panel-header">
                        <i class="fas fa-map-signs"></i>
                        Visualization Legend
                    </div>
                    <div class="info-panel-body">
                        <div class="legend">
                            <div class="legend-item">
                                <div class="legend-symbol" style="background: #3498db; border-radius: 50%;"></div>
                                <span class="legend-label">Deliberation Process</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-symbol" style="background: #e74c3c; border-radius: 50%;"></div>
                                <span class="legend-label">Participant</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-symbol" style="background: #f39c12; border-radius: 3px;"></div>
                                <span class="legend-label">Organization</span>
                            </div>
                            <div class="legend-item">
                                <div class="legend-symbol" style="background: #27ae60; clip-path: polygon(50% 0%, 0% 100%, 100% 100%);"></div>
                                <span class="legend-label">Topic</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Selected Node Info -->
                <div class="info-panel" id="node-info-panel" style="display: none;">
                    <div class="info-panel-header">
                        <i class="fas fa-search"></i>
                        Selected Node Details
                    </div>
                    <div class="info-panel-body">
                        <div id="node-details">
                            <p class="text-muted">Click on a node in the visualization to see detailed information.</p>
                        </div>
                    </div>
                </div>

                <!-- Platform Information -->
                <div class="info-panel">
                    <div class="info-panel-header">
                        <i class="fas fa-globe"></i>
                        Platforms Included
                    </div>
                    <div class="info-panel-body">
                        <ul class="list-unstyled">
                            <li><i class="fas fa-landmark text-primary"></i> EU Parliament</li>
                            <li><i class="fas fa-users text-info"></i> Decidim Barcelona</li>
                            <li><i class="fas fa-city text-warning"></i> Decide Madrid</li>
                            <li><i class="fas fa-balance-scale text-danger"></i> US Supreme Court</li>
                            <li><i class="fas fa-database text-success"></i> DeliData Research</li>
                            <li><i class="fas fa-comments text-secondary"></i> EU Have Your Say</li>
                            <li><i class="fas fa-brain text-dark"></i> Habermas Machine</li>
                        </ul>
                    </div>
                </div>
            </div>
        </aside>

        <!-- Main Network Visualization Area -->
        <main class="network-main" id="main-content" role="main">
            <!-- Network Controls -->
            <div class="network-controls">
                <div class="d-flex flex-wrap align-items-center gap-3">
                    <h1 class="h4 mb-0">
                        <i class="fas fa-project-diagram text-primary"></i>
                        Interactive Network Visualization
                    </h1>
                    <div class="ms-auto d-flex gap-2">
                        <button id="load-network" class="btn btn-primary" type="button" aria-describedby="network-help">
                            <i class="fas fa-play"></i>
                            Load Visualization
                        </button>
                        <button id="reset-view" class="btn btn-outline-secondary" type="button" disabled>
                            <i class="fas fa-expand-arrows-alt"></i>
                            Reset View
                        </button>
                        <button id="export-network" class="btn btn-outline-primary" type="button" disabled>
                            <i class="fas fa-download"></i>
                            Export
                        </button>
                        <button class="btn btn-outline-light d-md-none" type="button" onclick="toggleSidebar()" aria-label="Toggle sidebar">
                            <i class="fas fa-bars"></i>
                        </button>
                    </div>
                </div>
                <div id="network-help" class="text-muted small mt-2">
                    <i class="fas fa-info-circle"></i>
                    Explore relationships between deliberation processes, participants, organizations, and topics across multiple platforms.
                    Click nodes for details, drag to navigate, use mouse wheel to zoom.
                </div>

                <!-- Loading indicator -->
                <div class="loading" id="network-loading" role="status" aria-live="polite">
                    <div class="spinner"></div>
                    <p>Loading network visualization...</p>
                </div>
            </div>

            <!-- Network Visualization Container -->
            <div class="network-container">
                <div id="network-visualization" role="img" aria-label="Knowledge graph network visualization" tabindex="0"></div>

                <!-- Overlay for empty state -->
                <div id="empty-state" class="d-flex align-items-center justify-content-center h-100 text-center" style="position: absolute; top: 0; left: 0; right: 0; background: rgba(255,255,255,0.9);">
                    <div>
                        <i class="fas fa-network-wired fa-4x text-muted mb-3"></i>
                        <h3 class="text-muted">Network Visualization</h3>
                        <p class="text-muted">Click "Load Visualization" to explore the knowledge graph</p>
                        <p class="small text-muted">This interactive network shows real deliberation data from 7 platforms with full accessibility support</p>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- Professional Footer -->
    <footer class="bg-dark text-light py-4" role="contentinfo">
        <div class="container-fluid px-4">
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-primary">Deliberation Knowledge Graph Platform</h6>
                    <p class="mb-1 small">Professional platform for exploring cross-platform deliberative democracy data</p>
                    <p class="mb-0 small text-muted">© 2025 Linked Data Research Lab |
                        <a href="/sparql" class="text-light">SPARQL Endpoint</a> |
                        <a href="/api/stats" class="text-light">API Documentation</a>
                    </p>
                </div>
                <div class="col-md-6 text-md-end">
                    <small class="text-muted">
                        Deployed at <a href="https://svagnoni.linkeddata.es" class="text-light">svagnoni.linkeddata.es</a><br>
                        Built with accessibility standards (WCAG AAA) and best practices
                    </small>
                </div>
            </div>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Professional Network Visualization Platform - 2025
        // Enhanced with WCAG AAA accessibility and modern UX patterns

        // Global state management
        const AppState = {
            network: null,
            selectedNode: null,
            isLoading: false,
            data: {
                nodes: new vis.DataSet(),
                edges: new vis.DataSet()
            }
        };

        // Initialize application
        document.addEventListener('DOMContentLoaded', function() {
            initializeApp();
            setupEventListeners();
            loadStatistics();
        });

        function initializeApp() {
            // Announce app ready for screen readers
            announceToScreenReader('Deliberation Knowledge Graph Platform loaded and ready');

            // Focus management
            const mainContent = document.getElementById('main-content');
            if (mainContent) {
                mainContent.setAttribute('tabindex', '-1');
            }
        }

        function setupEventListeners() {
            // Network controls
            const loadBtn = document.getElementById('load-network');
            const resetBtn = document.getElementById('reset-view');
            const exportBtn = document.getElementById('export-network');

            if (loadBtn) {
                loadBtn.addEventListener('click', handleLoadNetwork);
                loadBtn.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleLoadNetwork();
                    }
                });
            }

            if (resetBtn) {
                resetBtn.addEventListener('click', handleResetView);
            }

            if (exportBtn) {
                exportBtn.addEventListener('click', handleExportNetwork);
            }

            // Keyboard navigation for network
            document.addEventListener('keydown', handleGlobalKeyboard);
        }

        function handleLoadNetwork() {
            if (AppState.isLoading) return;

            setLoadingState(true);
            announceToScreenReader('Loading network visualization...');

            loadNetworkVisualization()
                .then(() => {
                    setLoadingState(false);
                    announceToScreenReader('Network visualization loaded successfully');

                    // Enable other controls
                    document.getElementById('reset-view').disabled = false;
                    document.getElementById('export-network').disabled = false;
                })
                .catch(error => {
                    setLoadingState(false);
                    announceToScreenReader('Error loading network visualization');
                    console.error('Network loading error:', error);
                });
        }

        function handleResetView() {
            if (AppState.network) {
                AppState.network.fit();
                announceToScreenReader('Network view reset to fit all nodes');
            }
        }

        function handleExportNetwork() {
            if (!AppState.network) return;

            try {
                const canvas = AppState.network.canvas.frame.canvas;
                const link = document.createElement('a');
                link.download = 'deliberation-network.png';
                link.href = canvas.toDataURL();
                link.click();
                announceToScreenReader('Network exported as image');
            } catch (error) {
                console.error('Export error:', error);
                announceToScreenReader('Error exporting network');
            }
        }

        function handleGlobalKeyboard(event) {
            // Global keyboard shortcuts
            if (event.ctrlKey || event.metaKey) {
                switch(event.key) {
                    case 'r':
                        event.preventDefault();
                        handleResetView();
                        break;
                    case 'e':
                        event.preventDefault();
                        handleExportNetwork();
                        break;
                }
            }

            // Escape key to clear selection
            if (event.key === 'Escape' && AppState.selectedNode) {
                clearNodeSelection();
            }
        }

        function setLoadingState(loading) {
            AppState.isLoading = loading;
            const loadingEl = document.getElementById('network-loading');
            const emptyState = document.getElementById('empty-state');
            const loadBtn = document.getElementById('load-network');

            if (loading) {
                loadingEl.style.display = 'block';
                emptyState.style.display = 'none';
                loadBtn.disabled = true;
                loadBtn.setAttribute('aria-busy', 'true');
            } else {
                loadingEl.style.display = 'none';
                loadBtn.disabled = false;
                loadBtn.setAttribute('aria-busy', 'false');
            }
        }

        // Enhanced statistics loading with error handling
        function loadStatistics() {
            return fetch('/api/stats')
                .then(response => {
                    if (!response.ok) throw new Error('Failed to load statistics');
                    return response.json();
                })
                .then(data => {
                    updateStatisticsDisplay(data);
                })
                .catch(error => {
                    console.error('Statistics loading error:', error);
                    updateStatisticsDisplay({}, true);
                });
        }

        function updateStatisticsDisplay(data, isError = false) {
            const stats = {
                triples: data.totalTriples || 0,
                processes: data.totalProcesses || 0,
                participants: data.totalParticipants || 0,
                topics: data.totalTopics || 0
            };

            Object.entries(stats).forEach(([key, value]) => {
                const element = document.getElementById(`stat-${key}`);
                if (element) {
                    element.textContent = isError ? '!' : value.toLocaleString();
                    element.setAttribute('aria-label', `${key}: ${isError ? 'Error loading' : value}`);
                }
            });
        }

        // Enhanced network visualization with accessibility
        async function loadNetworkVisualization() {
            const networkQuery = `PREFIX del: <https://w3id.org/deliberation/ontology#>

SELECT ?source ?target ?sourceLabel ?targetLabel ?relation ?sourceType ?targetType ?platform
WHERE {
    {
        # Processes to Participants
        ?source a del:DeliberationProcess ;
                del:name ?sourceLabel ;
                del:platform ?platform ;
                del:hasParticipant ?target .
        ?target del:name ?targetLabel .
        BIND("hasParticipant" as ?relation)
        BIND("Process" as ?sourceType)
        BIND("Participant" as ?targetType)
    }
    UNION
    {
        # Participants to Organizations
        ?source a del:Participant ;
                del:name ?sourceLabel ;
                del:platform ?platform ;
                del:isAffiliatedWith ?target .
        ?target del:name ?targetLabel .
        BIND("affiliatedWith" as ?relation)
        BIND("Participant" as ?sourceType)
        BIND("Organization" as ?targetType)
    }
    UNION
    {
        # Add standalone entities
        ?source a ?type ;
                del:name ?sourceLabel .
        OPTIONAL { ?source del:platform ?platform }
        FILTER(?type IN (del:DeliberationProcess, del:Participant, del:Topic, del:Organization))
        BIND(?source as ?target)
        BIND(?sourceLabel as ?targetLabel)
        BIND("standalone" as ?relation)
        BIND(STRAFTER(STR(?type), "#") as ?sourceType)
        BIND(STRAFTER(STR(?type), "#") as ?targetType)
    }
}
LIMIT 200`;

            const response = await fetch('/sparql', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: networkQuery })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            if (data.results && data.results.bindings) {
                createEnhancedNetworkVisualization(data.results.bindings);
                document.getElementById('empty-state').style.display = 'none';
            } else {
                throw new Error('No network data received');
            }
        }

        function createEnhancedNetworkVisualization(connections) {
            const nodes = new vis.DataSet();
            const edges = new vis.DataSet();
            const nodeMap = new Map();

            console.log('Creating enhanced network with', connections.length, 'connections');

            if (connections.length === 0) {
                throw new Error('No connections found to visualize');
            }

            // Process connections with enhanced styling
            connections.forEach((connection, index) => {
                const sourceId = connection.source?.value || `node_${index}_source`;
                const targetId = connection.target?.value || `node_${index}_target`;
                const sourceLabel = connection.sourceLabel?.value || 'Unknown';
                const targetLabel = connection.targetLabel?.value || 'Unknown';
                const sourceType = connection.sourceType?.value || 'Unknown';
                const targetType = connection.targetType?.value || 'Unknown';
                const platform = connection.platform?.value || 'Unknown';
                const relation = connection.relation?.value || 'related';

                // Enhanced node creation with accessibility
                if (!nodeMap.has(sourceId)) {
                    nodeMap.set(sourceId, {
                        label: sourceLabel,
                        type: sourceType,
                        platform: platform
                    });

                    nodes.add(createAccessibleNode(sourceId, sourceLabel, sourceType, platform));
                }

                if (relation !== 'standalone' && sourceId !== targetId && !nodeMap.has(targetId)) {
                    nodeMap.set(targetId, {
                        label: targetLabel,
                        type: targetType,
                        platform: platform
                    });

                    nodes.add(createAccessibleNode(targetId, targetLabel, targetType, platform));
                }

                // Create edges with enhanced styling
                if (relation !== 'standalone' && sourceId !== targetId) {
                    edges.add(createAccessibleEdge(sourceId, targetId, relation, sourceLabel, targetLabel));
                }
            });

            // Create network with enhanced options
            const container = document.getElementById('network-visualization');
            const networkData = { nodes: nodes, edges: edges };

            const options = {
                nodes: {
                    borderWidth: 2,
                    shadow: true,
                    font: {
                        size: 14,
                        color: '#333333'
                    }
                },
                edges: {
                    width: 2,
                    shadow: true,
                    smooth: {
                        type: 'continuous'
                    }
                },
                physics: {
                    stabilization: {
                        enabled: true,
                        iterations: 100
                    },
                    barnesHut: {
                        gravitationalConstant: -8000,
                        springConstant: 0.001,
                        springLength: 200
                    }
                },
                interaction: {
                    hover: true,
                    selectConnectedEdges: true,
                    tooltipDelay: 200
                },
                layout: {
                    improvedLayout: true
                }
            };

            AppState.network = new vis.Network(container, networkData, options);

            // Enhanced event handlers
            AppState.network.on('click', handleNodeClick);
            AppState.network.on('hoverNode', handleNodeHover);
            AppState.network.on('blurNode', handleNodeBlur);
            AppState.network.on('stabilizationIterationsDone', () => {
                announceToScreenReader(`Network stabilized with ${nodes.length} nodes and ${edges.length} connections`);
            });

            // Store data references
            AppState.data = { nodes, edges };
        }

        function createAccessibleNode(id, label, type, platform) {
            const shortLabel = label.length > 30 ? label.substring(0, 27) + '...' : label;

            return {
                id: id,
                label: shortLabel,
                title: `${type}: ${label}\\nPlatform: ${platform}\\nClick for details`,
                group: platform,
                shape: getNodeShape(type),
                color: getNodeColor(platform),
                size: getNodeSize(type),
                font: {
                    size: 14,
                    color: getContrastColor(getNodeColor(platform))
                },
                // Accessibility properties
                'aria-label': `${type} node: ${label} from ${platform}`,
                role: 'button',
                tabindex: 0
            };
        }

        function createAccessibleEdge(fromId, toId, relation, sourceLabel, targetLabel) {
            const edgeColors = {
                'hasParticipant': '#3498db',
                'affiliatedWith': '#e74c3c',
                'aboutTopic': '#27ae60',
                'related': '#95a5a6'
            };

            return {
                from: fromId,
                to: toId,
                label: relation,
                title: `${relation}: ${sourceLabel} → ${targetLabel}`,
                color: {
                    color: edgeColors[relation] || '#95a5a6',
                    highlight: '#2c3e50'
                },
                arrows: 'to',
                font: { size: 11 }
            };
        }

        function getNodeShape(type) {
            const shapes = {
                'DeliberationProcess': 'box',
                'Process': 'box',
                'Participant': 'circle',
                'Organization': 'diamond',
                'Topic': 'triangle'
            };
            return shapes[type] || 'dot';
        }

        function getNodeColor(platform) {
            const colors = {
                'EU Parliament': '#3498db',
                'Decide Madrid': '#e74c3c',
                'Decidim Barcelona': '#f39c12',
                'US Supreme Court': '#27ae60',
                'Habermas Machine': '#9b59b6',
                'EU Have Your Say': '#1abc9c',
                'DeliData': '#e67e22'
            };
            return colors[platform] || '#95a5a6';
        }

        function getNodeSize(type) {
            const sizes = {
                'DeliberationProcess': 35,
                'Process': 35,
                'Participant': 25,
                'Organization': 30,
                'Topic': 28
            };
            return sizes[type] || 20;
        }

        function getContrastColor(bgColor) {
            // Simple contrast calculation for accessibility
            const hex = bgColor.replace('#', '');
            const r = parseInt(hex.substr(0, 2), 16);
            const g = parseInt(hex.substr(2, 2), 16);
            const b = parseInt(hex.substr(4, 2), 16);
            const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
            return luminance > 0.5 ? '#000000' : '#ffffff';
        }

        // Enhanced event handlers
        function handleNodeClick(params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                selectNode(nodeId);
            } else {
                clearNodeSelection();
            }
        }

        function handleNodeHover(params) {
            const nodeId = params.node;
            if (AppState.data.nodes.get(nodeId)) {
                // Could add hover effects here
            }
        }

        function handleNodeBlur(params) {
            // Clean up hover effects
        }

        function selectNode(nodeId) {
            AppState.selectedNode = nodeId;

            // Get node data
            const nodeData = AppState.data.nodes.get(nodeId);
            if (nodeData) {
                displayNodeDetails(nodeData);
                announceToScreenReader(`Selected ${nodeData.title || nodeData.label}`);
            }
        }

        function clearNodeSelection() {
            AppState.selectedNode = null;
            const panel = document.getElementById('node-info-panel');
            if (panel) {
                panel.style.display = 'none';
            }
        }

        function displayNodeDetails(nodeData) {
            const panel = document.getElementById('node-info-panel');
            const detailsDiv = document.getElementById('node-details');

            if (panel && detailsDiv) {
                const details = `
                    <div class="node-info">
                        <h6>${escapeHtml(nodeData.label || 'Unknown')}</h6>
                        <div class="property-item">
                            <span class="property-label">Type:</span>
                            <span class="property-value">${escapeHtml(nodeData.group || 'Unknown')}</span>
                        </div>
                        <div class="property-item">
                            <span class="property-label">Platform:</span>
                            <span class="property-value">${escapeHtml(nodeData.group || 'Unknown')}</span>
                        </div>
                        <div class="property-item">
                            <span class="property-label">Shape:</span>
                            <span class="property-value">${escapeHtml(nodeData.shape || 'Unknown')}</span>
                        </div>
                    </div>
                `;

                detailsDiv.innerHTML = details;
                panel.style.display = 'block';
            }
        }

        // Utility functions
        function announceToScreenReader(message) {
            const announcement = document.createElement('div');
            announcement.setAttribute('aria-live', 'polite');
            announcement.setAttribute('aria-atomic', 'true');
            announcement.className = 'sr-only';
            announcement.textContent = message;

            document.body.appendChild(announcement);

            // Remove after announcement
            setTimeout(() => {
                document.body.removeChild(announcement);
            }, 1000);
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text || '';
            return div.innerHTML;
        }

        // Mobile sidebar toggle
        function toggleSidebar() {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) {
                sidebar.classList.toggle('show');
                announceToScreenReader(sidebar.classList.contains('show') ? 'Sidebar opened' : 'Sidebar closed');
            }
        }

        // Make toggleSidebar available globally
        window.toggleSidebar = toggleSidebar;
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    main()