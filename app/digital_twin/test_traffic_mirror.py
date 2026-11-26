"""Offline tests for traffic_mirror: no Ryu or Mininet needed."""
from traffic_mirror import ingress_counters, RateMeter

H1, H2 = "00:00:00:00:00:01", "00:00:00:00:00:02"

topo = {"hosts": [
    {"mac": H2, "port": {"dpid": "0000000000000002", "port_no": "00000002"}},
    {"mac": H1, "port": {"dpid": "0000000000000001", "port_no": "00000001"}}]}


def flows(n):
    """h2 -> h1 traffic, seen on s2 (where it enters) and s1 (transit)."""
    def f(inp):
        return {"match": {"in_port": inp, "dl_src": H2, "dl_dst": H1}, "byte_count": n}
    table_miss = {"match": {}, "byte_count": 999}
    return {2: [f(2), table_miss], 1: [f(2)]}


pair = (H2, H1)

# counted once, at the ingress switch; table-miss flow ignored
assert ingress_counters(topo, flows(1000)) == {pair: 1000}

# 250 kB in 2 s = 1 Mbit/s
m = RateMeter()
assert m.update(ingress_counters(topo, flows(0)), now=0) == {}   # first poll: no rate yet
r = m.update(ingress_counters(topo, flows(250_000)), now=2)
assert r[pair] == 1_000_000, r

# counter reset (e.g. flow reinstalled) gives 0, not a negative rate
r = m.update(ingress_counters(topo, flows(10)), now=4)
assert r[pair] == 0, r

print("traffic tests passed")
