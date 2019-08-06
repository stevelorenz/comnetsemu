#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Test performance of features implemented in ComNetsEmu
"""

import unittest
import sys

import comnetsemu.tool as tool
from comnetsemu.net import Containernet
from comnetsemu.clean import cleanup
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.node import Controller


def create_network(host_num, host_sw_loss=0, sw_sw_loss=0):
    """h-s multihop chain"""
    net = Containernet(link=TCLink, controller=Controller)
    net.addController('c0')

    last_sw = None
    for i in range(host_num):
        host = net.addDockerHost('h%s' %
                                 (i+1), dimage='dev_test',
                                 ip="10.0.0.%s/24" % (i+1))
        switch = net.addSwitch("s%s" % (i + 1))
        net.addLink(switch, host, bw=10, delay="100ms",
                    use_htb=True, loss=host_sw_loss)
        if last_sw:
            net.addLink(switch, last_sw, use_htb=True,
                        bw=10, delay="100ms", loss=sw_sw_loss)
        last_sw = switch

    return net


if __name__ == "__main__":
    setLogLevel("warning")
    unittest.main(verbosity=2)
