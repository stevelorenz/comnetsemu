#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
"""
About: Test core features implemented in ComNetsEmu
"""

import os
import functools
import sys
import time
import unittest

import pyroute2
import requests

from comnetsemu.clean import cleanup
from comnetsemu.net import Containernet, VNFManager
from comnetsemu.node import DockerHost
from mininet.log import setLogLevel
from mininet.node import OVSBridge
from mininet.topo import Topo

# Measurement error threshold
CPU_ERR_THR = 5  # %
MEM_ERR_THR = 50  # MB

HOST_NUM = 3


class TestTopo(Topo):
    def build(self, n):
        switch = self.addSwitch("s1")
        for h in range(1, n + 1):
            host = self.addHost(
                f"h{h}", ip=f"10.0.0.{h}/24", docker_args={"cpuset_cpus": "0"}
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
        cls.mgr = VNFManager(cls.net)

    @classmethod
    def tearDownClass(cls):
        cls.mgr.addContainer("zombie", "h1", "dev_test", "/bin/bash", {})
        cls.net.stop()
        cls.mgr.stop()
        cleanup()
        # if sys.exc_info() != (None, None, None):
        # cleanup()

    @unittest.skipIf(len(sys.argv) == 3 and sys.argv[2] == "-quick", "Schneller!")
    def test_ping(self):
        ret = self.net.pingAll()
        self.assertEqual(ret, 0.0)

    def test_container_crud(self):
        with self.assertRaises(KeyError):
            self.mgr.addContainer("foo", "foo", "dev_test", "/bin/bash", {})
        with self.assertRaises(ValueError):
            self.mgr.removeContainer("foo")
        with self.assertRaises(ValueError):
            self.mgr.monResourceStats("foo")

        cname_list = list()
        for i in range(1, HOST_NUM + 1):
            for j in range(1, i + 1):
                self.mgr.addContainer(
                    f"c{i}{j}",
                    f"h{i}",
                    "dev_test",
                    "/bin/bash",
                    docker_args={"cpu_quota": 1000},
                )
                cname_list.append(f"c{i}{j}")
        cname_list_get = self.mgr.getAllContainers()
        self.assertEqual(cname_list, cname_list_get)

        # Check docker_args works
        c11_ins = self.mgr._getDockerIns("c11")
        self.assertEqual(c11_ins.attrs["HostConfig"]["CpuQuota"], 1000)

        for i in range(1, HOST_NUM + 1):
            cname_list_host = self.mgr.getContainersDhost(f"h{i}")
            self.assertEqual(cname_list_host, [f"c{i}{k}" for k in range(1, i + 1)])
            for cname in cname_list_host:
                self.mgr.removeContainer(cname)

        for cname in cname_list:
            c_ins = self.mgr._getDockerIns(cname)
            self.assertTrue(c_ins is None)

        d1 = self.mgr.addContainer("d1", "h1", "dev_test", "bash", docker_args={})
        d1_get = self.mgr.getContainerInstance("d1")
        self.assertIs(d1, d1_get)
        self.mgr.removeContainer("d1")
        d2 = self.mgr.getContainerInstance("d2", None)
        self.assertEqual(d2, None)

        cwd = os.getcwd()
        d1 = self.mgr.addContainer(
            "d1",
            "h1",
            "dev_test",
            "bash",
            docker_args={"volumes": {f"{cwd}": {"bind": "/foo", "mode": "rw"}}},
        )
        mounts = d1.dins.attrs["Mounts"]
        for m in mounts:
            if m["Destination"] == "/foo":
                self.assertEqual(m["Source"], f"{cwd}")
            elif m["Destination"] == "/tmp/comnetsemu/appcontainermanger":
                self.assertEqual(m["Source"], "/tmp/comnetsemu/appcontainermanger")
            elif m["Destination"] == "/var/lib/docker":
                pass
            else:
                print(m)
                raise ValueError("Unkown mount is added!")
        self.mgr.removeContainer("d1")

    @unittest.skipIf(len(sys.argv) == 3 and sys.argv[2] == "-quick", "Schneller!")
    def test_container_isolation(self):
        h1 = self.net.get("h1")
        h2 = self.net.get("h2")
        h3 = self.net.get("h3")

        # CPU and memory
        h1.dins.update(cpu_quota=10000)
        h1.dins.update(mem_limit=10 * (1024 ** 2))  # in bytes

        c1 = self.mgr.addContainer(
            "c1", "h1", "dev_test", "stress-ng -c 1 -m 1 --vm-bytes 300M", {}
        )
        usages = self.mgr.monResourceStats(c1.name, sample_period=0.1, sample_num=2)
        cpu = sum(u[0] for u in usages) / len(usages)
        mem = sum(u[1] for u in usages) / len(usages)
        self.assertTrue(abs(cpu - 10.0) <= CPU_ERR_THR)
        self.assertTrue(abs(mem - 10.0) <= MEM_ERR_THR)
        self.mgr.removeContainer(c1.name)
        h1.dins.update(cpu_quota=-1)
        h1.dins.update(mem_limit=100 * (1024 ** 3))

        # Network
        for r in [h2, h3]:
            c1 = self.mgr.addContainer("c1", r.name, "dev_test", "iperf -s", {})
            ret = h1.cmd("iperf -c {} -u -b 10M -t 3".format(r.IP()))
            clt_bw = float(self.net._parseIperf(ret).split(" ")[0])
            self.assertTrue(clt_bw > 0.0)
            self.mgr.removeContainer(c1.name)

    # def test_container_migration(self):
    #     self.mgr.addContainer("c1", "h1", "dev_test", "/bin/bash", {})
    #     self.mgr.checkpoint("c1")
    #     from comnetsemu.cli import CLI
    #     CLI(self.net)
    #     self.mgr.removeContainer("c1")

    def test_appcontainermanager_rest_api(self):
        ip_route = pyroute2.IPRoute()
        mgr_api_ip = ip_route.get_addr(label="docker0")[0].get_attr("IFA_ADDRESS")
        mgr_api_port = 8000
        base_url = f"http://{mgr_api_ip}:{mgr_api_port}/containers"

        self.mgr.addContainer("c1", "h1", "dev_test", "bash", docker_args={})
        self.mgr.runRESTServerThread(ip=mgr_api_ip, port=mgr_api_port, enable_log=False)
        time.sleep(0.5)

        r = requests.get(base_url + "foo")
        self.assertEqual(r.status_code, 400)
        r = requests.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), ["c1"])
        self.mgr.removeContainer("c1")

        r = requests.post(base_url)
        self.assertEqual(r.status_code, 400)
        r = requests.post(base_url + "foo", json={})
        self.assertEqual(r.status_code, 400)
        cdata = {
            "name": "c1",
            "dhost": "h1",
            "dimage": "dev_test",
            # "dcmd": "bash",
            "docker_args": {},
        }
        r = requests.post(base_url, json=cdata)
        self.assertEqual(r.status_code, 400)
        cdata["dcmd"] = "bash"
        # Test the lock: c2 must be created earlier than c1.
        self.mgr.addContainer("c2", "h1", "dev_test", "bash", docker_args={})
        r = requests.post(base_url, json=cdata)
        self.assertEqual(r.status_code, 200)
        r = requests.get(base_url)
        self.assertEqual(r.json(), ["c2", "c1"])
        r = requests.delete(base_url + "/c3")
        self.assertEqual(r.status_code, 400)
        r = requests.delete(base_url + "/foo/bar")
        self.assertEqual(r.status_code, 400)
        r = requests.delete(base_url + "/c1")
        self.assertEqual(r.status_code, 200)

        self.mgr.removeContainer("c2")


if __name__ == "__main__":
    setLogLevel("warning")
    unittest.main(verbosity=2)
