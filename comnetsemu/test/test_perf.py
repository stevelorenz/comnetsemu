#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Test performance of features implemented in ComNetsEmu
"""

import subprocess
import unittest

import comnetsemu.tool as tool
from comnetsemu.net import Containernet
from comnetsemu.cli import CLI
from mininet.link import TCLink
from mininet.node import Controller


def CLEANUP():
    subprocess.run(["ce", "-c"], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


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


class TestTCLink(unittest.TestCase):

    LOSS_THR = 10

    def test_link_loss(self):
        host_num = 3

        net = create_network(host_num, host_sw_loss=0, sw_sw_loss=10)
        hosts = [net.get("h%s" % n) for n in range(1, host_num+1)]

        net.start()
        ret = hosts[0].cmd("ping -i 0.5 -c 20 %s" % hosts[1].IP())
        sent, received = tool.parsePing(ret)
        loss_rate = ((sent - received) / float(sent)) * 100.0
        self.assertTrue(abs(loss_rate - 20.0) <= self.LOSS_THR)

        net.stop()
        CLEANUP()
