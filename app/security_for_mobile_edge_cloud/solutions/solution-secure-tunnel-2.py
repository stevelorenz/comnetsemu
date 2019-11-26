#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import comnetsemu.tool as tool
from comnetsemu.net import Containernet
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
        "client1",
        dimage="sec_test",
        ip="10.0.0.2",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000},
    )
    client3 = net.addDockerHost(
        "client3",
        dimage="sec_test",
        ip="10.0.0.3",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )
    client4 = net.addDockerHost(
        "client4",
        dimage="sec_test",
        ip="10.0.0.4",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, center, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, client1, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, client3, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, client4, bw=10, delay="10ms")

    info("*** Starting network\n")
    net.start()

    info("*** Create wg key pairs\n")
    center_private_key, center_public_key = generate_key_pair_for_host(center)
    client1_private_key, client1_public_key = generate_key_pair_for_host(client1)
    client3_private_key, client3_public_key = generate_key_pair_for_host(client3)
    client4_private_key, client4_public_key = generate_key_pair_for_host(client4)

    info("*** Create wg interfaces\n")

    center.cmd(
        "printf -- '[Interface]\nAddress = 192.168.0.1/24\nSaveConfig = true\nListenPort = 1337\nPrivateKey = "
        + center_private_key
        + "\n[Peer]\nPublicKey = "
        + client1_public_key
        + "\nAllowedIPs = 192.168.0.2/32\nEndpoint = 10.0.0.2:1337\n\n[Peer]\nPublicKey = "
        + client3_public_key
        + "\nAllowedIPs = 192.168.0.3/32\nEndpoint = 10.0.0.3:1337\n\n[Peer]\nPublicKey = "
        + client4_public_key
        + "\nAllowedIPs = 192.168.0.4/32\nEndpoint = 10.0.0.4:1337\n\n' > /etc/wireguard/wg0.conf"
    )
    client1.cmd(
        "printf -- '[Interface]\nAddress = 192.168.0.2/24\nSaveConfig = true\nListenPort = 1337\nPrivateKey = "
        + client1_private_key
        + "\n[Peer]\nPublicKey = "
        + center_public_key
        + "\nAllowedIPs = 192.168.0.0/24\nEndpoint = 10.0.0.1:1337\n' > /etc/wireguard/wg0.conf"
    )
    client3.cmd(
        "printf -- '[Interface]\nAddress = 192.168.0.3/24\nSaveConfig = true\nListenPort = 1337\nPrivateKey = "
        + client3_private_key
        + "\n[Peer]\nPublicKey = "
        + center_public_key
        + "\nAllowedIPs = 192.168.0.0/24\nEndpoint = 10.0.0.1:1337\n' > /etc/wireguard/wg0.conf"
    )
    client4.cmd(
        "printf -- '[Interface]\nAddress = 192.168.0.4/24\nSaveConfig = true\nListenPort = 1337\nPrivateKey = "
        + client4_private_key
        + "\n[Peer]\nPublicKey = "
        + center_public_key
        + "\nAllowedIPs = 192.168.0.0/24\nEndpoint = 10.0.0.1:1337\n' > /etc/wireguard/wg0.conf"
    )

    center.cmd("wg-quick up wg0")
    client1.cmd("wg-quick up wg0")
    client3.cmd("wg-quick up wg0")
    client4.cmd("wg-quick up wg0")

    info("*** Test the connection\n")
    test_connection(client1, "192.168.0.1")
    test_connection(client3, "192.168.0.1")
    test_connection(client4, "192.168.0.1")
    test_connection(client4, "192.168.0.2")
    test_connection(client4, "192.168.0.3")

    info("*** Stopping network\n")
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
    info("*** Test the connection\n")
    info("* Ping test count: %d" % PING_COUNT)
    ret = source_container.cmd("ping -c " + str(PING_COUNT) + " " + target_ip)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    info("* Measured loss rate: {:.2f}%\n".format(measured))


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
