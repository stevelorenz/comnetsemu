#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import comnetsemu.tool as tool
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

PING_COUNT = 3


def testTopo():
    "Create an empty network and add nodes to it."

    net = Containernet(controller=Controller, link=TCLink)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    client = net.addDockerHost(
        "client",
        dimage="sec_test",
        ip="10.0.0.1/24",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )
    server = net.addDockerHost(
        "server",
        dimage="nginx",
        ip="10.0.0.2/24",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )
    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, client, bw=100, delay="10ms")
    net.addLinkNamedIfce(s1, server, bw=100, delay="10ms")

    info("*** Starting network\n")
    net.start()

    info("** client -> server\n")
    test_connection(client, "10.0.0.2")

    info("\n")

    # Create whitelist
    info("*** Create whitelist\n")
    server.cmd("nft add table inet filter")
    server.cmd(
        "nft add chain inet filter input { type filter hook input priority 0 \; policy drop \; }"
    )
    server.cmd("nft add rule inet filter input ip saddr 10.0.0.1 accept")

    # The server can talk back to client
    info("** server -> client\n")
    test_connection(server, "10.0.0.2")
    # But he cannot talk to some other server on the internet, this is a problem
    info("** server -> internet\n")
    test_connection(server, "8.8.8.8")

    info("\n")

    info("*** Enable connection tracking\n")
    server.cmd("nft add rule inet filter input ct state established,related accept")

    info("** server -> internet\n")
    test_connection(server, "8.8.8.8")

    # client is overdoing it a little and our server cannot handle all of its requests...
    info("*** client is flodding server with too many requests!\n")
    server.cmd("iperf -s &")
    print(client.cmd("iperf -c 10.0.0.2"))

    server.cmd(
        "nft insert rule inet filter input position 2 limit rate over 1 mbytes/second drop"
    )

    print(client.cmd("iperf -c 10.0.0.2"))

    info("\n")

    info("*** Stopping network")
    net.stop()


def test_connection(source_container, target_ip):
    ret = source_container.cmd("ping -c " + str(PING_COUNT) + " " + target_ip)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    if measured == 0.0:
        info("* Connection established\n")
    else:
        info("* Connection denied\n")


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
