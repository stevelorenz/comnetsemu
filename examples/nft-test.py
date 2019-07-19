#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example of using Docker as a Mininet host
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

    info('*** Adding controller\n')
    net.addController('c0')

    info('*** Adding hosts\n')
    h1 = net.addDockerHost('h1', dimage='sec_test', ip='10.0.0.1',
                           cpuset_cpus="0", cpu_quota=25000)
    h2 = net.addDockerHost('h2', dimage='sec_test', ip='10.0.0.2',
                           cpuset_cpus="1", cpu_quota=25000)

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLinkNamedIfce(s1, h1, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h2, bw=10, delay='1ms', use_htb=True)

    info('*** Starting network\n')
    net.start()

    test_connection(h1)

    info('*** Add drop all nftables rule\n')
    h1.cmd("nft add table inet filter")
    h1.cmd("nft add chain inet filter input { type filter hook input priority 0 \; policy drop \; }")

    test_connection(h1)

    info('*** Stopping network')
    net.stop()


def test_connection(h1):
    info("*** Test the connection\n")
    print("* Ping test count: %d" % PING_COUNT)
    ret = h1.cmd("ping -c %d 10.0.0.2" % PING_COUNT)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    print("* Measured loss rate: {:.2f}%".format(measured))


if __name__ == '__main__':
    setLogLevel('info')
    testTopo()
