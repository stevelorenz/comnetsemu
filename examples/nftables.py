#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: This examples shows the basic setup of a firewall with nftables.
"""

import comnetsemu.tool as tool
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

PING_COUNT = 15


def testTopo():
    "Create an empty network and add nodes to it."

    net = Containernet(controller=Controller, link=TCLink)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    h1 = net.addDockerHost(
        "h1", dimage="sec_test", ip="10.0.0.1", docker_args={"cpuset_cpus": "0"}
    )
    h2 = net.addDockerHost(
        "h2", dimage="sec_test", ip="10.0.0.2", docker_args={"cpuset_cpus": "0"}
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, h1, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, h2, bw=10, delay="10ms")

    info("*** Starting network\n")
    net.start()

    test_connection(h2)

    info("*** Add drop all nftables rule\n")
    h1.cmd("nft add table inet filter")
    h1.cmd(
        "nft add chain inet filter input { type filter hook input priority 0 \; policy accept \; }"
    )
    h1.cmd("nft add rule inet filter input ip saddr 10.0.0.2 counter drop")

    test_connection(h2)

    print(h1.cmd("nft list table inet filter"))

    info("*** Stopping network")
    net.stop()


def test_connection(client):
    info("*** Test the connection\n")
    print("* Ping test count: %d" % PING_COUNT)
    ret = client.cmd("ping -c %d 10.0.0.1" % PING_COUNT)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    print("* Measured loss rate: {:.2f}%".format(measured))


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
