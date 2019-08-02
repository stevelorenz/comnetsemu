#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example of using Docker as a Mininet host
"""

import comnetsemu.tool as tool
from time import sleep
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller
import random

PING_COUNT = 3


def testTopo():
    "Create an empty network and add nodes to it."

    net = Containernet(controller=Controller, link=TCLink)

    info('*** Adding controller\n')
    net.addController('c0')

    info('*** Adding hosts\n')
    h1 = net.addDockerHost('h1', dimage='sec_test', ip='10.0.0.1',
                           cpuset_cpus="1", cpu_quota=25000)
    h2 = net.addDockerHost('h2', dimage='nginx', ip='10.0.0.2',
                           cpuset_cpus="1", cpu_quota=25000)
    h3 = net.addDockerHost('h3', dimage='sec_test', ip='10.0.0.3',
                           cpuset_cpus="0", cpu_quota=25000)

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLinkNamedIfce(s1, h1, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h2, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h3, bw=10, delay='1ms', use_htb=True)

    info('*** Starting network\n')
    net.start()

    info('** h1 -> h2\n')
    test_connection(h1, "10.0.0.2")
    info('** h3 -> h2\n')
    test_connection(h3, "10.0.0.2")

    info('\n')

    # Create blacklist
    info('*** Create blacklist\n')
    # TODO: Create a nftables filter table on h2 and drop all incoming traffic that is coming from h3 (10.0.0.3)

    #  Check if h1 can connect and h3 can not.
    info('** h1 -> h2\n')
    test_connection(h1, "10.0.0.2")
    info('** h3 -> h2\n')
    test_connection(h3, "10.0.0.2")

    # h3 changes her ip address
    info("*** h3 changes ip address to a different one!\n")
    h3.cmd("ip a f dev h3-s1")
    h3.cmd("ip a a 10.0.0." + str(random.randint(3,250)) + "/24 dev h3-s1")

    # h3 can connect again
    info('** h3 -> h2\n')
    test_connection(h3, "10.0.0.2")

    info('\n')

    # Change to whitelist
    info('*** Create whitelist\n')
    # TODO: Create a whitelist that only allows incoming traffic from h1 (10.0.0.1)

    # The server can talk back to h2
    info('** h1 -> h2\n')
    test_connection(h1, "10.0.0.2")
    info('** h3 -> h2\n')
    test_connection(h3, "10.0.0.2")

    info('*** Stopping network')
    net.stop()


def test_connection(source_container, target_ip):
    ret = source_container.cmd("ping -c " + str(PING_COUNT) + " " + target_ip)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    if measured == 0.0:
        info('* Connection established\n')
    else:
        info('* Connection denied\n')


if __name__ == '__main__':
    setLogLevel('info')
    testTopo()
