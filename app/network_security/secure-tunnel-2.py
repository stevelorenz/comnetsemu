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
    h4 = net.addDockerHost('h4', dimage='sec_test', ip='10.0.0.4', cpuset_cpus="0", cpu_quota=25000)

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLinkNamedIfce(s1, h1, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h2, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h3, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h4, bw=10, delay='1ms', use_htb=True)

    info('*** Starting network\n')
    net.start()

    info('*** Create wg key pairs\n')
    h1_private_key, h1_public_key = generate_key_pair_for_host(h1)
    h2_private_key, h2_public_key = generate_key_pair_for_host(h2)
    h3_private_key, h3_public_key = generate_key_pair_for_host(h3)
    h4_private_key, h4_public_key = generate_key_pair_for_host(h4)

    info('*** Create wg interfaces\n')

    # TODO: Create a star topology with h1 as the center. Instead of using wg tool write a configuration for the
    # interface and place it in /etc/wireguard/wg0.conf, then use the wg-quick command to setup the interface.
    # There is an example how to write a multiline configuration into a file below.
    # h1.cmd("printf -- 'first line\n second line\n' > /etc/wireguard/wg0.conf")
    # The documentation of the interface configuration can be found in the manpages of the wg and wg-quick tool.

    info('*** Test the connection\n')
    # TODO: Test the connection via the test_connection method to see if you can connect via the tunnels to h1
    test_connection(h2, "10.0.0.1")
    test_connection(h3, "10.0.0.1")
    test_connection(h4, "10.0.0.1")

    info('*** Stopping network\n')
    net.stop()


def generate_key_pair_for_host(h1):
    h1.cmd("umask 077; wg genkey > privatekey")
    h1.cmd("wg pubkey < privatekey > publickey")
    h1_pubkey = h1.cmd("cat ./publickey").replace('\n', ' ').replace('\r', '')
    h1_privatekey = h1.cmd("cat ./privatekey").replace('\n', ' ').replace('\r', '')
    return h1_privatekey, h1_pubkey


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
