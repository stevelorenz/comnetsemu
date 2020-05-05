#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import comnetsemu.tool as tool
from time import sleep
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

PING_COUNT = 1


def testTopo():

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

    try:
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

        # Create whitelist
        info("*** Create firewall whitelist\n")
        router.cmd("nft add table inet filter")
        router.cmd(
            "nft add chain inet filter forward { type filter hook forward priority 0 \; policy drop \; }"
        )
        router.cmd(
            "nft add rule inet filter forward ct state established,related ip daddr 192.168.0.0/24 accept"
        )
        router.cmd("nft add rule inet filter forward ip saddr 10.0.0.0/24 accept")
        router.cmd("nft add rule inet filter forward ip saddr 192.168.0.0/24 accept")

        info(
            "*** Rewrite the present filter ruleset and create one chain for each of the 3 networks.\n"
        )
        info(
            "*** You can use the network interfaces to distinguish the traffic from the networks.\n"
        )
        info(
            "*** Additionally filter traffic to the ports 22 and 1337 on the router and the internal networks.\n"
        )

        while not check_connectivity_between_hosts(
            router, internal1, internal2, internet
        ):
            sleep(5)

    except KeyboardInterrupt:
        info("** KeyboardInterrupt detected, exit the program.\n")

    finally:
        info("*** Stopping network")
        net.stop()


def check_connectivity_between_hosts(router, internal1, internal2, internet):
    # info("\n*** Testing router\n")
    # info("** router -> internal1\n")
    if not test_connection(router, "10.0.0.2"):
        return False
    # info("** router -> internal2\n")
    if not test_connection(router, "192.168.0.2"):
        return False
    # info("** router -> internet\n")
    if not test_connection(router, "100.64.0.2"):
        return False
    # info("\n*** Testing internal1\n")
    # info("** internal1 -> internal2\n")
    if not test_connection(internal1, "192.168.0.2"):
        return False
    # info("** internal1 -> internet\n")
    if test_connection(internal1, "100.64.0.2"):
        return False
    # info("\n*** Testing internal2\n")
    # info("** internal2 -> internal1\n")
    if not test_connection(internal2, "10.0.0.2"):
        return False
    # info("** internal2 -> internet\n")
    if not test_connection(internal2, "100.64.0.2"):
        return False
    # info("\n*** Testing internet\n")
    # info("** internet -> internal1\n")
    if test_connection(internet, "10.0.0.2"):
        return False
    # info("** internet -> internal2\n")
    if test_connection(internet, "192.168.0.2"):
        return False
    # info("\n*** Checking for open ports\n")
    if check_open_port(internal1, "192.168.0.2", "22"):
        return False
    if check_open_port(internal1, "192.168.0.2", "1337"):
        return False
    if check_open_port(internal1, "192.168.0.1", "22"):
        return False
    return True


def check_open_port(source_container, target_ip, target_port):
    tmp = source_container.cmd("nmap -p " + target_port + " " + target_ip)
    if "filtered" in tmp:
        return False
    if "open" in tmp:
        return True
    else:
        return False


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
