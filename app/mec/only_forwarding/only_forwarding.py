#!/usr/bin/python

"""
Description
"""

import sys
import os
import time

sys.path.append(os.getcwd())

from comnetsemu.net import Containernet, VNFManager
from comnetsemu.cli import CLI
from mininet.node import RemoteController, Controller, CPULimitedHost
from mininet.log import setLogLevel, info
from mininet.link import TCLink


def start() -> None:
    net = Containernet(build=False, link=TCLink, xterms=False)
    mgr = VNFManager(net)

    info("*** Adding Controller\n")
    controller1 = net.addController("controller1",
                                    controller=RemoteController,
                                    ip="127.0.0.1",
                                    port=6633)
    controller1.start()

    info("*** Adding Hosts\n")

    client1 = net.addDockerHost(
        "client1",
        dimage="mec_test",
        ip="10.0.0.10",
        mac="00:00:00:00:00:01",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw", "/tmp/:/tmp/log:rw"])

    server1 = net.addDockerHost(
        "server1",
        dimage="mec_test",
        ip="10.0.0.21",
        mac="00:00:00:00:01:01",
        cpu_quota=25000,
        cpuset_cpus="0",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"])
    server2 = net.addDockerHost(
        "server2",
        dimage="mec_test",
        ip="10.0.0.22",
        mac="00:00:00:00:01:02",
        cpu_quota=25000,
        cpuset_cpus="0",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"])

    info("*** Adding Switches\n")
    switch1 = net.addSwitch("switch1")
    switch1.start([controller1])
    switch1.cmdPrint("ovs-vsctl show")

    info("*** Adding Links\n")
    net.addLink(node1=switch1,
                node2=client1,
                delay="20ms",
                use_htb=True)

    net.addLink(node1=switch1,
                node2=server1,
                delay="40ms",
                use_htb=True)
    net.addLink(node1=switch1,
                node2=server2,
                delay="50ms",
                use_htb=True)

    info("*** Starting Network\n")
    net.build()
    net.start()
    net.pingAll()  # optional

    info("*** Adding Docker Containers\n")
    client1_container = mgr.addContainer(
        name="client1_container",
        dhost="client1",
        dimage="mec_test",
        dcmd="python3.6 /tmp/client.py")

    server1_container = mgr.addContainer(
        name="server1_container",
        dhost="server1",
        dimage="mec_test",
        dcmd="python3.6 /tmp/server.py")
    server2_container = mgr.addContainer(
        name="server2_container",
        dhost="server2",
        dimage="mec_test",
        dcmd="python3.6 /tmp/server.py")

    time.sleep(2)

    print(f"client 1 : \n{client1_container.dins.logs().decode('utf-8')}\n"
          f"server 1 : \n{server1_container.dins.logs().decode('utf-8')}\n"
          f"server 2 : \n{server2_container.dins.logs().decode('utf-8')}\n")

    time.sleep(2)
    CLI(net)
    time.sleep(2)

    info("*** Removing Docker Containers\n")
    mgr.removeContainer(client1_container)

    mgr.removeContainer(server1_container)
    mgr.removeContainer(server2_container)

    info("*** Stopping Network\n")
    net.stop()
    mgr.stop()


if __name__ == "__main__":
    setLogLevel("info")
    start()
