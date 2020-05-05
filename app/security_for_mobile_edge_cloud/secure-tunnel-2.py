#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import comnetsemu.tool as tool
from comnetsemu.net import Containernet
from time import sleep
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

PING_COUNT = 15


def testTopo():
    "Create an empty network and add nodes to it."

    net = Containernet(controller=Controller, link=TCLink)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    center = net.addDockerHost(
        "center",
        dimage="sec_test",
        ip="10.0.0.1",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000},
    )
    client1 = net.addDockerHost(
        "h2",
        dimage="sec_test",
        ip="10.0.0.2",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000},
    )
    client2 = net.addDockerHost(
        "h3",
        dimage="sec_test",
        ip="10.0.0.3",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )
    client3 = net.addDockerHost(
        "h4",
        dimage="sec_test",
        ip="10.0.0.4",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, center, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, client1, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, client2, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, client3, bw=10, delay="10ms")

    try:
        info("*** Starting network\n")
        net.start()

        info("*** Create wg key pairs\n")
        center_private_key, center_public_key = generate_key_pair_for_host(center)
        h2_private_key, h2_public_key = generate_key_pair_for_host(client1)
        h3_private_key, h3_public_key = generate_key_pair_for_host(client2)
        h4_private_key, h4_public_key = generate_key_pair_for_host(client3)

        info("*** Create wg interfaces\n")

        info(
            "*** Create a star topology with center as the center. Instead of using wg tool write a configuration for the\n"
        )
        info(
            "*** interface and place it in /etc/wireguard/wg0.conf, then use the wg-quick command to setup the interface.\n"
        )
        info(
            "*** The wg and wg-quick manpages contain a reference for the syntax of the configuration file.\n"
        )
        info(
            "*** Use the network 192.168.0.0/24 for the inner tunnel and asign 192.168.0.1 to the center.\n"
        )

        while (
            not test_connection(client1, "192.168.0.1")
            or not test_connection(client2, "192.168.0.1")
            or not test_connection(client3, "192.168.0.1")
        ):
            sleep(10)

    except KeyboardInterrupt:
        info("** KeyboardInterrupt detected, exit the program.\n")

    finally:
        info("*** Stopping network")
        net.stop()


def generate_key_pair_for_host(center):
    center.cmd("umask 077; wg genkey > privatekey")
    center.cmd("wg pubkey < privatekey > publickey")
    center_pubkey = center.cmd("cat ./publickey").replace("\n", " ").replace("\r", "")
    center_privatekey = (
        center.cmd("cat ./privatekey").replace("\n", " ").replace("\r", "")
    )
    return center_privatekey, center_pubkey


def test_connection(source_container, target_ip):
    ret = source_container.cmd("ping -W 1 -c " + str(PING_COUNT) + " " + target_ip)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    if measured == 0.0:
        return True
    else:
        return False


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
