#!/usr/bin/python3

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
import subprocess


class NetworkSlicingTopo(Topo):
    def __init__(self):
        # Initialize topology
        Topo.__init__(self)

        # Create template host, switch, and link
        host_config = dict(inNamespace=True)
        link_config = dict()  # Total Capacity of the link ~ 10Mbps
        host_link_config = dict()

        # Create router nodes ~ 2 router nodes in our case
        for i in range(2):
            sconfig = {"dpid": "%016x" % (i + 1)}
            self.addSwitch("r%d" % (i + 1), **sconfig)

        # Create host nodes ~ 3 clients + 3 servers = 6 Host Nodes
        for i in range(6):
            self.addHost("h%d" % (i + 1), **host_config) # We choose 'h' because 'c' is the controller
            
 



        # Add router link
        self.addLink("r1", "r2", **link_config)

        # Add clients-router1 and clients-router2 links
        self.addLink("h1", "r1", **host_link_config)
        self.addLink("h2", "r1", **host_link_config)
        self.addLink("h3", "r1", **host_link_config)
        self.addLink("h4", "r2", **host_link_config)
        self.addLink("h5", "r2", **host_link_config)
        self.addLink("h6", "r2", **host_link_config)




topos = {"networkslicingtopo": (lambda: NetworkSlicingTopo())}

if __name__ == "__main__":
    topo = NetworkSlicingTopo()
    net = Mininet(
        topo=topo,
        
        # We specify an external controller by passing the Controller object in the Mininet constructor
        # This was added in Mininet 2.2.0 and above.
        # SOS Note: Do not specify port -- Default: 6653
        controller=RemoteController( 'c0', ip='127.0.0.1'), 
        switch=OVSKernelSwitch,
        build=False,
        autoSetMacs=True,
        autoStaticArp=True,
        link=TCLink,
    )
    
    # ------------ Check Constructor for Controller ----------------- #
    #controller = RemoteController("c1", ip="127.0.0.1", port=6633)
    #net.addController(controller)
    
    net.build()
    net.start()
    
    # Here we automate the process of creating the 2 slices by calling as a subprocess the common_scenario.sh
    # Assumption: We begin with a non-emergency scenario.
    subprocess.call("./common_scenario.sh")
    
    CLI(net)
    net.stop()
