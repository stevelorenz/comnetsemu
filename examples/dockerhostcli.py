#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example to spawn Xterms for Docker hosts
"""

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller


def testTopo():

    # xterms=True, spawn xterms for all nodes after net.start()
    net = Containernet(controller=Controller, link=TCLink, xterms=True)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    h1 = net.addDockerHost(
        "h1",
        dimage="dev_test",
        ip="10.0.0.1/24",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8), "hostname": "h1"},
    )
    h2 = net.addDockerHost(
        "h2",
        dimage="dev_test",
        ip="10.0.0.2/24",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8), "hostname": "h2"},
    )
    h3 = net.addHost("h3", ip="10.0.0.3/24")
    h4 = net.addHost("h4", ip="10.0.0.4/24")

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, h1, bw=10, delay="100ms")
    net.addLinkNamedIfce(s1, h2, bw=10, delay="100ms")
    net.addLinkNamedIfce(s1, h3, bw=10, delay="100ms")
    net.addLinkNamedIfce(s1, h4, bw=10, delay="100ms")

    info("*** Starting network\n")
    net.start()

    info("*** Enter CLI\n")
    info("Use help command to get CLI usages\n")
    CLI(net)

    info("*** Stopping network")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
