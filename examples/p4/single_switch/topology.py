#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: A basic example of a BMv2 simple switch (The reference P4 software switch)
"""

import argparse
import os

from comnetsemu.cli import CLI
from comnetsemu.log import info, setLogLevel
from comnetsemu.net import Containernet
from comnetsemu.node import P4DockerHost, P4Switch, P4RuntimeSwitch
from comnetsemu.builder import P4Builder
from mininet.link import TCLink

AUTOTEST_MODE = os.environ.get("COMNETSEMU_AUTOTEST_MODE", 0)
THIS_DIR = os.path.abspath(os.path.curdir)


def run_test_topo(switch_type: str, json_path: str):

    net = None

    try:
        info("*** Create the test network\n")

        net = Containernet(link=TCLink, xterms=False)

        info("*** Adding hosts\n")
        h1 = net.addHost(
            "h1",
            cls=P4DockerHost,
            dimage="dev_test",
            ip="192.168.0.1/24",
            mac="10:00:00:00:00:01",
            docker_args={
                "hostname": "h1",
            },
        )
        h2 = net.addHost(
            "h2",
            cls=P4DockerHost,
            dimage="dev_test",
            ip="192.168.0.2/24",
            mac="10:00:00:00:00:02",
            docker_args={
                "hostname": "h2",
            },
        )

        if switch_type == "P4Switch":
            info("*** Adding one P4Switch: s1\n")
            s1 = net.addSwitch(
                "s1",
                cls=P4Switch,
                json_path=json_path,
                thrift_port=9090,
            )
        elif switch_type == "P4RuntimeSwitch":
            s1 = net.addSwitch(
                "s1",
                cls=P4RuntimeSwitch,
                json_path=json_path,
                thrift_port=9090,
                grpc_port=50051,
            )
        else:
            raise RuntimeError(f"Unknown switch type: {switch_type}")

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

        # The ARP handling is not implemented in the basic.p4
        info("*** Add static ARP entries in hosts\n")
        h1.cmd("arp -s 192.168.0.2 10:00:00:00:00:02")
        h2.cmd("arp -s 192.168.0.1 10:00:00:00:00:01")

        info("*** Add table entries in P4Switch with simple_switch_CLI.\n")
        s1.cmdPrint('echo "table_info ipv4_lpm" | simple_switch_CLI')

        s1.cmdPrint(
            'echo "table_add ipv4_lpm direct_to_port 192.168.0.1/32 => 1" | simple_switch_CLI'
        )
        s1.cmdPrint(
            'echo "table_add ipv4_lpm direct_to_port 192.168.0.2/32 => 2" | simple_switch_CLI'
        )

        s1.cmdPrint('echo "table_dump ipv4_lpm" | simple_switch_CLI')

        loss = net.ping(hosts=[h1, h2])
        print(f"The loss rate between h1 and h2: {loss}")

        if not AUTOTEST_MODE:
            info("*** Enter CLI\n")
            info("Use help command to get CLI usages\n")
            CLI(net)

    finally:
        info("*** Stopping network")
        if net:
            net.stop()


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--switch_type",
        default="P4Switch",
        choices=["P4Switch", "P4RuntimeSwitch"],
        type=str,
        help="The type of the switch",
    )
    args = parser.parse_args()

    setLogLevel("info")
    p4_builder = P4Builder(p4_src="./basic.p4")
    json_out, _ = p4_builder.build()
    run_test_topo(args.switch_type, json_out.as_posix())
    p4_builder.clean()


if __name__ == "__main__":
    main()
