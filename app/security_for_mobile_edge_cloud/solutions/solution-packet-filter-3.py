#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import comnetsemu.tool as tool
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

PING_COUNT = 3


def testTopo():
    "Create an empty network and add nodes to it."

    net = Containernet(controller=Controller, link=TCLink)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    router = net.addDockerHost(
        "router",
        dimage="sec_test",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000},
    )
    internal1 = net.addDockerHost(
        "internal1",
        dimage="sec_test",
        ip="10.0.0.2",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000},
    )
    internal2 = net.addDockerHost(
        "internal2",
        dimage="sec_test",
        ip="192.168.0.2",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )
    internet = net.addDockerHost(
        "internet",
        dimage="sec_test",
        ip="100.64.0.2",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")
    s2 = net.addSwitch("s2")
    s3 = net.addSwitch("s3")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, router, bw=100, delay="10ms")
    net.addLinkNamedIfce(s2, router, bw=100, delay="10ms")
    net.addLinkNamedIfce(s3, router, bw=100, delay="10ms")
    net.addLinkNamedIfce(s1, internal1, bw=100, delay="10ms")
    net.addLinkNamedIfce(s2, internal2, bw=100, delay="10ms")
    net.addLinkNamedIfce(s3, internet, bw=100, delay="10ms")

    info("*** Starting network\n")
    net.start()

    # Setup the router
    router.cmd("ip a a 10.0.0.1/24 dev router-s1")
    router.cmd("ip a a 192.168.0.1/24 dev router-s2")
    router.cmd("ip a a 100.64.0.1/24 dev router-s3")

    # Configure the router as default gateway
    internal1.cmd("ip r c default via 10.0.0.1")
    internal2.cmd("ip r c default via 192.168.0.1")
    internet.cmd("ip r c default via 100.64.0.1")

    # Start some services
    internal2.cmd("service ssh start")
    internal2.cmd("nc -l -p 1337 &")
    router.cmd("service ssh start")

    check_connectivity_between_hosts(router, internal1, internal2, internet)

    """
    info('*** Create firewall whitelist\n')
    router.cmd("nft add table inet filter")
    router.cmd("nft add chain inet filter forward { type filter hook forward priority 0 \; policy drop \; }")
    router.cmd("nft add rule inet filter forward ct state established,related ip daddr 10.0.0.0/24 accept")
    router.cmd("nft add rule inet filter forward ip saddr 10.0.0.0/24 accept")
    router.cmd("nft add rule inet filter forward ip saddr 192.168.0.0/24 accept")
    """

    router.cmd("nft add table inet filter")
    router.cmd(
        "nft add chain inet filter forward { type filter hook forward priority 0 \; policy drop \; }"
    )
    router.cmd(
        "nft add chain inet filter input { type filter hook input priority 0 \; policy drop \; }"
    )
    router.cmd("nft add chain inet filter forward-s1")
    router.cmd("nft add chain inet filter forward-s2")
    router.cmd("nft add chain inet filter forward-s3")

    router.cmd("nft add rule inet filter forward iif router-s1 counter jump forward-s1")
    router.cmd("nft add rule inet filter forward iif router-s2 counter jump forward-s2")
    router.cmd("nft add rule inet filter forward iif router-s3 counter jump forward-s3")

    router.cmd("nft add rule inet filter forward-s1 tcp dport {ssh, 1337} drop")
    router.cmd("nft add rule inet filter forward-s1 ip saddr 10.0.0.0/24 accept")

    router.cmd("nft add rule inet filter forward-s2 ip saddr 192.168.0.0/24 accept")
    router.cmd(
        "nft add rule inet filter forward-s3 ct state established,related ip daddr 10.0.0.0/24 accept"
    )

    check_connectivity_between_hosts(router, internal1, internal2, internet)

    info("*** Stopping network")
    net.stop()


def check_connectivity_between_hosts(router, internal1, internal2, internet):
    info("\n*** Testing router\n")
    info("** router -> internal1\n")
    test_connection(router, "10.0.0.2")
    info("** router -> internal2\n")
    test_connection(router, "192.168.0.2")
    info("** router -> internet\n")
    test_connection(router, "100.64.0.2")
    info("\n*** Testing internal1\n")
    info("** internal1 -> internal2\n")
    test_connection(internal1, "192.168.0.2")
    info("** internal1 -> internet\n")
    test_connection(internal1, "100.64.0.2")
    info("\n*** Testing internal2\n")
    info("** internal2 -> internal1\n")
    test_connection(internal2, "10.0.0.2")
    info("** internal2 -> internet\n")
    test_connection(internal2, "100.64.0.2")
    info("\n*** Testing internet\n")
    info("** internet -> internal1\n")
    test_connection(internet, "10.0.0.2")
    info("** internet -> internal2\n")
    test_connection(internet, "192.168.0.2")
    info("\n*** Checking for open ports\n")
    check_open_port(internal1, "192.168.0.2", "22")
    check_open_port(internal1, "192.168.0.2", "1337")
    check_open_port(internal1, "192.168.0.1", "22")
    info("\n")


def check_open_port(source_container, target_ip, target_port):
    tmp = source_container.cmd("nmap -p " + target_port + " " + target_ip)
    if "filtered" in tmp:
        return info("* Port " + target_port + " on " + target_ip + " is filtered\n")
    if "open" in tmp:
        return info("* Port " + target_port + " on " + target_ip + " is open\n")
    else:
        return info("* Port " + target_port + " on " + target_ip + " is closed\n")


def test_connection(source_container, target_ip):
    ret = source_container.cmd("ping -c " + str(PING_COUNT) + " " + target_ip)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    if measured == 0.0:
        return info("* Connection established\n")
    else:
        return info("* Connection denied\n")


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
