#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Test core features implemented in ComNetsEmu
"""

import functools
import subprocess
import unittest

from comnetsemu.net import VNFManager, Containernet
from comnetsemu.node import DockerContainer, DockerHost
from mininet.topo import LinearTopo, Topo
from mininet.node import OVSBridge


def CLEANUP():
    subprocess.run(["ce", "-c"], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


class TestTopo(Topo):

    def build(self, k=2):
        self.k = k
        switch = self.addSwitch('s1')
        for h in range(1, k):
            host = self.addHost('h%s' % h)
            self.addLink(switch, host)


class TestVNFManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        dargs = {
            "dimage": "dev_test",
            "dcmd": "bash"
        }
        dhost_test = functools.partial(DockerHost, **dargs)

        cls.net = Containernet(
            topo=TestTopo(2),
            switch=OVSBridge,
            host=dhost_test,
        )

    def test_ping(self):
        ret = self.net.pingAll()
        self.assertEqual(ret, 0.0)

    @classmethod
    def tearDownClass(cls):
        cls.net.stop()
        CLEANUP()
