#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
About: Basic example of using Docker as a Mininet host.
       Like upstream Mininet, the network topology can be either created by
       provide a topology class or directly using the network object.

Topo: Two Docker hosts (h1, h2) connected directly to a single switch (s1).

Tests:
- Iperf UDP bandwidth test between h1 and h2.
- Packet losses test with ping and increased link loss rate.
"""

import comnetsemu.tool as tool
from comnetsemu.net import Containernet
from comnetsemu.node import DockerHost
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller, OVSBridge
from mininet.topo import Topo

PING_COUNT = 15


def run_net():

    # To be tested parameters at runtime
    loss_rates = [30]

    net = Containernet(controller=Controller, link=TCLink)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    h1 = net.addHost(
        "h1",
        cls=DockerHost,
        dimage="dev_test",
        ip="10.0.0.1/24",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8)},
    )
    h2 = net.addHost(
        "h2",
        cls=DockerHost,
        dimage="dev_test",
        ip="10.0.0.2/24",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8)},
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLink(h1, s1, bw=10, delay="100ms", intfName1="h1-s1", intfName2="s1-h1")
    net.addLink(h2, s1, bw=10, delay="100ms", intfName1="h2-s1", intfName2="s1-h2")

    info("*** Starting network\n")
    net.start()

    info("**** Testing bandwidth between h1 and h2\n")
    net.iperf((h1, h2), l4Type="UDP", udpBw="10M")

    info("*** Configure the link loss rate of h1 at runtime\n")
    for loss in loss_rates:
        print("* The loss rate of h1 is {:.2f}%, unidirectional".format(loss))
        print("* Ping test count: %d" % PING_COUNT)

        host = net.get("h1")
        # INFO: The parent number is defined in mininet/link.py
        ret = host.cmd(
            "tc qdisc change dev {} {} handle 10: netem loss {}%".format(
                "h1-s1", " parent 5:1", loss
            )
        )
        if ret != "":
            print("Failed to change loss. Error:%s\n", ret)

        ret = h1.cmd("ping -c %d 10.0.0.2" % PING_COUNT)
        sent, received = tool.parsePing(ret)
        measured = ((sent - received) / float(sent)) * 100.0
        print(
            "Expected loss rate: {:.2f}%, measured loss rate: {:.2f}%".format(
                loss, measured
            )
        )

    info("*** Stopping network")
    net.stop()


class TestTopo(Topo):
    def build(self, n):
        switch = self.addSwitch("s1")
        for h in range(1, n + 1):
            host = self.addHost(
                "h%s" % h,
                cls=DockerHost,
                dimage="dev_test",
                docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8)},
            )
            self.addLink(switch, host, bw=10, delay="100ms")


def run_topo():
    net = Containernet(
        controller=Controller, link=TCLink, switch=OVSBridge, topo=TestTopo(2)
    )

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Starting network\n")
    net.start()
    net.pingAll()
    h1 = net.get("h1")
    h2 = net.get("h2")
    net.iperf((h1, h2), l4Type="UDP", udpBw="10M")
    info("*** Stopping network")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    run_net()
    run_topo()
