#!/usr/bin/env python3
"""
Flask API server per l'interfaccia cittadino del DKG
Integrato con lo stack esistente: Flask + RDFLib + D3.js
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any

from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from rdflib import Graph
import pandas as pd

from retrieval_system import HybridRetrievalSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inizializza Flask app
app = Flask(__name__)
CORS(app)

# Variabile globale per il sistema di retrieval
retrieval_system = None


def init_retrieval_system(kg_path: str):
    """Inizializza il sistema di retrieval"""
    global retrieval_system
    logger.info(f"Inizializzazione sistema di retrieval con KG: {kg_path}")
    retrieval_system = HybridRetrievalSystem(kg_path)
    logger.info("Sistema di retrieval pronto!")


@app.route('/')
def index():
    """Pagina principale interfaccia cittadino"""
    try:
        with open('../frontend/citizen.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return jsonify({'error': 'File citizen.html non trovato'}), 404


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'retrieval_system_ready': retrieval_system is not None,
        'processes_count': len(retrieval_system.processes) if retrieval_system else 0
    })


@app.route('/api/search', methods=['POST'])
def search():
    """Endpoint di ricerca ibrida"""
    if not retrieval_system:
        return jsonify({'error': 'Sistema di retrieval non inizializzato'}), 500

    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query mancante'}), 400

        query = data['query']
        top_k = data.get('top_k', 10)

        results = retrieval_system.search(query=query, top_k=top_k)

        return jsonify({
            'results': results,
            'query': query,
            'total_results': len(results)
        })

    except Exception as e:
        logger.error(f"Errore nella ricerca: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/process/<path:uri>', methods=['GET'])
def get_process(uri: str):
    """Ottieni dettagli completi di un processo deliberativo"""
    if not retrieval_system:
        return jsonify({'error': 'Sistema non inizializzato'}), 500

    try:
        if not uri.startswith('http'):
            uri = f"https://svagnoni.linkeddata.es/resource/process/{uri}"

        process = retrieval_system.get_process_by_uri(uri)
        if not process:
            return jsonify({'error': 'Processo non trovato'}), 404

        return jsonify(process)

    except Exception as e:
        logger.error(f"Errore: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<format>', methods=['POST'])
def download_data(format: str):
    """Download dati in vari formati (RDF, JSON, CSV)"""
    if not retrieval_system:
        return jsonify({'error': 'Sistema non inizializzato'}), 500

    try:
        data = request.get_json() or {}
        full_dump = data.get('full_dump', False)

        if format in ['rdf', 'ttl']:
            output_path = Path('/tmp/dkg_export.ttl')
            retrieval_system.graph.serialize(destination=str(output_path), format='turtle')
            return send_file(output_path, as_attachment=True, download_name='dkg_export.ttl')

        elif format == 'jsonld':
            output_path = Path('/tmp/dkg_export.jsonld')
            retrieval_system.graph.serialize(destination=str(output_path), format='json-ld')
            return send_file(output_path, as_attachment=True, download_name='dkg_export.jsonld')

        elif format == 'json':
            return jsonify({
                'processes': retrieval_system.processes,
                'total': len(retrieval_system.processes)
            })

        elif format == 'csv':
            df = pd.DataFrame([{
                'uri': p['uri'],
                'title': p.get('title', ''),
                'description': p.get('description', ''),
                'platform': p.get('platform', ''),
                'contributions': p.get('contributions_count', 0),
                'fallacies': p.get('fallacies_count', 0)
            } for p in retrieval_system.processes])

            output_path = Path('/tmp/dkg_export.csv')
            df.to_csv(output_path, index=False)
            return send_file(output_path, as_attachment=True, download_name='dkg_export.csv')

        else:
            return jsonify({'error': f'Formato {format} non supportato'}), 400

    except Exception as e:
        logger.error(f"Errore download: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Statistiche generali del knowledge graph"""
    if not retrieval_system:
        return jsonify({'error': 'Sistema non inizializzato'}), 500

    try:
        processes = retrieval_system.processes
        return jsonify({
            'total_processes': len(processes),
            'total_contributions': sum(p.get('contributions_count', 0) for p in processes),
            'total_fallacies': sum(p.get('fallacies_count', 0) for p in processes),
            'platforms': list(set(p.get('platform', 'Unknown') for p in processes))
        })

    except Exception as e:
        logger.error(f"Errore statistiche: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='DKG Citizen Interface API')
    parser.add_argument('--kg-path', required=True, help='Path al knowledge graph (TTL)')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', default=5001, type=int)

    args = parser.parse_args()

    init_retrieval_system(args.kg_path)

    logger.info(f"Server avviato su {args.host}:{args.port}")
    app.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
