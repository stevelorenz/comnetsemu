#!/usr/bin/python3

"""
About: Example of internal container migration

Topo:  h1     h2     h3
        |      |      |
       s1 -------------
"""


import argparse
import time

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet, VNFManager
from comnetsemu.node import DockerHost
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller, OVSBridge
from mininet.topo import Topo


class TestTopo(Topo):

    def build(self, n):
        switch = self.addSwitch('s1')
        for h in range(1, n+1):
            host = self.addHost('h%s' % h,
                                cls=DockerHost, dimage="dev_test",
                                ip="10.0.0.%s/24" % h, cpu_quota=int(50000/n))
            self.addLink(switch, host, bw=10, delay="100ms", use_htb=True)


def runIperfServer(h):
    ret = h.cmd("iperf -s -u -t 10 -i 1 -e")
    print("*** Output of Iperf server running on the {}".format(h.name))
    print(ret)


def runContainerMigration():

    net = Containernet(controller=Controller, link=TCLink, switch=OVSBridge,
                       topo=TestTopo(3))

    mgr = VNFManager(net)

    info('*** Adding controller\n')
    net.addController('c0')

    info('*** Starting network\n')
    net.start()
    h1 = net.get("h1")
    h2 = net.get("h2")
    h3 = net.get("h3")

    print("*** Deploy the Iperf client container on h2.")
    iperf_client = mgr.addContainer(
        "iperf_client", "h2", "dev_test", "iperf -c 10.0.0.1 -t 36000 -u")
    runIperfServer(h1)

    print("*** Migrate the Iperf client container from h2 to h3.")
    iperf_client_migrated = mgr.migrateCRIU(h2, iperf_client, h3)
    runIperfServer(h1)

    info('*** Stopping network\n')
    mgr.removeContainer(iperf_client)
    mgr.removeContainer(iperf_client_migrated)
    net.stop()
    mgr.stop()


if __name__ == '__main__':
    setLogLevel('info')
    runContainerMigration()
