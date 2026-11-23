import json
from pathlib import Path
from urllib.request import urlopen

BASE_DIR = Path(__file__).resolve().parent
SWITCHFIL = BASE_DIR / "ryu_output" / "switches.json"
HOSTFIL = BASE_DIR / "ryu_output" / "hosts.json"
LINK = BASE_DIR / "ryu_output" / "links.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def fetchTopology(base_url):
    """Hent switches, links og hosts fra en Ryu REST API-tjeneste."""
    base_url = base_url.rstrip("/")

    def get(path):
        with urlopen(base_url + path, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    return {
        "switches": get("/v1.0/topology/switches"),
        "links": get("/v1.0/topology/links"),
        "hosts": get("/v1.0/topology/hosts"),
    }

def normalize(topology=None):
    """Konverter Ryu-topologien til en stabil, sammenlignbar representasjon."""
    if topology is None:
        topology = {
            "switches": load_json(SWITCHFIL) if SWITCHFIL.exists() else [],
            "hosts": load_json(HOSTFIL),
            "links": load_json(LINK),
        }

    def normalize_dpid(dpid):
        if dpid is None:
            return None
        return str(int(dpid, 16) if isinstance(dpid, str) else dpid)

    def normalize_port(port):
        if port is None:
            return None
        if isinstance(port, str):
            return str(int(port, 16))
        return str(port)

    switches = sorted(
        {normalize_dpid(switch["dpid"]) for switch in topology.get("switches", [])}
    )

    hosts = []
    seen_hosts = set()
    for host in topology.get("hosts", []):
        port = host.get("port") or {}
        ipv4 = sorted(host.get("ipv4", []))
        mac = (host.get("mac") or "").lower()
        dpid = normalize_dpid(port.get("dpid"))
        port_no = normalize_port(port.get("port_no"))
        host_key = (mac, tuple(ipv4), dpid, port_no)
        if host_key not in seen_hosts:
            seen_hosts.add(host_key)
            hosts.append({
                "mac": mac,
                "ipv4": ipv4,
                "dpid": dpid,
                "port": port_no,
            })
    hosts.sort(key=lambda host: (
        tuple(host["ipv4"]),
        host["mac"],
        host["dpid"] or "",
        host["port"] or "",
    ))

    links = set()
    for link in topology.get("links", []):
        src = link.get("src") or {}
        dst = link.get("dst") or {}
        src_endpoint = (
            normalize_dpid(src.get("dpid")),
            normalize_port(src.get("port_no")),
        )
        dst_endpoint = (
            normalize_dpid(dst.get("dpid")),
            normalize_port(dst.get("port_no")),
        )
        if None not in src_endpoint and None not in dst_endpoint:
            links.add(tuple(sorted((src_endpoint, dst_endpoint))))

    normalized_links = [
        {
            "src": {"dpid": src[0], "port": src[1]},
            "dst": {"dpid": dst[0], "port": dst[1]},
        }
        for src, dst in sorted(links)
    ]

    return {
        "switches": switches,
        "hosts": hosts,
        "links": normalized_links,
    }

def diff(phys, twin):
    """Sammenlign fysisk og digital topologi og returner avvik."""
    missmatches = []

    physical_switches = set(phys.get("switches", []))
    twin_switches = set(twin.get("switches", []))
    for dpid in sorted(physical_switches - twin_switches):
        missmatches.append({
            "type": "missing_switch",
            "location": "twin",
            "dpid": dpid,
        })
    for dpid in sorted(twin_switches - physical_switches):
        missmatches.append({
            "type": "extra_switch",
            "location": "twin",
            "dpid": dpid,
        })

    def host_key(host):
        return (
            host["mac"],
            tuple(host.get("ipv4", [])),
            host.get("dpid"),
            host.get("port"),
        )

    physical_hosts = {host_key(host): host for host in phys.get("hosts", [])}
    twin_hosts = {host_key(host): host for host in twin.get("hosts", [])}
    for key in sorted(set(physical_hosts) - set(twin_hosts)):
        missmatches.append({
            "type": "missing_host",
            "location": "twin",
            "host": physical_hosts[key],
        })
    for key in sorted(set(twin_hosts) - set(physical_hosts)):
        missmatches.append({
            "type": "extra_host",
            "location": "twin",
            "host": twin_hosts[key],
        })

    def link_key(link):
        src = link["src"]
        dst = link["dst"]
        return tuple(sorted((
            (src["dpid"], src["port"]),
            (dst["dpid"], dst["port"]),
        )))

    physical_links = {link_key(link): link for link in phys.get("links", [])}
    twin_links = {link_key(link): link for link in twin.get("links", [])}
    for key in sorted(set(physical_links) - set(twin_links)):
        missmatches.append({
            "type": "missing_link",
            "location": "twin",
            "link": physical_links[key],
        })
    for key in sorted(set(twin_links) - set(physical_links)):
        missmatches.append({
            "type": "extra_link",
            "location": "twin",
            "link": twin_links[key],
        })

    return missmatches

#ferdig! returnerer True hvis det ikke er noe galt
def report(missmatches):
    if missmatches:
        print("Topology mismatch:")
        for mismatch in missmatches:
            print("- %s: %s" % (
                mismatch["type"],
                mismatch.get("dpid")
                or mismatch.get("host")
                or mismatch.get("link"),
            ))
    return len(missmatches) == 0


def validate(
    physical_url="http://127.0.0.1:8080",
    twin_url="http://127.0.0.1:8081",
):
    physical = normalize(fetchTopology(physical_url))
    twin = normalize(fetchTopology(twin_url))
    missmatches = diff(physical, twin)
    return report(missmatches)


def main():
    return 0 if validate() else 1


if __name__ == "__main__":
    raise SystemExit(main())