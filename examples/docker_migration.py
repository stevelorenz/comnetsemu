#!/usr/bin/python3

"""
About: Example of internal Docker container stateful migration with CRIU (https://criu.org/Main_Page)

Topo:  h1     h2     h3
        |      |      |
       s1 -------------
"""


import time

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

    print("*** Deploy a looper container on h1")
    looper = mgr.addContainer(
        "looper", "h1", "dev_test", "/bin/sh -c 'i=0; while true; do echo $i; i=$(expr $i + 1); sleep 1; done'")
    time.sleep(5)
    print("*** Logs of the original looper \n" + looper.get_logs())

    print("*** Migrate the looper from h1 to h2.")
    looper_h2 = mgr.migrateCRIU(h1, looper, h2)
    time.sleep(5)
    print(looper_h2.get_logs())

    print("*** Migrate the looper from h2 to h3.")
    looper_h3 = mgr.migrateCRIU(h2, looper_h2, h3)
    time.sleep(5)
    print(looper_h3.get_logs())

    info('*** Stopping network\n')
    mgr.removeContainer(looper)
    mgr.removeContainer(looper_h2)
    mgr.removeContainer(looper_h3)
    net.stop()
    mgr.stop()


if __name__ == '__main__':
    setLogLevel('info')
    runContainerMigration()
