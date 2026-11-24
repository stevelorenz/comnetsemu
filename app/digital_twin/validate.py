import time
from ryu_client import fetchTopology

def normalize(topology):
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
    mismatches = []

    physical_switches = set(phys.get("switches", []))
    twin_switches = set(twin.get("switches", []))
    for dpid in sorted(physical_switches - twin_switches):
        mismatches.append({
            "type": "missing_switch",
            "location": "twin",
            "dpid": dpid,
        })
    for dpid in sorted(twin_switches - physical_switches):
        mismatches.append({
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
        mismatches.append({
            "type": "missing_host",
            "location": "twin",
            "host": physical_hosts[key],
        })
    for key in sorted(set(twin_hosts) - set(physical_hosts)):
        mismatches.append({
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

    phys_hosts = {h["mac"]: h for h in phys["hosts"]}
    twin_hosts = {h["mac"]: h for h in twin["hosts"]}
    for mac in sorted(phys_hosts.keys() - twin_hosts.keys()):
        mismatches.append({"type": "missing_host", "host": phys_hosts[mac]})
    for mac in sorted(twin_hosts.keys() - phys_hosts.keys()):
        mismatches.append({"type": "extra_host", "host": twin_hosts[mac]})
    for mac in sorted(phys_hosts.keys() & twin_hosts.keys()):
        for field in ("ipv4", "dpid", "port"):
            if phys_hosts[mac][field] != twin_hosts[mac][field]:
                mismatches.append({"type": "host_" + field, "mac": mac,
                                    "physical": phys_hosts[mac][field],
                                    "twin": twin_hosts[mac][field]})

    return mismatches

#ferdig! returnerer True hvis det ikke er noe galt
def report(mismatches):
    if mismatches:
        print("Topology mismatch:")
        for mismatch in mismatches:
            print("- %s: %s" % (
                mismatch["type"],
                mismatch.get("dpid")
                or mismatch.get("host")
                or mismatch.get("link"),
            ))
    if not mismatches:
        print("GREAT SUCCESS!")
    return len(mismatches) == 0


def validate(
    physical_url="http://127.0.0.1:8080",
    twin_url="http://127.0.0.1:8081",
    attempts=5,
    delay=1.0,
):
    for _ in range(attempts):
        m = diff(normalize(fetchTopology(physical_url)), normalize(fetchTopology(twin_url)))
        if not m:
            break
        time.sleep(delay)
    return report(m)


def main():
    return 0 if validate() else 1


if __name__ == "__main__":
    raise SystemExit(main())