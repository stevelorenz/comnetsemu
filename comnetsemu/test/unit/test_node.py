#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Test comnetsemu.node module
"""

import functools
import sys
import unittest

from comnetsemu.clean import cleanup
from comnetsemu.net import Containernet
from comnetsemu.node import DockerHost
from mininet.log import setLogLevel
from mininet.node import OVSBridge
from mininet.topo import Topo

HOST_NUM = 3


class TestTopo(Topo):
    def build(self, n):
        switch = self.addSwitch("s1")
        for h in range(1, n + 1):
            host = self.addHost(
                f"h{h}",
                ip=f"10.0.0.{h}/24",
                docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8)},
            )
            self.addLink(host, switch)


class TestVNFManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dargs = {"dimage": "dev_test"}
        dhost_test = functools.partial(DockerHost, **dargs)

        cls.net = Containernet(
            topo=TestTopo(HOST_NUM),
            switch=OVSBridge,
            host=dhost_test,
            autoSetMacs=True,
            autoStaticArp=True,
        )
        cls.net.start()

    def test_dockerhost_crud(self):
        d1 = self.net.addDockerHost(
            "d1", dimage="dev_test", ip="10.0.1.1/24", docker_args={}
        )
        self.net.addLink(d1.name, "s1")

    @classmethod
    def tearDownClass(cls):
        cls.net.stop()
        if sys.exc_info() != (None, None, None):
            cleanup()


if __name__ == "__main__":
    setLogLevel("warning")
    unittest.main(verbosity=2)
