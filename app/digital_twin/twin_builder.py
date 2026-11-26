from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from validate import validate, normalize
import time

from ryu_client import fetchTopology
from traffic_mirror import read_flows, ingress_counters, RateMeter, TrafficMirror, print_rates

PHYS = "http://127.0.0.1:8080"
TWIN = "http://127.0.0.1:8081"

PREFIX = 8   # JSON-en har ingen nettmaske, Mininet bruker /8 som standard



#leser inn json-fila

#teller antall rutere/hosts i nettverket 
def findNumberOfHosts(topology):
    return len(topology['hosts'])

#henter switchen med riktig dpid, eller lager den hvis den ikke finnes ennå
def getSwitch(net, dpid):
    name = "ts%d" % int(dpid, 16)
    return net.get(name)


#her lages hver host/ruter med copiverdier
def createHost(net, hosts, number):
    h = hosts[number]
    port = h["port"]

    ip = h["ipv4"][0] if h["ipv4"] else None
    name = "th" + str(number + 1)
    host = net.addHost(name, mac=h["mac"], **({"ip": f"{ip}/{PREFIX}"} if ip else {}))

    switch = getSwitch(net, port["dpid"])
    net.addLink(host, switch,
                port2=int(port["port_no"], 16),   # hex-streng: "00000001" -> 1
                addr2=port["hw_addr"])            # MAC på switch-porten
    return host



def newNet(topology):
    net = Mininet( controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)
    try:
        buildNet(net, topology)
    except BaseException:
        net.stop()          # fjern det som rakk aa bli laget, ellers blokkerer det neste bygg
        raise
    return net


def buildNet(net, topology):
    info( '*** Adding controller\n' )
    net.addController( 'tc0', ip='127.0.0.1', port=6654 )

    info('*** Adding switches\n')
    switch_by_dpid = {}
    switches = topology['switches']
    for switch in switches:
        dpid = int(switch['dpid'],16)
        twin = net.addSwitch(f'ts{dpid}', dpid=switch['dpid'], protocols='OpenFlow13')
        switch_by_dpid[dpid] = twin


    info( '*** Adding hosts\n' )
    hosts = topology['hosts']
    for i in range(findNumberOfHosts(topology)):
        createHost(net, hosts, i)

    info('*** Adding links')
    seen_switch_links = set()
    for link in topology['links']:
        src = link["src"]
        dst = link["dst"]

        src_dpid = int(src["dpid"], 16)
        dst_dpid = int(dst["dpid"], 16)
        link_key = frozenset([(src_dpid, int(src["port_no"], 16)), (dst_dpid, int(dst["port_no"], 16))])
        if link_key in seen_switch_links:
            continue
        seen_switch_links.add(link_key)

        net.addLink(
            net.get("ts%d" % src_dpid),
            net.get("ts%d" % dst_dpid),
            port1=int(src["port_no"], 16),
            port2=int(dst["port_no"], 16),
        )

    info( '*** Starting network\n' )
    net.start()
    net.pingAll()


def main():
    topology = fetchTopology()
    current = normalize(topology)
    network = newNet(topology)
    validate()
    mirror, phys_meter, twin_meter = TrafficMirror(network), RateMeter(), RateMeter()
    try:
        while True:
            time.sleep(2)                          # 5 s is too slow for traffic
            topology = fetchTopology()
            new = normalize(topology)
            if new != current:
                info('*** Physical network changed!\n')
                network.stop()                     # also kills the twin's iperfs
                network = None                     # so finally doesn't stop it twice
                network = newNet(topology)
                current = new
                validate()
                mirror, twin_meter = TrafficMirror(network), RateMeter()

            phys_rates = phys_meter.update(ingress_counters(topology, read_flows(topology, PHYS)))
            mirror.apply(phys_rates)
            twin_topo = fetchTopology(TWIN)
            twin_rates = twin_meter.update(ingress_counters(twin_topo, read_flows(twin_topo, TWIN)))
            print_rates(phys_rates, twin_rates)
    finally:
        if network is not None:
            network.stop()
        
if __name__ == '__main__':
    setLogLevel('info')
    main()