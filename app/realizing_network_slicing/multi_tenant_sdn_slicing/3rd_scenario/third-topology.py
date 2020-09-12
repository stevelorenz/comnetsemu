#!/usr/bin/python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink


class FVTopo(Topo):
    def __init__(self):
        # Initialize topology
        Topo.__init__(self)

        # Create template host, switch, and link
        hconfig = {"inNamespace": True}
        http_link_config = {"bw": 1}
        voip_link_config = {"bw": 5}
        video_link_config = {"bw": 10}
        host_link_config = {}

        # Create switch nodes
        for i in range(5):
            sconfig = {"dpid": "%016x" % (i + 1)}
            self.addSwitch("s%d" % (i + 1), protocols="OpenFlow10", **sconfig)

        # Create host nodes
        # for i in range(2):
        self.addHost("h1", ip="10.0.0.1", **hconfig)
        self.addHost("h2", ip="10.0.0.2", **hconfig)
        self.addHost("h3", ip="10.0.0.3", **hconfig)
        self.addHost("h4", ip="10.0.0.4", **hconfig)

        # Add switch links
        self.addLink("s1", "s2", **video_link_config)
        self.addLink("s1", "s3", **voip_link_config)
        self.addLink("s1", "s4", **http_link_config)
        self.addLink("s2", "s5", **video_link_config)
        self.addLink("s3", "s5", **voip_link_config)
        self.addLink("s4", "s5", **http_link_config)

        # Add host links
        self.addLink("h1", "s1", **host_link_config)
        self.addLink("h2", "s1", **host_link_config)
        self.addLink("h3", "s5", **host_link_config)
        self.addLink("h4", "s5", **host_link_config)


topos = {"fvtopo": (lambda: FVTopo())}
if __name__ == "__main__":
    topo = FVTopo()
    net = Mininet(
        topo=topo,
        switch=OVSKernelSwitch,
        build=False,
        autoSetMacs=True,
        autoStaticArp=True,
        link=TCLink,
    )
    controller = RemoteController("c1", ip="127.0.0.1", port=6633)
    net.addController(controller)
    net.build()
    net.start()
    CLI(net)
    net.stop()
