#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Network topology to test MEICA+COIN.
"""

import argparse
import math
import os
import shlex
import subprocess
import sys
import time

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller, RemoteController
from mininet.term import makeTerm

PARENT_DIR = os.path.abspath(os.path.join(os.path.curdir, os.pardir))

class MeicaDistTest(object):
    """MeicaDistTest"""

    def __init__(self):
        self.net = Containernet(
            controller=Controller,
            link=TCLink,
            xterms=False,
        )

        self._vnfs = []
        self._switches = []

    def setup(self):
        info("*** Adding controller\n")
        self.net.addController(
            "c0", controller=RemoteController, port=6653, protocols="OpenFlow13"
        )

        # MARK: Host addresses below 11 could be used for network services.
        info("*** Adding end hosts\n")
        self.client = self.net.addDockerHost(
            "client",
            dimage="kodo_rlnc_coder",
            ip="10.0.1.11/16",
            docker_args={
                "cpuset_cpus": "0",
                "nano_cpus": int(3e8),
                "hostname": "client",
                "volumes": {
                    PARENT_DIR: {"bind": "/kodo_rlnc_coder", "mode": "rw"},
                },
                "working_dir": "/kodo_rlnc_coder/multi_hop_recoding_latency",
            },
        )

        self.server = self.net.addDockerHost(
            "server",
            dimage="kodo_rlnc_coder",
            ip="10.0.3.11/16",
            docker_args={
                "cpuset_cpus": "0",
                # Assume the server is busy now and pretty slow compared to the
                # network nodes :)
                "nano_cpus": int(3e8),
                "hostname": "server",
                "volumes": {
                    PARENT_DIR: {"bind": "/kodo_rlnc_coder", "mode": "rw"},
                },
                "working_dir": "/kodo_rlnc_coder/multi_hop_recoding_latency",
            },
        )

    def run_multi_htop(self, node_num, vnf_mode, recode_node):
        info("* Running multi_htop test.\n")
        
        info("*** write recode_node.temp\n")
        b=",".join(str(i) for i in recode_node)
        fo = open("recode_node.temp", "w")
        fo.write(b)
        fo.close()

        info("*** Adding network nodes.\n")
        host_addr_base = 10
        ans = int(math.floor(1e9 / node_num))
        for n in range(1, node_num + 1):
            vnf = self.net.addDockerHost(
                f"vnf{n}",
                dimage="kodo_rlnc_coder",
                ip=f"10.0.2.{host_addr_base+n}/16",
                docker_args={
                    "cpuset_cpus": "1",
                    "nano_cpus": int(math.floor(1e9 / node_num)),
                    "hostname": f"vnf{n}",
                    # For DPDK-related resources.
                    "volumes": {
                        "/sys/bus/pci/drivers": {
                            "bind": "/sys/bus/pci/drivers",
                            "mode": "rw",
                        },
                        "/sys/kernel/mm/hugepages": {
                            "bind": "/sys/kernel/mm/hugepages",
                            "mode": "rw",
                        },
                        "/sys/devices/system/node": {
                            "bind": "/sys/devices/system/node",
                            "mode": "rw",
                        },
                        "/dev": {"bind": "/dev", "mode": "rw"},
                        PARENT_DIR: {"bind": "/kodo_rlnc_coder", "mode": "rw"},
                    },
                    "working_dir": "/kodo_rlnc_coder/multi_hop_recoding_latency",
                },
            )
            self._vnfs.append(vnf)
            self._switches.append(self.net.addSwitch(f"s{n}", protocols="OpenFlow13"))

        info("*** Creating links.\n")
        # For end hosts
        self.net.addLinkNamedIfce(self._switches[0], self.client, bw=100, delay="50ms")
        self.net.addLinkNamedIfce(self._switches[-1], self.server, bw=100, delay="50ms")
        # For network nodes
        for n in range(0, node_num - 1):
            self.net.addLink(
                self._switches[n], self._switches[n + 1], bw=100, delay="50ms"
            )
        for i, s in enumerate(self._switches):
            self.net.addLinkNamedIfce(s, self._vnfs[i], bw=1000, delay="1ms")

        self.net.start()

        c0 = self.net.get("c0")
        r_n_str=''
        for i in args.recode_node:
            r_n_str=r_n_str+str(i)+' '
        makeTerm(c0, cmd=f"ryu-manager ./multi_hop_controller.py; read")

        info("*** Update ARP tables of VNFs.\n")
        for v in self._vnfs:
            v.cmd(f"ping -c 3 {self.server.IP()}")
            v.cmd(f"ping -c 3 {self.client.IP()}")

        info("*** Ping server from client.\n")
        ret = self.client.cmd(f"ping -c 3 {self.server.IP()}")
        print(ret)
        info("*** Ping client from server.\n")
        ret = self.server.cmd(f"ping -c 3 {self.client.IP()}")
        print(ret)

        if vnf_mode != "null":
            info("*** Run meica_vnf on each VNF in backgroud...\n")
            for v in self._vnfs:
                v.cmd(
                    f"cd /kodo_rlnc_coder/multi_hop_recoding_latency && python3 ./run_vnf.py --mode {vnf_mode} & 2>&1"
                )
                time.sleep(1)  # Avoid memory corruption among VNFs.

    def run(self, topo, node_num, vnf_mode,recode_node):
        if node_num < 2:
            raise RuntimeError("The minimal number of nodes is two.")
        if len(recode_node) != node_num:
            raise RuntimeError("recode_node list don't match nood_num.")
        if topo == "multi_htop" :
            self.run_multi_htop(node_num, vnf_mode,recode_node)


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Run this script with sudo.", file=sys.stderr)
        sys.exit(1)
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument(
        "--topo",
        type=str,
        default="multi_htop",
        choices=["multi_htop"],
        help="Name of the test topology.",
    )
    parser.add_argument(
        "--node_num", type=int, default=3, dest="node_num", help="Number of nodes in the network."
    )
    parser.add_argument(
        "--vnf_mode",
        type=str,
        default="store_forward",
        choices=["null", "store_forward", "compute_forward"],
        help="Mode to run all VNFs.",
    )
    # add a new argument to set the recode node
    parser.add_argument(
        "--recode_node",
        type=int,
        nargs="+",
        default= [0,0,0],
        choices=[0,1],
        help="choice which node to run recode, ex: --recode_node 0 1 0"
    )
    args = parser.parse_args()
    home_dir = os.path.expanduser("~")
    xresources_path = os.path.join(home_dir, ".Xresources")
    if os.path.exists(xresources_path):
        subprocess.run(shlex.split(f"xrdb -merge {xresources_path}"), check=True)

    # IPv6 is currently not used.
    subprocess.run(
        shlex.split("sysctl -w net.ipv6.conf.all.disable_ipv6=1"),
        check=True,
    )

    setLogLevel("info")
    test = MeicaDistTest()
    test.setup()

    try:
        test.run(topo=args.topo, node_num=args.node_num, vnf_mode=args.vnf_mode, recode_node=args.recode_node)
        info("*** Enter CLI\n")
        CLI(test.net)
    finally:
        info("*** Stopping network")
        test.net.stop()
        subprocess.run(shlex.split("sudo killall ryu-manager"), check=True)
        subprocess.run(
            shlex.split("sysctl -w net.ipv6.conf.all.disable_ipv6=0"),
            check=True,
        )
