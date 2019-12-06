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
    compressor = net.addDockerHost(
        "compressor",
        dimage="o2sc",
        ip="10.0.0.1/24",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000, "hostname": "compressor"},
    )
    decompressor = net.addDockerHost(
        "decompressor",
        dimage="o2sc",
        ip="10.0.0.2/24",
        docker_args={
            "cpuset_cpus": "1",
            "cpu_quota": 25000,
            "hostname": "decompressor",
        },
    )
    source_1 = net.addDockerHost(
        "source_1",
        dimage="o2sc",
        ip="10.0.0.11/24",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000, "hostname": "source_1"},
    )
    source_2 = net.addDockerHost(
        "source_2",
        dimage="o2sc",
        ip="10.0.0.12/24",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000, "hostname": "source_2"},
    )
    source_3 = net.addDockerHost(
        "source_3",
        dimage="o2sc",
        ip="10.0.0.13/24",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000, "hostname": "source_3"},
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, compressor, bw=10, delay="100ms")
    net.addLinkNamedIfce(s1, decompressor, bw=10, delay="100ms")
    net.addLinkNamedIfce(s1, source_1, bw=10, delay="100ms")
    net.addLinkNamedIfce(s1, source_2, bw=10, delay="100ms")
    net.addLinkNamedIfce(s1, source_3, bw=10, delay="100ms")

    info("*** Starting network\n")
    net.start()
    net.pingAll()

    info("*** Enter CLI\n")
    info("Use help command to get CLI usages\n")
    CLI(net)

    info("*** Stopping network")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
