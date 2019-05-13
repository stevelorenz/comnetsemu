#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example of using Docker as a Mininet host
"""

from comnetsemu.net import Containernet
from mininet.cli import CLI
from mininet.log import info, setLogLevel
from mininet.node import Controller


def testTopo():
    "Create an empty network and add nodes to it."

    net = Containernet(controller=Controller)

    info('*** Adding controller\n')
    net.addController('c0')

    info('*** Adding hosts\n')
    h1 = net.addDockerHost('h1', dimage='dev_test', ip='10.0.0.1')
    h2 = net.addDockerHost('h2', dimage='dev_test', ip='10.0.0.2')

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLink(s1, h1)
    net.addLink(s1, h2)

    info('*** Starting network\n')
    net.start()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    testTopo()
