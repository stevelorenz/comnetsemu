#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: A basic example of a BMv2 simple switch (The reference P4 software switch)
"""

import os
import pathlib
import shlex
import subprocess

from comnetsemu.cli import CLI
from comnetsemu.log import info, setLogLevel
from comnetsemu.net import Containernet
from comnetsemu.node import P4DockerHost, P4Switch, P4RuntimeSwitch
from mininet.link import TCLink
from mininet.node import Controller

CURRENT_DIR = os.path.abspath(os.path.curdir)


def buildP4Program():
    pathlib.Path("./build").mkdir(parents=True, exist_ok=True)
    info("*** Build the P4 program: ./basic.p4 with p4c-bm2-ss compiler.\n")
    info("*** The generated JSON output is located in ./build/basic.json.\n")
    subprocess.run(
        shlex.split(
            "p4c-bm2-ss --p4v 16 --p4runtime-files ./build/basic.p4.p4info.txt -o ./build/basic.json ./basic.p4"
        ),
        check=True,
    )


def testTopo():

    net = None

    try:
        info("*** Create the test network\n")

        # xterms=True, spawn xterms for all nodes after net.start()
        net = Containernet(link=TCLink, xterms=True)

        volumes = {CURRENT_DIR: {"bind": "/tmp/single_switch", "mode": "rw"}}

        info("*** Adding hosts\n")
        h1 = net.addHost(
            "h1",
            cls=P4DockerHost,
            dimage="dev_test",
            ip="10.0.0.1/24",
            mac="00:04:00:00:00:01",
            docker_args={
                "cpuset_cpus": "0",
                "nano_cpus": int(1e8),
                "hostname": "h1",
                "volumes": volumes,
                "working_dir": "/tmp/single_switch",
            },
        )
        h2 = net.addHost(
            "h2",
            cls=P4DockerHost,
            dimage="dev_test",
            ip="10.0.0.2/24",
            mac="00:04:00:00:00:02",
            docker_args={
                "cpuset_cpus": "0",
                "nano_cpus": int(1e8),
                "hostname": "h2",
                "volumes": volumes,
                "working_dir": "/tmp/single_switch",
            },
        )

        info("*** Adding P4 switch\n")
        # TODO: Check if options for P4 simple switch can be improved.
        s1 = net.addSwitch(
            "s1",
            cls=P4RuntimeSwitch,
            sw_path="simple_switch_grpc",
            json_path="./build/basic.json",
            grpc_port=50051,
            thrift_port=9090,
        )

        info("*** Creating links\n")
        net.addLink(s1, h1)
        net.addLink(s1, h2)

        info("*** Starting network\n")
        net.start()

        info("*** Information of created hosts:\n")
        for h in net.hosts:
            h.describe()
        info("*** Information of created switches:\n")
        for s in net.switches:
            s.describe()

        info("*** Enter CLI\n")
        info("Use help command to get CLI usages\n")
        CLI(net)

    finally:
        info("*** Stopping network")
        if net:
            net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    buildP4Program()
    testTopo()
