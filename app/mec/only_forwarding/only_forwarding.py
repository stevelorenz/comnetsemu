#!/usr/bin/python

"""
Description
"""

import time

from comnetsemu.net import Containernet, VNFManager
from comnetsemu.cli import CLI
from comnetsemu.node import DockerHost, DockerContainer
from mininet.node import RemoteController, OVSSwitch  # , Controller, CPULimitedHost
from mininet.log import setLogLevel, info
from mininet.link import TCLink


def start() -> None:
    net = Containernet(build=False, link=TCLink, xterms=False)
    mgr = VNFManager(net)

    info("\n*** Adding Controller\n")
    controller1: RemoteController = net.addController("controller1",
                                                      controller=RemoteController,
                                                      ip="127.0.0.1",
                                                      port=6633)
    controller1.start()

    info("\n*** Adding Hosts\n")
    client1: DockerHost = net.addDockerHost(
        "client1",
        dimage="mec_test",
        ip="10.0.0.10",
        mac="00:00:00:00:00:01",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw", "/tmp/:/tmp/log:rw"]
    )
    probe1: DockerHost = net.addDockerHost(
        "probe1",
        dimage="mec_test",
        ip="10.0.0.40",
        mac="00:00:00:00:01:ff",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"]
    )
    server1: DockerHost = net.addDockerHost(
        "server1",
        dimage="mec_test",
        ip="10.0.0.21",
        mac="00:00:00:00:01:01",
        cpu_quota=25000,
        cpuset_cpus="0",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"]
    )
    server2: DockerHost = net.addDockerHost(
        "server2",
        dimage="mec_test",
        ip="10.0.0.22",
        mac="00:00:00:00:01:02",
        cpu_quota=25000,
        cpuset_cpus="0",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"]
    )

    info("\n*** Adding Switches\n")
    switch1: OVSSwitch = net.addSwitch("switch1")
    switch1.start([controller1])
    switch1.cmdPrint("ovs-vsctl show")

    info("\n*** Adding Links\n")
    net.addLink(node1=switch1,
                node2=client1,
                delay="200ms",
                use_htb=True)
    net.addLink(node1=switch1,
                node2=probe1,
                delay="50ms",
                use_htb=True)
    net.addLink(node1=switch1,
                node2=server1,
                delay="200ms",
                use_htb=True)
    net.addLink(node1=switch1,
                node2=server2,
                delay="300ms",
                use_htb=True)

    info("\n*** Starting Network\n")
    net.build()
    net.start()
    net.pingAll()  # optional

    info("\n*** Adding Docker Containers\n")
    client1_container: DockerContainer = mgr.addContainer(
        name="client1_container",
        dhost="client1",
        dimage="mec_test",
        dcmd="python3.6 /tmp/client.py")
    probe1_container: DockerContainer = mgr.addContainer(
        name="probe1_container",
        dhost="probe1",
        dimage="mec_test",
        dcmd="python3.6 /tmp/probe_agent.py")
    server1_container: DockerContainer = mgr.addContainer(
        name="server1_container",
        dhost="server1",
        dimage="mec_test",
        dcmd="python3.6 /tmp/server.py")
    server2_container: DockerContainer = mgr.addContainer(
        name="server2_container",
        dhost="server2",
        dimage="mec_test",
        dcmd="python3.6 /tmp/server.py")
    # print(f"{type(controller1)}   kkk   {type(switch1)}")
    time.sleep(2)

    print(f"client 1 : \n{client1_container.dins.logs().decode('utf-8')}\n"
          f"probe 1 : \n{probe1_container.dins.logs().decode('utf-8')}\n"
          f"server 1 : \n{server1_container.dins.logs().decode('utf-8')}\n"
          f"server 2 : \n{server2_container.dins.logs().decode('utf-8')}\n")

    # time.sleep(2)
    # CLI(net)
    time.sleep(180)

    info("\n*** Removing Docker Containers\n")
    mgr.removeContainer(client1_container.name)
    mgr.removeContainer(probe1_container.name)
    mgr.removeContainer(server1_container.name)
    mgr.removeContainer(server2_container.name)

    info("\n*** Stopping Network\n")
    net.stop()
    mgr.stop()


if __name__ == "__main__":
    setLogLevel("info")
    start()
