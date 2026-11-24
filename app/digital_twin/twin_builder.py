from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

import json
import sys

HOSTFIL = "/home/vagrant/comnetsemu/app/digital_twin/ryu_output/hosts.json"
SWITCHFIL = "/home/vagrant/comnetsemu/app/digital_twin/ryu_output/switches.json"
LINK = "/home/vagrant/comnetsemu/app/digital_twin/ryu_output/links.json"
PREFIX = 8   # JSON-en har ingen nettmaske, Mininet bruker /8 som standard



#leser inn json-fila
def loadHosts(fil=HOSTFIL):
    with open(fil, "r") as file:
        return json.load(file)



#teller antall rutere/hosts i nettverket 
def findNumberOfHosts(fil=HOSTFIL):
    return len(loadHosts(fil))

def loadSwitches():
    with open(SWITCHFIL, "r") as f:
        switches = json.load(f)
        return switches

def loadLinks(fil=LINK):
    with open(fil, "r") as file:
        return json.load(file)

#henter switchen med riktig dpid, eller lager den hvis den ikke finnes ennå
def getSwitch(net, dpid):
    name = "ts%d" % int(dpid, 16)
    return net.get(name)


#her lages hver host/ruter med copiverdier
def createHost(net, hosts, number):
    h = hosts[number]
    port = h["port"]

    ip = h["ipv4"][0] if h["ipv4"][0] else None
    name = "th" + str(number + 1)
    host = net.addHost(name, mac=h["mac"], **({"ip": f"{ip}/{PREFIX}"} if ip else {}))

    switch = getSwitch(net, port["dpid"])
    net.addLink(host, switch,
                port2=int(port["port_no"], 16),   # hex-streng: "00000001" -> 1
                addr2=port["hw_addr"])            # MAC på switch-porten
    return host



def newNet():
    net = Mininet( controller=RemoteController, switch=OVSSwitch, autoSetMacs=True)

    info( '*** Adding controller\n' )
    net.addController( 'tc0', ip='127.0.0.1', port=6654 )

    info('*** Adding switches\n')
    switch_by_dpid = {}
    switches = loadSwitches()
    for switch in switches:
        dpid = int(switch['dpid'],16)
        twin = net.addSwitch(f'ts{dpid}', dpid=switch['dpid'], protocols='OpenFlow13')
        switch_by_dpid[dpid] = twin


    info( '*** Adding hosts\n' )
    hosts = loadHosts()
    for i in range(findNumberOfHosts()):
        createHost(net, hosts, i)

    info('*** Adding links')
    seen_switch_links = set()
    for link in loadLinks():
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
    CLI( net )
    net.stop()
    return


def main():
    return newNet()

if __name__ == '__main__':
    setLogLevel('info')
    main()