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
    client = net.addDockerHost('client', dimage='sec_test', ip='10.0.0.1',
                           cpuset_cpus="1", cpu_quota=25000)
    server = net.addDockerHost('server', dimage='nginx', ip='10.0.0.2',
                           cpuset_cpus="1", cpu_quota=25000)
    attacker = net.addDockerHost('attacker', dimage='sec_test', ip='10.0.0.3',
                           cpuset_cpus="0", cpu_quota=25000)

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLinkNamedIfce(s1, client, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, server, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, attacker, bw=10, delay='1ms', use_htb=True)

    info('*** Starting network\n')
    net.start()

    info('** client -> server\n')
    test_connection(client, "10.0.0.2")
    info('** attacker -> server\n')
    test_connection(attacker, "10.0.0.2")

    info('\n')

    # Create blacklist
    info('*** Create blacklist\n')
    # TODO: Create a nftables filter table on server and drop all incoming traffic that is coming from attacker (10.0.0.3)

    #  Check if client can connect and attacker can not.
    info('** client -> server\n')
    test_connection(client, "10.0.0.2")
    info('** attacker -> server\n')
    test_connection(attacker, "10.0.0.2")

    # attacker changes her ip address
    info("*** attacker changes ip address to a different one!\n")
    attacker.cmd("ip a f dev attacker-s1")
    attacker.cmd("ip a a 10.0.0." + str(random.randint(3,250)) + "/24 dev attacker-s1")

    # attacker can connect again
    info('** attacker -> server\n')
    test_connection(attacker, "10.0.0.2")

    info('\n')

    # Change to whitelist
    info('*** Create whitelist\n')
    # TODO: Create a whitelist that only allows incoming traffic from client (10.0.0.1)

    # The server can talk back to server
    info('** client -> server\n')
    test_connection(client, "10.0.0.2")
    info('** attacker -> server\n')
    test_connection(attacker, "10.0.0.2")

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
