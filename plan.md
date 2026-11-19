# Plan: Digital Twin for SDN Networks in ComNetsEmu

**Task (from the project list):** build a script that generates the Digital Twin of
an SDN network, using the Ryu northbound REST API to retrieve topology and traffic
information. The procedure must be fully automated, and changes to the Physical
Twin at runtime must be reproduced automatically in the Digital Twin.

---

## 1. Architecture

Two separate Mininet networks run in the same ComNetsEmu VM, each with its own Ryu
controller. A Python "twin builder" polls the physical network's Ryu REST API and
builds and updates the twin to match.

```
 Physical Twin                         Digital Twin
 Mininet (s1, h1…)                     Mininet (ts1, th1…)
      │ OpenFlow :6633                      │ OpenFlow :6654
 Ryu #1  REST :8080  ──poll──▶  twin_builder.py  ──▶ Ryu #2  REST :8081
                                (diff + apply)
```

### Controllers

Physical (Ryu #1):

```bash
ryu-manager --observe-links \
  ryu.app.simple_switch_13 ryu.app.rest_topology ryu.app.ofctl_rest
```

Twin (Ryu #2), on different OpenFlow and REST ports:

```bash
ryu-manager --observe-links --ofp-tcp-listen-port 6654 --wsapi-port 8081 \
  ryu.app.simple_switch_13 ryu.app.rest_topology ryu.app.ofctl_rest
```

If the topology has loops, use `ryu.app.simple_switch_stp_13` in both controllers
instead of `simple_switch_13`.

### Naming and identity rules

- **Prefix the twin's node names** (`ts1`, `th1`). Switch interfaces live in the
  VM's shared root namespace, so they cannot share names with the physical
  network's. Linux limits interface names to 15 characters, so keep the prefix
  short.
- **Hosts can reuse the same IPs and MACs**, because each Mininet host has its own
  network namespace.
- **Copy the switch DPIDs and port numbers exactly.** `addSwitch(..., dpid=...)` and
  `addLink(..., port1=, port2=)` let you set both. Then flow and port stats from the
  physical network line up one-to-one with the twin.
- **Be careful with `sudo mn -c`:** it cleans up *both* networks.

---

## 2. What the Ryu REST API provides

| Need | Endpoint |
|---|---|
| Switches | `GET /v1.0/topology/switches` |
| Links (src/dst dpid + port) | `GET /v1.0/topology/links` |
| Hosts (MAC, IP, attachment point) | `GET /v1.0/topology/hosts` |
| Port state (up/down, port exists) | `GET /stats/portdesc/<dpid>` |
| Traffic per port (bytes/packets) | `GET /stats/port/<dpid>` |
| Traffic per src→dst pair | `GET /stats/flow/<dpid>` (simple_switch_13 installs flows matching `in_port`, `eth_src`, `eth_dst`) |

### Limitations to plan for

- **Ryu only learns about a host once the host sends traffic.** Run a `pingall` (or
  one ARP per host) at startup.
- **OpenFlow does not expose link bandwidth or delay.** Either measure them (ping
  RTT, an iperf probe) or read them from a config file. State which one you chose in
  the presentation.

---

## 3. The twin builder (core of the project)

1. **Snapshot:** poll every 1–2 s and normalize into one model:
   - `switches{dpid}`
   - `links{(dpid, port) ↔ (dpid, port)}`
   - `hosts{mac: ip, dpid, port}`
   - traffic rates computed from byte-counter differences between polls
2. **Initial build:** create the twin Mininet from the first snapshot and start it.
   A loop-free topology is simplest to begin with.
3. **Diff loop:** compare the new snapshot with the twin's current model and apply
   only the changes:
   - **New switch:** `net.addSwitch(...)`, then `.start([controller])`.
   - **New link:** `net.addLink(a, b, port1=, port2=)`, then
     `a.attach(link.intf1)` and `b.attach(link.intf2)` on the switches.
   - **New host:** `addHost`, `addLink`, then `host.setIP()` and `setMAC()`.
   - **Missing link:** check portdesc to tell the two cases apart:
     - ports still exist and are LINK_DOWN → `net.configLinkStatus(a, b, 'down')`
       (this is what happens after `link s1 s2 down` on the physical network);
     - ports are gone → `net.delLinkBetween(a, b)`.
   - **Fallback:** for any change that is hard to apply in place, tear the twin down
     and rebuild it from the snapshot. Slower, but always correct.
4. **Traffic mirroring:** turn the flow stats into a matrix of rates from each source
   host to each destination host. Replay it in the twin with UDP iperf at those
   rates, and update it whenever the measured rates change.
5. **Validation:** fetch the twin's own REST API (`:8081`) and diff it against the
   physical one automatically. Print "IN SYNC" or the list of mismatches.

---

## 4. Suggested file layout

```
app/digital_twin/
  physical_net.py      # physical topology + CLI
  change_scenario.py   # scripted changes: link down at 20 s, add a host at 40 s, start traffic…
  twin_builder.py      # snapshot → build → diff → apply loop
  ryu_client.py        # thin REST wrapper
  traffic_mirror.py    # rate computation + iperf replay
  validate.py          # physical vs. twin diff
  viz.py (optional)    # networkx/matplotlib view of both side by side
```

---

## 5. Demo flow

1. Start the physical network and run `twin_builder.py`. The twin appears
   automatically and `validate.py` reports it in sync.
2. Run `change_scenario.py`: a link goes down, a host is added, then traffic starts.
   Each change shows up in the twin within a few seconds, and validation stays in
   sync.
3. Show twin-side measurements (traffic rates, ping on the mirrored paths) next to
   the physical ones.

---

## 6. Splitting the work (up to 3 people)

1. The physical network and the change scenarios.
2. The twin builder: build and diff/apply.
3. Traffic mirroring, validation and the visualization.

---

## 7. Suggested order of work

1. [ ] Start Ryu #1 with the REST apps and a small physical topology; query every
       endpoint with `curl` and save example responses
2. [ ] `ryu_client.py` + snapshot model
3. [ ] Initial twin build from one snapshot (with prefixes, same DPIDs and ports)
4. [ ] `validate.py` (physical vs. twin diff)
5. [ ] Rebuild-on-change fallback
6. [ ] In-place changes, one type at a time: link down/up → new host → new link →
       new switch
7. [ ] Traffic mirroring
8. [ ] `change_scenario.py` + demo rehearsal
9. [ ] Optional: visualization
10. [ ] Slides: architecture, sync algorithm, limitations (bandwidth/delay, host
        discovery), results

The tricky part is the dynamic link and switch changes in Mininet, so get the
rebuild fallback working first.
