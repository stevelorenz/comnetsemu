#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Test/Debug script for using Ryu SDN controller
"""

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet
from mininet.node import OVSSwitch, RemoteController

if __name__ == "__main__":

    c = RemoteController('ryu', ip='127.0.0.1', port=6633)
    net = Containernet(controller=RemoteController)
    net.addController(c)

    h1 = net.addDockerHost("h1", ip="10.0.0.101/8", dimage="dev_test")
    h2 = net.addDockerHost("h2", ip="10.0.0.102/8", dimage="dev_test")

    s1 = net.addSwitch("s1", cls=OVSSwitch)

    net.addLink(s1, h1)
    net.addLink(s1, h2)

    net.start()
    CLI(net)
    net.stop()
