#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import comnetsemu.tool as tool
from time import sleep
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller
import random

PING_COUNT = 1


def testTopo():

    net = Containernet(controller=Controller, link=TCLink)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    client = net.addDockerHost(
        "client",
        dimage="sec_test",
        ip="10.0.0.1/24",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000},
    )
    server = net.addDockerHost(
        "server",
        dimage="nginx",
        ip="10.0.0.2/24",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000},
    )
    attacker = net.addDockerHost(
        "attacker",
        dimage="sec_test",
        ip="10.0.0.3/24",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, client, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, server, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, attacker, bw=10, delay="10ms")

    try:
        info("*** Starting network\n")
        net.start()

        info("** client -> server\n")
        info("** " + str(test_connection(client, "10.0.0.2")) + "\n")
        info("** attacker -> server\n")
        info("** " + str(test_connection(attacker, "10.0.0.2")) + "\n")

        info(
            "*** The client and the attacker can both communicate with the server \n\n"
        )

        # Create blacklist
        info(
            "*** Create a blacklist that stops the attacker from accessing the server.\n"
        )
        info(
            "*** First create a nftables table for IPv4 and IPv6 and then add a base chain connected to the input hook.\n"
        )
        info(
            "*** Finally add a rule to the base chain that drops packets coming from the attacker (10.0.0.3).\n"
        )
        info("*** When the attacker is blocked the exercise continues.\n")

        #  Check if client can connect and attacker can not.
        while not test_connection(client, "10.0.0.2") or test_connection(
            attacker, "10.0.0.2"
        ):
            sleep(5)

        info("** client -> server\n")
        info("** " + str(test_connection(client, "10.0.0.2")) + "\n")
        test_connection(client, "10.0.0.2")
        info("** attacker -> server\n")
        info("** " + str(test_connection(attacker, "10.0.0.2")) + "\n")

        info("\n")
        info(
            "*** The attacker is blocked and the client can still access the server.\n"
        )
        info("*** The attacker changed her IP address to a different one!\n")
        info(
            "*** Implement a whitelist that only allows the client to connect to the server.\n"
        )

        attacker_ip = "10.0.0." + str(random.randint(3, 250))
        attacker.cmd("ip a f dev attacker-s1")
        attacker.cmd("ip a a " + attacker_ip + "/24 dev attacker-s1")

        info("** attacker -> server\n")
        info("** " + str(test_connection(attacker, "10.0.0.2")) + "\n")

        #  Check if client can connect and attacker can not.
        while not test_connection(client, "10.0.0.2") or test_connection(
            attacker, "10.0.0.2"
        ):
            sleep(5)

        info("\n")

        # The server can talk back to server
        info("** client -> server\n")
        info("** " + str(test_connection(client, "10.0.0.2")) + "\n")
        test_connection(client, "10.0.0.2")
        info("** attacker -> server\n")
        info("** " + str(test_connection(attacker, "10.0.0.2")) + "\n")

    except KeyboardInterrupt:
        info("** KeyboardInterrupt detected, exit the program.\n")

    finally:
        info("*** Stopping network")
        net.stop()


def test_connection(source_container, target_ip):
    ret = source_container.cmd("ping -c " + str(PING_COUNT) + " " + target_ip)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    if measured == 0.0:
        return True
    else:
        return False


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
