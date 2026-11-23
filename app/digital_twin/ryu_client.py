import json
import os
import sys

import requests

BASE = 'http://127.0.0.1:8080'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ryu_output')


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


def save(name, data):
    with open(os.path.join(OUT_DIR, name), 'w') as f:
        json.dump(data, f, indent=4)


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


if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)

    topo = fetchTopology()
    switches, links, hosts = topo['switches'], topo['links'], topo['hosts']

    save('switches.json', switches)
    save('links.json', links)
    save('hosts.json', hosts)

    for sw in switches:
        dpid = int(sw['dpid'], 16)
        save(f'flow_s{dpid}.json', get(f'/stats/flow/{dpid}'))

    print(f'{len(switches)} switches, {len(links)} links, {len(hosts)} hosts -> {OUT_DIR}')
