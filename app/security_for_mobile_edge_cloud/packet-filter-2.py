#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import comnetsemu.tool as tool
from time import sleep
import re
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
    client = net.addDockerHost(
        "client",
        dimage="sec_test",
        ip="10.0.0.1/24",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )
    server = net.addDockerHost(
        "server",
        dimage="nginx",
        ip="10.0.0.2/24",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )
    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, client, bw=100, delay="10ms")
    net.addLinkNamedIfce(s1, server, bw=100, delay="10ms")

    info("*** Starting network\n")

    try:
        net.start()

        info("** client -> server\n")
        info("** " + str(test_connection(client, "10.0.0.2")) + "\n")

        info("\n")

        # Create whitelist
        info("*** Create whitelist\n")
        server.cmd("nft add table inet filter")
        server.cmd(
            "nft add chain inet filter input { type filter hook input priority 0 \; policy drop \; }"
        )
        server.cmd("nft add rule inet filter input ip saddr 10.0.0.1 accept")

        # The server can talk back to client
        info("** server -> client\n")
        info("** " + str(test_connection(server, "10.0.0.1")) + "\n")
        # But he cannot talk to some other server on the internet, this is a problem
        info("** server -> internet\n")
        info("** " + str(test_connection(server, "8.8.8.8")) + "\n")

        info("\n")

        info(
            "*** The server can only communicate with the client because of the implemented whitelist filtering.\n"
        )
        info(
            "*** When the server wants to talk to the internet the internet cannot talk back because the incoming "
            "traffic is dropped.\n"
        )
        info(
            "*** Use the connection tracking state to allow established connections to answer the server.\n"
        )
        info("*** Do this without removing the whitelist.\n")

        while not test_connection(server, "8.8.8.8") or not test_connection(
            client, "10.0.0.2"
        ):
            sleep(5)

        info("** server -> internet\n")
        info("** " + str(test_connection(server, "8.8.8.8")) + "\n")

        info(
            "*** Now we want to make sure that the client cannot overload the server with traffic.\n"
        )
        info("*** Drop all traffic of the client that exceeds 10 Mbit/s.\n")

        # client is overdoing it a little and our server cannot handle all of its requests...
        server.cmd("iperf -s &")

        while try_to_flood_the_server(client):
            sleep(5)

        info("\n")
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


def try_to_flood_the_server(client):
    text = client.cmd("iperf -c 10.0.0.2")

    speed = re.search("[0-9]*\.*[0-9]*\sMbits", text)
    # print(speed)
    speed = float(speed[0].split(" ")[0])
    # print(speed)

    return speed > 10.0


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
