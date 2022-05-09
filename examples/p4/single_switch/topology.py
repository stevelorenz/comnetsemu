#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: A basic example of a BMv2 simple switch (The reference P4 software switch)
"""

import pathlib
import subprocess
import shlex

from comnetsemu.cli import CLI
from comnetsemu.log import info, setLogLevel
from comnetsemu.net import Containernet
from comnetsemu.node import P4DockerHost, P4Switch
from mininet.link import TCLink
from mininet.node import Controller


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

        info("*** Adding hosts\n")
        h1 = net.addDockerHost(
            "h1",
            dimage="dev_test",
            ip="10.0.0.1/24",
            mac="00:04:00:00:00:01",
            docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8), "hostname": "h1"},
        )
        h2 = net.addDockerHost(
            "h2",
            dimage="dev_test",
            ip="10.0.0.2/24",
            mac="00:04:00:00:00:02",
            docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8), "hostname": "h2"},
        )

        info("*** Adding P4 switch\n")
        # TODO: Check if options for P4 simple switch can be improved.
        s1 = net.addP4Switch(
            "s1",
            sw_path="simple_switch",
            json_path="./build/basic.json",
            thrift_port=9090,
        )

        info("*** Creating links\n")
        net.addLink(s1, h1)
        net.addLink(s1, h2)

        info("*** Starting network\n")
        net.start()

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
