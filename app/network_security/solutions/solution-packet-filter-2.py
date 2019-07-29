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
    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLinkNamedIfce(s1, h1, bw=100, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h2, bw=100, delay='1ms', use_htb=True)

    info('*** Starting network\n')
    net.start()

    info('** h1 -> h2\n')
    test_connection(h1, "10.0.0.2")

    info('\n')

    # Create whitelist
    info('*** Create whitelist\n')
    h2.cmd("nft add table inet filter")
    h2.cmd("nft add chain inet filter input { type filter hook input priority 0 \; policy drop \; }")
    h2.cmd("nft add rule inet filter input ip saddr 10.0.0.1 accept")

    # The server can talk back to h1
    info('** h2 -> h1\n')
    test_connection(h2, "10.0.0.2")
    # But he cannot talk to some other server on the internet, this is a problem
    info('** h2 -> internet\n')
    test_connection(h2, "8.8.8.8")

    info('\n')


    info('*** Enable connection tracking\n')
    h2.cmd("nft add rule inet filter input ct state established,related accept")

    info('** h2 -> internet\n')
    test_connection(h2, "8.8.8.8")

    # h1 is overdoing it a little and our server cannot handle all of its requests...
    info('*** h1 is flodding h2 with too many requests!\n')
    h2.cmd("iperf -s &")
    print(h1.cmd("iperf -c 10.0.0.2"))

    h2.cmd("nft insert rule inet filter input position 2 limit rate over 1 mbytes/second drop")

    print(h1.cmd("iperf -c 10.0.0.2"))

    info('\n')

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
