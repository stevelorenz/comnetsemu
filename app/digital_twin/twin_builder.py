from mininet.net import Mininet
from mininet.node import RemoteController
from nullswitch import NullSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

import json
import sys

HOSTFIL = "../ryu_output/hosts.json"
LINK = "../ryu_output/links.json"
PREFIX = 8   # JSON-en har ingen nettmaske, Mininet bruker /8 som standard



#leser inn json-fila
def loadHosts(fil=HOSTFIL):
    with open(fil, "r") as file:
        return json.load(file)



#teller antall rutere/hosts i nettverket 
def findNumberOfHosts(fil=HOSTFIL):
    return len(loadHosts(fil))



#henter switchen med riktig dpid, eller lager den hvis den ikke finnes ennå
def getSwitch(net, dpid):
    name = "s%d" % int(dpid, 16)          # "0000000000000003" -> "s3"
    if name not in net:
        net.addSwitch(name, dpid=dpid)
    return net.get(name)


#her lages hver host/ruter med copiverdier
def createHost(net, hosts, number):
    h = hosts[number]
    port = h["port"]

    ip = h["ipv4"][0]
    name = "h" + ip.split(".")[-1]        # 10.0.0.3 -> h3
    host = net.addHost(name, ip="%s/%d" % (ip, PREFIX), mac=h["mac"])

    switch = getSwitch(net, port["dpid"])
    net.addLink(host, switch,
                port2=int(port["port_no"], 16),   # hex-streng: "00000001" -> 1
                intfName2=port["name"],           # "s1-eth1"
                addr2=port["hw_addr"])            # MAC på switch-porten
    return host



def newNet():
    net = Mininet( controller=RemoteController, switch=NullSwitch )

    info( '*** Adding controller\n' )
    net.addController( 'c0' )

    info( '*** Adding hosts\n' )
    hosts = loadHosts()
    for i in range(findNumberOfHosts()):
        createHost(net, hosts, i)

    info( '*** Starting network\n' )
    net.start()
    CLI( net )
    net.stop()
    return


def main():
    return newNet()
