#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from comnetsemu.cli import CLI, spawnXtermDocker
from comnetsemu.net import Containernet, VNFManager
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

if __name__ == "__main__":

    setLogLevel("info")

    net = Containernet(controller=Controller, link=TCLink, xterms=False)
    mgr = VNFManager(net)

    info("*** Add controller\n")
    net.addController("c0")

    info("*** Creating hosts\n")
    h1 = net.addDockerHost(
        "mqttServer", dimage="dev_test", ip="10.0.0.1", docker_args={"hostname": "mqttServer"}
    )
    h2 = net.addDockerHost(
        "webServer", dimage="dev_test", ip="10.0.0.2", docker_args={"hostname": "webServer"},
    )
    h3 = net.addDockerHost(
        "drone", dimage="dev_test", ip="10.0.0.3", docker_args={"hostname": "drone"}
    )
    h4 = net.addDockerHost(
        "client", dimage="dev_test", ip="10.0.0.4", docker_args={"hostname": "client"}
    )

    info("*** Adding switch and links\n")
    switch1 = net.addSwitch("s1")
    switch2 = net.addSwitch("s2")
    switch3 = net.addSwitch("s3")
    switch4 = net.addSwitch("s4")
    net.addLink(switch1, h1, bw=10, delay="10ms")
    net.addLink(switch1, switch2, bw=10, delay="10ms")
    net.addLink(switch1, switch3, bw=10, delay="10ms")
    net.addLink(switch1, switch4, bw=10, delay="10ms")
    net.addLink(switch2, h2, bw=10, delay="10ms")
    # net.addLink(switch2, switch3, bw=10, delay="10ms")
    net.addLink(switch3, h3, bw=10, delay="10ms")
    net.addLink(switch4, h4, bw=10, delay="10ms")

    info("\n*** Starting network\n")
    net.start()

    srv1 = mgr.addContainer("srv1", "mqttServer", "eclipse-mosquitto", "", docker_args={})
    srv2 = mgr.addContainer("srv2", "webServer", "webserver", "", docker_args={})
    srv3 = mgr.addContainer("srv3", "drone", "drone", "python /drone/drone.py --ip 10.0.0.1 --port 1883 --debug", docker_args={})
    srv4 = mgr.addContainer("srv4", "client", "client", "bash", docker_args={})
    
    spawnXtermDocker("srv4")
    CLI(net)

    mgr.removeContainer("srv1")
    mgr.removeContainer("srv2")
    mgr.removeContainer("srv3")
    mgr.removeContainer("srv4")
    net.stop()
    mgr.stop()  
