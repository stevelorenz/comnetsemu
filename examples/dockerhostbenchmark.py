#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Benchmark performance of DockerHost compared to Mininet's CPULimitedHost
"""

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller, CPULimitedHost


def run_benchmark_tests():

    # xterms=True, spawn xterms for all nodes after net.start()
    net = Containernet(controller=Controller, link=TCLink, xterms=True)

    info('*** Adding controller\n')
    net.addController('c0')

    info('*** Adding hosts\n')
    h1 = net.addDockerHost('h1_c', dimage='dev_test', ip='10.0.0.11/24',
                           cpuset_cpus="0", cpu_quota=25000)
    h2 = net.addDockerHost('h2_c', dimage='dev_test', ip='10.0.0.12/24',
                           cpuset_cpus="0", cpu_quota=25000)

    h3 = net.addHost('h3', ip='10.0.0.13/24', cls=CPULimitedHost,
                     cores="1", cpu=0.25)
    h4 = net.addHost('h4', ip='10.0.0.14/24', cls=CPULimitedHost,
                     cores="1", cpu=0.25)

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1')

    info('*** Creating links\n')
    net.addLinkNamedIfce(s1, h1, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h2, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h3, bw=10, delay='1ms', use_htb=True)
    net.addLinkNamedIfce(s1, h4, bw=10, delay='1ms', use_htb=True)

    info('*** Starting network\n')
    net.start()

    info('*** Enter CLI\n')
    info('Use help command to get CLI usages\n')
    CLI(net)

    info('*** Stopping network')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run_benchmark_tests()
