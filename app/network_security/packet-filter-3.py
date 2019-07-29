#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example of using Docker as a Mininet host
"""

import comnetsemu.tool as tool
from time import sleep
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

PING_COUNT = 3


def testTopo():
    "Create an empty network and add nodes to it."

    net = Containernet(controller=Controller, link=TCLink)

    info('*** Adding controller\n')
    net.addController('c0')

    info('*** Adding hosts\n')
    router = net.addDockerHost('router', dimage='sec_test',
                           cpuset_cpus="1", cpu_quota=25000)
    h1 = net.addDockerHost('h1', dimage='sec_test', ip='10.0.0.2',
                           cpuset_cpus="1", cpu_quota=25000)
    h2 = net.addDockerHost('h2', dimage='sec_test', ip='192.168.0.2',
                           cpuset_cpus="0", cpu_quota=25000)
    h3 = net.addDockerHost('h3', dimage='sec_test', ip='100.64.0.2',
                           cpuset_cpus="0", cpu_quota=25000)

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')

    info('*** Creating links\n')
    net.addLinkNamedIfce(s1, router, bw=100, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s2, router, bw=100, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s3, router, bw=100, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h1, bw=100, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s2, h2, bw=100, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s3, h3, bw=100, delay='1ms', use_htb=True)

    info('*** Starting network\n')
    net.start()

    # Setup the router
    router.cmd("ip a a 10.0.0.1/24 dev router-s1")
    router.cmd("ip a a 192.168.0.1/24 dev router-s2")
    router.cmd("ip a a 100.64.0.1/24 dev router-s3")

    # Configure the router as default gateway
    h1.cmd("ip r c default via 10.0.0.1")
    h2.cmd("ip r c default via 192.168.0.1")
    h3.cmd("ip r c default via 100.64.0.1")

    # Start some services
    h2.cmd("service ssh start")
    h2.cmd("nc -l -p 1337 &")
    router.cmd("service ssh start")

    check_connectivity_between_hosts(router, h1, h2, h3)

    # Create whitelist
    info('*** Create firewall whitelist\n')
    router.cmd("nft add table inet filter")
    router.cmd("nft add chain inet filter forward { type filter hook forward priority 0 \; policy drop \; }")
    router.cmd("nft add rule inet filter forward ct state established,related ip daddr 10.0.0.0/24 accept")
    router.cmd("nft add rule inet filter forward ip saddr 10.0.0.0/24 accept")
    router.cmd("nft add rule inet filter forward ip saddr 192.168.0.0/24 accept")

    # TODO: Rewrite the filter ruleset and create a chain with filter rules for each of the 3 network interfaces of the router
    # TODO: Filter traffic to the open ports 22 and 1337 on the router and h2

    check_connectivity_between_hosts(router, h1, h2, h3)

    info('*** Stopping network')
    net.stop()


def check_connectivity_between_hosts(router, h1, h2, h3):
    info("\n*** Testing router\n")
    info("** router -> h1\n")
    test_connection(router, "10.0.0.2")
    info("** router -> h2\n")
    test_connection(router, "192.168.0.2")
    info("** router -> h3\n")
    test_connection(router, "100.64.0.2")
    info("\n*** Testing h1\n")
    info("** h1 -> h2\n")
    test_connection(h1, "192.168.0.2")
    info("** h1 -> h3\n")
    test_connection(h1, "100.64.0.2")
    info("\n*** Testing h2\n")
    info("** h2 -> h1\n")
    test_connection(h2, "10.0.0.2")
    info("** h2 -> h3\n")
    test_connection(h2, "100.64.0.2")
    info("\n*** Testing h3\n")
    info("** h3 -> h1\n")
    test_connection(h3, "10.0.0.2")
    info("** h3 -> h2\n")
    test_connection(h3, "192.168.0.2")
    info("\n*** Checking for open ports\n")
    check_open_port(h1, "192.168.0.2", "22")
    check_open_port(h1, "192.168.0.2", "1337")
    check_open_port(h1, "192.168.0.1", "22")
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
        return info('* Connection established\n')
    else:
        return info('* Connection denied\n')


if __name__ == '__main__':
    setLogLevel('info')
    testTopo()
