import json
import os
import sys

import requests

BASE = 'http://127.0.0.1:8080'

def get(path, base=BASE):
    url = base + path
    try:
        r = requests.get(url, timeout=5)
    except requests.exceptions.ConnectionError:
        sys.exit(f'Could not connect to {base}. Is ryu-manager running with --wsapi-port matching?')
    if r.status_code == 404:
        sys.exit(f'{url} returned 404. Start ryu-manager with ryu.app.rest_topology and ryu.app.ofctl_rest.')
    r.raise_for_status()
    return r.json()

def fetchTopology(base=BASE):
    """Hent topologien fra Ryu-kontrolleren paa base, f.eks.
    'http://127.0.0.1:8080' (fysisk) eller 'http://127.0.0.1:8081' (twin).

    Returnerer raadataene fra REST-API-et uendret:
        {'switches': [...], 'links': [...], 'hosts': [...]}
    """
    return {
        'switches': get('/v1.0/topology/switches', base),
        'links': get('/v1.0/topology/links', base),
        'hosts': get('/v1.0/topology/hosts', base),
    }