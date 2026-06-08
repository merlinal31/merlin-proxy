"""
Merlin Notes — Airtable Proxy
Déployé sur Railway. Cache le token Airtable côté serveur.
L'app web appelle ce proxy au lieu d'Airtable directement.

Variables d'environnement Railway à configurer :
  AIRTABLE_TOKEN   → token Airtable (pat...)
  AIRTABLE_BASE    → ID de la base (appFFP5S7VQMQyshH)
  PROXY_SECRET     → clé secrète choisie librement (ex: merlin2024xyz)
  ALLOWED_ORIGIN   → https://notes-taches.onrender.com
"""

import os
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# ── CONFIG ──────────────────────────────────────────
AIRTABLE_TOKEN  = os.environ.get('AIRTABLE_TOKEN', '')
AIRTABLE_BASE   = os.environ.get('AIRTABLE_BASE', '')
PROXY_SECRET    = os.environ.get('PROXY_SECRET', '')
ALLOWED_ORIGIN  = os.environ.get('ALLOWED_ORIGIN', 'https://notes-taches.onrender.com')

AIRTABLE_BASE_URL = f'https://api.airtable.com/v0/{AIRTABLE_BASE}'

# ── HELPERS ─────────────────────────────────────────
def airtable_headers():
    return {
        'Authorization': f'Bearer {AIRTABLE_TOKEN}',
        'Content-Type': 'application/json',
    }

def cors_headers():
    return {
        'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
        'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Proxy-Secret',
        'Access-Control-Max-Age': '86400',
    }

def check_secret():
    """Vérifie que la requête vient bien de l'app Merlin Notes."""
    if not PROXY_SECRET:
        return True  # pas de secret configuré → on laisse passer (dev)
    secret = request.headers.get('X-Proxy-Secret', '')
    return secret == PROXY_SECRET

def proxy_response(r):
    """Convertit une réponse requests en réponse Flask avec CORS."""
    resp = Response(r.content, status=r.status_code, content_type='application/json')
    for k, v in cors_headers().items():
        resp.headers[k] = v
    return resp

# ── PREFLIGHT OPTIONS ────────────────────────────────
@app.route('/api/<path:path>', methods=['OPTIONS'])
@app.route('/api/', methods=['OPTIONS'])
def options_handler(path=''):
    resp = Response('', status=204)
    for k, v in cors_headers().items():
        resp.headers[k] = v
    return resp

# ── HEALTH CHECK ─────────────────────────────────────
@app.route('/', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'Merlin Notes Proxy',
        'base': AIRTABLE_BASE[:8] + '...' if AIRTABLE_BASE else 'not set',
        'token': 'set' if AIRTABLE_TOKEN else 'NOT SET',
        'secret': 'set' if PROXY_SECRET else 'not set (open)',
    })

# ── LIST / SEARCH RECORDS ────────────────────────────
@app.route('/api/<table>', methods=['GET'])
def list_records(table):
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 401

    # Forward all query params to Airtable
    params = dict(request.args)
    url = f'{AIRTABLE_BASE_URL}/{table}'
    r = requests.get(url, headers=airtable_headers(), params=params, timeout=30)
    return proxy_response(r)

# ── GET SINGLE RECORD ────────────────────────────────
@app.route('/api/<table>/<record_id>', methods=['GET'])
def get_record(table, record_id):
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 401

    url = f'{AIRTABLE_BASE_URL}/{table}/{record_id}'
    r = requests.get(url, headers=airtable_headers(), timeout=15)
    return proxy_response(r)

# ── CREATE RECORDS ───────────────────────────────────
@app.route('/api/<table>', methods=['POST'])
def create_records(table):
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 401

    url = f'{AIRTABLE_BASE_URL}/{table}'
    r = requests.post(url, headers=airtable_headers(), json=request.get_json(), timeout=15)
    return proxy_response(r)

# ── UPDATE RECORDS (PATCH) ───────────────────────────
@app.route('/api/<table>', methods=['PATCH'])
def update_records(table):
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 401

    url = f'{AIRTABLE_BASE_URL}/{table}'
    r = requests.patch(url, headers=airtable_headers(), json=request.get_json(), timeout=15)
    return proxy_response(r)

# ── UPDATE SINGLE RECORD ─────────────────────────────
@app.route('/api/<table>/<record_id>', methods=['PATCH'])
def update_record(table, record_id):
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 401

    url = f'{AIRTABLE_BASE_URL}/{table}/{record_id}'
    r = requests.patch(url, headers=airtable_headers(), json=request.get_json(), timeout=15)
    return proxy_response(r)

# ── DELETE RECORD ────────────────────────────────────
@app.route('/api/<table>/<record_id>', methods=['DELETE'])
def delete_record(table, record_id):
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 401

    url = f'{AIRTABLE_BASE_URL}/{table}/{record_id}'
    r = requests.delete(url, headers=airtable_headers(), timeout=15)
    return proxy_response(r)

# ── MAIN ─────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
