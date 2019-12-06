#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

import comnetsemu.tool as tool
from comnetsemu.net import Containernet
from time import sleep
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
        ip="10.0.0.1",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000},
    )
    server = net.addDockerHost(
        "server",
        dimage="sec_test",
        ip="10.0.0.2",
        docker_args={"cpuset_cpus": "1", "cpu_quota": 25000},
    )
    attacker = net.addDockerHost(
        "attacker",
        dimage="sec_test",
        ip="10.0.0.3",
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

        info("*** Attacker, Client and Server setup\n")
        client.cmd("ping -c 10 10.0.0.2")
        attacker.cmd(
            "printf -- '#!/bin/bash\narpspoof -i attacker-s1 -t 10.0.0.1 10.0.0.2 >> /dev/null &\narpspoof -i attacker-s1 -t 10.0.0.2 10.0.0.1 >> /dev/null &' > spoof.sh; chmod +x spoof.sh; ./spoof.sh"
        )
        sleep(10)
        attacker.cmd("tcpdump -vvv -i attacker-s1 -B 100000 ip >> messages.log &")
        sleep(10)
        server.cmd("mkdir -p /var/run/vsftpd/empty")
        server.cmd("vsftpd &")

        info("*** Setup a tunnel to protect the ftp request from the MitM attacker!\n")
        info(
            "*** First create key pairs for the client and server and then establish a WireGuard tunnel between them\n"
        )
        info("*** Use the inner tunnel ip 192.168.0.2 for the server!\n")

        x = 0
        while not check_secure_network_tunnel(attacker, client, x):
            sleep(10)
            x = x + 1

    except KeyboardInterrupt:
        info("** KeyboardInterrupt detected, exit the program.\n")

    finally:
        info("*** Stopping network")
        net.stop()


def check_secure_network_tunnel(attacker, client, index):
    if not test_connection(client, "192.168.0.2"):
        return False
    login_at_ftp_server(client, "192.168.0.2", "password" + str(index))
    output = attacker.cmd("cat messages.log")
    for line in output.split("\n"):
        print(line)
        if "password" + str(index) in line:
            return False
    return True


def login_at_ftp_server(client_container, ftp_server_ip, password):
    # info('*** Login into ftp server\n')
    client_container.cmd(
        "printf -- '#!/bin/bash \n ftp -i -n "
        + ftp_server_ip
        + " <<EOF\n user root "
        + password
        + " \nEOF\n' > login.sh && chmod +x login.sh && ./login.sh"
    )


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
