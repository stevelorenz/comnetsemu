#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Example for a customized host

A typical use case for a customized host classes is when you need to do some configuration
for all hosts of a specific type.
For example, in your emulated network, the IPv6 should be disabled on hosts.
This can also be done by first creating a normal host and then using the `cmd` method to run custom command.
However, creating a customized class is more convenient.

You can override the `config` method to add customized configurations.
"""

from comnetsemu.cli import CLI
from comnetsemu.log import info, setLogLevel
from comnetsemu.net import Containernet
from comnetsemu.node import DockerHost
from mininet.link import TCLink
from mininet.node import Controller


class CustomHost(DockerHost):

    """A customized host which disables IPv6 support"""

    def config(self, **params):
        r = super().config(**params)

        self.cmd('echo "test" > /tmp/comnetsemu_test.log')
        # Disable IPv6
        self.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        self.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        self.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")

        return r


def testTopo():

    # xterms=True, spawn xterms for all nodes after net.start()
    net = Containernet(controller=Controller, link=TCLink, xterms=True)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    h1 = net.addHost(
        "h1",
        cls=CustomHost,
        dimage="dev_test",
        ip="10.0.0.1/24",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8), "hostname": "h1"},
    )
    h2 = net.addHost(
        "h2",
        cls=CustomHost,
        dimage="dev_test",
        ip="10.0.0.2/24",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8), "hostname": "h2"},
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, h1, bw=10, delay="100ms")
    net.addLinkNamedIfce(s1, h2, bw=10, delay="100ms")

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
