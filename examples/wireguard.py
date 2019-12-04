#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: This example demonstrates how to setup a Wireguard network tunnel between two hosts.
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
        "h1",
        dimage="sec_test",
        ip="10.0.0.1",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8)},
    )
    h2 = net.addDockerHost(
        "h2",
        dimage="sec_test",
        ip="10.0.0.2",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8)},
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, h1, bw=10, delay="1ms", use_htb=True)
    net.addLinkNamedIfce(s1, h2, bw=10, delay="1ms", use_htb=True)

    info("*** Starting network\n")
    net.start()

    info("*** Create wg key pairs\n")
    h1.cmd("umask 077; wg genkey > privatekey")
    h1.cmd("wg pubkey < privatekey > publickey")
    h1_pubkey = h1.cmd("cat ./publickey").replace("\n", " ").replace("\r", "")

    h2.cmd("umask 077; wg genkey > privatekey")
    h2.cmd("wg pubkey < privatekey > publickey")
    h2_pubkey = h2.cmd("cat ./publickey").replace("\n", " ").replace("\r", "")

    info("*** Create wg interfaces\n")
    h1.cmd("ip link add dev wg0 type wireguard")
    h1.cmd("ip address add dev wg0 192.168.0.1/24")

    h2.cmd("ip link add dev wg0 type wireguard")
    h2.cmd("ip address add dev wg0 192.168.0.2/24")

    info("*** Setup peer configuration\n")
    h1.cmd(
        "wg set wg0 listen-port 1337 private-key ./privatekey peer {} allowed-ips 192.168.0.0/24 endpoint 10.0.0.2:1337".format(
            h2_pubkey
        )
    )
    h1.cmd("ip link set up dev wg0")

    h2.cmd(
        "wg set wg0 listen-port 1337 private-key ./privatekey peer {} allowed-ips 192.168.0.0/24 endpoint 10.0.0.1:1337".format(
            h1_pubkey
        )
    )
    h2.cmd("ip link set up dev wg0")

    info("*** Test the connection\n")
    print("* Ping test count: %d" % PING_COUNT)
    ret = h1.cmd("ping -c %d 192.168.0.2" % PING_COUNT)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    print("* Measured loss rate: {:.2f}%".format(measured))

    info("*** Stopping network")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
