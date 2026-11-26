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

OFPPC_PORT_DOWN = 1    # port config-bit: porten er administrativt nede
OFPPS_LINK_DOWN = 1    # port state-bit: ingen link


def downPorts(switches, base=BASE):
    """{(dpid, port_no)} (som int) for porter som er nede eller mangler link."""
    down = set()
    for sw in switches:
        dpid = int(sw['dpid'], 16)
        for p in get(f'/stats/portdesc/{dpid}', base).get(str(dpid), []):
            if not isinstance(p.get('port_no'), int):
                continue                      # "LOCAL" o.l.
            if p.get('config', 0) & OFPPC_PORT_DOWN or p.get('state', 0) & OFPPS_LINK_DOWN:
                down.add((dpid, p['port_no']))
    return down


def fetchTopology(base=BASE):
    """Hent topologien fra Ryu-kontrolleren paa base, f.eks.
    'http://127.0.0.1:8080' (fysisk) eller 'http://127.0.0.1:8081' (twin).

    Returnerer {'switches': [...], 'links': [...], 'hosts': [...]} fra REST-API-et,
    men uten hosts som henger paa en port som er fjernet eller nede.
    """
    switches = get('/v1.0/topology/switches', base)
    links = get('/v1.0/topology/links', base)
    hosts = get('/v1.0/topology/hosts', base)

    # Ryu glemmer aldri hosts: fjern de som henger paa en port som ikke finnes
    # lenger (switch slettet, nett startet paa nytt) eller som er nede (link h1 s1 down)
    live_ports = {(p['dpid'], p['port_no']) for sw in switches for p in sw['ports']}
    down = downPorts(switches, base)
    hosts = [h for h in hosts
             if (h['port']['dpid'], h['port']['port_no']) in live_ports
             and (int(h['port']['dpid'], 16), int(h['port']['port_no'], 16)) not in down]

    return {'switches': switches, 'links': links, 'hosts': hosts}