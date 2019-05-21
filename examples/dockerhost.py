#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example of using Docker as a Mininet host
"""

import comnetsemu.tool as tool
from comnetsemu.net import Containernet
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller


def testTopo():
    "Create an empty network and add nodes to it."

    # To be tested parameters at runtime
    loss_rates = list(range(10, 50, 10))

    net = Containernet(controller=Controller, link=TCLink)

    info('*** Adding controller\n')
    net.addController('c0')

    info('*** Adding hosts\n')
    h1 = net.addDockerHost('h1', dimage='dev_test', ip='10.0.0.1',
                           cpuset_cpus="0", cpu_quota=25000)
    h2 = net.addDockerHost('h2', dimage='dev_test', ip='10.0.0.2',
                           cpuset_cpus="1", cpu_quota=25000)

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLinkNamedIfce(s1, h1, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h2, bw=10, delay='1ms', use_htb=True)

    info('*** Starting network\n')
    net.start()

    info("**** Testing bandwidth between h1 and h2\n")
    net.iperf((h1, h2), l4Type='UDP', udpBw="10M")

    info("*** Configure the link loss rate of h1 at runtime\n")
    for loss in loss_rates:
        print("* The loss rate of h1 is {:.2f}%".format(loss))
        net.change_host_ifce_loss(h1, "h1-s1", loss)
        ret = h1.cmd("ping -c 30 10.0.0.2")
        sent, received = tool.parsePing(ret)
        measured = ((sent - received) / float(sent)) * 100.0
        print("Expected loss rate: {:.2f}%, measured loss rate: {:.2f}%".format(
            loss, measured
        ))

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    testTopo()
