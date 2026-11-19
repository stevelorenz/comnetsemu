import json
import os
import sys

import requests

BASE = 'http://127.0.0.1:8080'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ryu_output')


def get(path):
    url = BASE + path
    try:
        r = requests.get(url, timeout=5)
    except requests.exceptions.ConnectionError:
        sys.exit(f'Could not connect to {BASE}. Is ryu-manager running with --wsapi-port matching?')
    if r.status_code == 404:
        sys.exit(f'{url} returned 404. Start ryu-manager with ryu.app.rest_topology and ryu.app.ofctl_rest.')
    r.raise_for_status()
    return r.json()


def save(name, data):
    with open(os.path.join(OUT_DIR, name), 'w') as f:
        json.dump(data, f, indent=4)


if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)

    switches = get('/v1.0/topology/switches')
    links = get('/v1.0/topology/links')
    hosts = get('/v1.0/topology/hosts')

    save('switches.json', switches)
    save('links.json', links)
    save('hosts.json', hosts)

    for sw in switches:
        dpid = int(sw['dpid'], 16)
        save(f'flow_s{dpid}.json', get(f'/stats/flow/{dpid}'))

    print(f'{len(switches)} switches, {len(links)} links, {len(hosts)} hosts -> {OUT_DIR}')
