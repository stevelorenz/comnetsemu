"""Measure host-to-host traffic in the physical network and replay it in the twin.

Rates come from Ryu flow stats (simple_switch_13 installs one flow per
in_port/src MAC/dst MAC). Each flow is counted only on the switch port where
the source host is attached, so traffic is not counted once per hop.
"""
import time

from ryu_client import get

THRESHOLD_BPS = 50_000       # ignore ARP/IPv6/ping noise
CHANGE = 0.2                 # restart a stream if its rate changes by more than 20%
PAYLOAD_RATIO = 1470 / 1512  # iperf -b is UDP payload, flow counters include headers


def read_flows(topology, base):
    """{dpid: [flow, ...]} from /stats/flow for every switch."""
    flows = {}
    for sw in topology['switches']:
        dpid = int(sw['dpid'], 16)
        flows[dpid] = get(f'/stats/flow/{dpid}', base).get(str(dpid), [])
    return flows


def ingress_counters(topology, flows):
    """{(src_mac, dst_mac): bytes}, counted only where the source host is attached."""
    edge = {(int(h['port']['dpid'], 16), int(h['port']['port_no'], 16)): h['mac']
            for h in topology['hosts']}
    counters = {}
    for dpid, entries in flows.items():
        for f in entries:
            m = f.get('match', {})
            src = m.get('dl_src') or m.get('eth_src')
            dst = m.get('dl_dst') or m.get('eth_dst')
            if not src or not dst or 'in_port' not in m:
                continue                      # table-miss / LLDP flows
            if edge.get((dpid, int(m['in_port']))) != src:
                continue                      # not where this traffic enters
            counters[(src, dst)] = counters.get((src, dst), 0) + f['byte_count']
    return counters


class RateMeter:
    """Turns byte counters into bit/s between two successive calls."""

    def __init__(self):
        self.last, self.last_t = {}, None

    def update(self, counters, now=None):
        now = time.monotonic() if now is None else now
        rates = {}
        if self.last_t is not None and now > self.last_t:
            dt = now - self.last_t
            for pair, b in counters.items():
                delta = b - self.last.get(pair, b)        # new flow: 0 for now
                rates[pair] = max(delta, 0) * 8 / dt      # counter reset: 0
        self.last, self.last_t = counters, now
        return rates


class TrafficMirror:
    """Keeps one UDP iperf stream per active (src, dst) pair in the twin."""

    def __init__(self, net):
        self.by_mac = {h.MAC(): h for h in net.hosts}
        self.servers = set()
        self.streams = {}                     # (src, dst) -> (pid, rate)

    def apply(self, rates):
        wanted = {p: r for p, r in rates.items()
                  if r >= THRESHOLD_BPS and p[0] in self.by_mac and p[1] in self.by_mac
                  and self.by_mac[p[1]].IP()}

        # stop streams that ended or changed too much
        for pair, (pid, cur) in list(self.streams.items()):
            new = wanted.get(pair)
            if new is None or abs(new - cur) > CHANGE * cur:
                self.by_mac[pair[0]].cmd(f'kill {pid}')
                del self.streams[pair]

        # start missing streams
        for pair, rate in wanted.items():
            if pair in self.streams:
                continue
            src, dst = self.by_mac[pair[0]], self.by_mac[pair[1]]
            if dst.name not in self.servers:
                dst.cmd('iperf -s -u > /dev/null 2>&1 &')
                self.servers.add(dst.name)
            out = src.cmd(f'iperf -c {dst.IP()} -u -b {int(rate * PAYLOAD_RATIO)} -t 86400 '
                          f'> /dev/null 2>&1 & echo $!').split()
            if out:
                self.streams[pair] = (out[-1], rate)


def print_rates(phys, twin):
    for pair in sorted(set(phys) | set(twin)):
        p, t = phys.get(pair, 0), twin.get(pair, 0)
        if max(p, t) >= THRESHOLD_BPS:
            print(f'  {pair[0]} -> {pair[1]}: physical {p / 1e6:6.2f} Mbit/s'
                  f'   twin {t / 1e6:6.2f} Mbit/s')
