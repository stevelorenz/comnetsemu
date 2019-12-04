#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Topology to test machine learning for object detection application.
"""

from pathlib import Path
from shlex import split
from subprocess import check_output

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

HOST_SRC_DIR = str(Path("./").absolute())


def get_ofport(ifce):
    """Get the openflow port based on iterface name

    :param ifce (str): Name of the interface
    """
    return check_output(split("ovs-vsctl get Interface {} ofport".format(ifce))).decode(
        "utf-8"
    )


def add_ovs_flows():
    """Add Openflow rules to redirect traffic between client and server to vnf."""
    check_output(split("ovs-ofctl del-flows s1"))

    check_output(
        split(
            'ovs-ofctl add-flow s1 "{proto},in_port={in_port},actions=output={out_port}"'.format(
                **{
                    "in_port": get_ofport("s1-client"),
                    "out_port": get_ofport("s1-vnf"),
                    "proto": "udp",
                }
            )
        )
    )
    check_output(
        split(
            'ovs-ofctl add-flow s1 "{proto},in_port={in_port},actions=output={out_port}"'.format(
                **{
                    "in_port": get_ofport("s1-server"),
                    "out_port": get_ofport("s1-client"),
                    "proto": "udp",
                }
            )
        )
    )


def disable_cksum_offload(ifces):
    """Disable RX/TX checksum offloading"""
    for ifce in ifces:
        check_output(split("sudo ethtool --offload %s rx off tx off" % ifce))


def testTopo():
    """testTopo"""

    net = Containernet(
        controller=Controller,
        link=TCLink,
        autoSetMacs=True,
        autoStaticArp=True,
        xterms=True,
    )

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")

    client = net.addDockerHost(
        "client",
        dimage="yolov2",
        ip="10.0.0.11/24",
        docker_args={"cpuset_cpus": "0", "hostname": "client"},
    )

    vnf = net.addDockerHost(
        "vnf",
        dimage="yolov2",
        ip="10.0.0.12/24",
        docker_args={"cpuset_cpus": "0", "hostname": "vnf"},
    )

    # Run server on another vCPU since it is more compute-intensive than client
    # and vnf.
    server = net.addDockerHost(
        "server",
        dimage="yolov2",
        ip="10.0.0.21/24",
        docker_args={"cpuset_cpus": "1", "hostname": "server"},
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, client, bw=10, delay="150ms", use_htb=True)
    net.addLinkNamedIfce(s1, vnf, bw=10, delay="150ms", use_htb=True)
    net.addLinkNamedIfce(s1, server, bw=10, delay="150ms", use_htb=True)

    info("*** Starting network\n")
    net.start()
    net.pingAll()
    add_ovs_flows()
    ifces = ["s1-vnf"]
    disable_cksum_offload(ifces)

    info("*** Enter CLI\n")
    CLI(net)

    info("*** Stopping network")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
