#!/usr/bin/python

"""
Description

ensure that mininet is configured to only assign IPv4 addresses to Hosts,
see: https://github.com/mininet/mininet/issues/454
"""

import time
import socket

from comnetsemu.net import Containernet, VNFManager
from comnetsemu.cli import CLI
from comnetsemu.node import DockerHost, APPContainer

from mininet.node import RemoteController, OVSSwitch, OVSController, Controller
from mininet.log import setLogLevel, info
from mininet.link import TCLink  # import last to avoid collision


def start() -> None:
    net = Containernet(build=False, link=TCLink, xterms=False)
    mgr = VNFManager(net)

    rx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx_socket.bind(("127.0.0.1", 8016))
    cnt: int = 0
    active_container: bool = False
    full_tree: bool = False

    info("\n*** Adding Controller\n")
    controller1: RemoteController = net.addController(
        "controller1", controller=RemoteController, ip="127.0.0.1", port=6633
    )
    controller1.start()

    info("\n*** Adding Hosts\n")
    client1: DockerHost = net.addDockerHost(
        "client1",
        dimage="mec_test",
        ip="10.0.0.10",
        mac="00:00:00:00:00:01",
        docker_args={"volumes": {"/tmp": {"bind": "/tmp", "mode": "rw"}}},
    )
    probe1: DockerHost = net.addDockerHost(
        "probe1",
        dimage="mec_test",
        docker_args={},
        ip="10.0.0.40",
        mac="00:00:00:00:01:ff",
    )
    server1: DockerHost = net.addDockerHost(
        "server1",
        dimage="mec_test",
        ip="10.0.0.21",
        mac="00:00:00:00:01:01",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )
    server2: DockerHost = net.addDockerHost(
        "server2",
        dimage="mec_test",
        ip="10.0.0.22",
        mac="00:00:00:00:01:02",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )
    server3: DockerHost = net.addDockerHost(
        "server3",
        dimage="mec_test",
        ip="10.0.0.23",
        mac="00:00:00:00:01:03",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )
    server4: DockerHost = net.addDockerHost(
        "server4",
        dimage="mec_test",
        ip="10.0.0.24",
        mac="00:00:00:00:01:04",
        docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
    )
    if full_tree:
        server5: DockerHost = net.addDockerHost(
            "server5",
            dimage="mec_test",
            ip="10.0.0.25",
            mac="00:00:00:00:01:05",
            docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
        )
        server6: DockerHost = net.addDockerHost(
            "server6",
            dimage="mec_test",
            ip="10.0.0.26",
            mac="00:00:00:00:01:06",
            docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
        )
        server7: DockerHost = net.addDockerHost(
            "server7",
            dimage="mec_test",
            ip="10.0.0.27",
            mac="00:00:00:00:01:07",
            docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
        )
        server8: DockerHost = net.addDockerHost(
            "server8",
            dimage="mec_test",
            ip="10.0.0.28",
            mac="00:00:00:00:01:08",
            docker_args={"cpuset_cpus": "0", "cpu_quota": 25000},
        )

    info("\n*** Adding Switches\n")
    switch1: OVSSwitch = net.addSwitch("switch1")

    switch11: OVSSwitch = net.addSwitch("switch11")
    switch12: OVSSwitch = net.addSwitch("switch12")

    switch111: OVSSwitch = net.addSwitch("switch111")
    switch112: OVSSwitch = net.addSwitch("switch112")
    switch121: OVSSwitch = net.addSwitch("switch121")
    switch122: OVSSwitch = net.addSwitch("switch122")

    switch1.start([controller1])
    switch1.cmdPrint("ovs-vsctl show")

    switch11.start([controller1])
    switch11.cmdPrint("ovs-vsctl show")
    switch12.start([controller1])
    switch12.cmdPrint("ovs-vsctl show")

    switch111.start([controller1])
    switch111.cmdPrint("ovs-vsctl show")
    switch112.start([controller1])
    switch112.cmdPrint("ovs-vsctl show")
    switch121.start([controller1])
    switch121.cmdPrint("ovs-vsctl show")
    switch122.start([controller1])
    switch122.cmdPrint("ovs-vsctl show")

    info("\n*** Adding Links\n")
    net.addLink(node1=switch1, node2=client1, delay="200ms", use_htb=True)
    net.addLink(node1=switch1, node2=probe1, delay="50ms", use_htb=True)

    net.addLink(node1=switch1, node2=switch11, delay="10ms", use_htb=True)
    if full_tree:
        net.addLink(node1=switch1, node2=switch12, delay="10ms", use_htb=True)

    net.addLink(node1=switch11, node2=switch111, delay="10ms", use_htb=True)
    net.addLink(node1=switch11, node2=switch112, delay="10ms", use_htb=True)
    if full_tree:
        net.addLink(node1=switch12, node2=switch121, delay="10ms", use_htb=True)
        net.addLink(node1=switch12, node2=switch122, delay="10ms", use_htb=True)

    net.addLink(node1=switch111, node2=server1, delay="100ms", use_htb=True)
    net.addLink(node1=switch111, node2=server2, delay="150ms", use_htb=True)
    net.addLink(node1=switch112, node2=server3, delay="200ms", use_htb=True)
    net.addLink(node1=switch112, node2=server4, delay="250ms", use_htb=True)
    if full_tree:
        net.addLink(node1=switch121, node2=server5, delay="300ms", use_htb=True)
        net.addLink(node1=switch121, node2=server6, delay="350ms", use_htb=True)
        net.addLink(node1=switch122, node2=server7, delay="400ms", use_htb=True)
        net.addLink(node1=switch122, node2=server8, delay="450ms", use_htb=True)

    info("\n*** Starting Network\n")
    net.build()
    net.start()
    net.pingAll()  # optional

    info("\n*** Adding Docker Containers\n")
    client1_container: APPContainer = mgr.addContainer(
        name="client1_container",
        dhost="client1",
        dimage="mec_test",
        docker_args={},
        dcmd="python3.6 /tmp/client.py",
    )
    probe1_container: APPContainer = mgr.addContainer(
        name="probe1_container",
        dhost="probe1",
        dimage="mec_test",
        docker_args={},
        dcmd="python3.6 /tmp/probe_agent.py",
    )

    probing_server1_container: APPContainer = mgr.addContainer(
        name="probing_server1_container",
        dhost="server1",
        dimage="mec_test",
        docker_args={},
        dcmd="python3.6 /tmp/probe_server.py",
    )
    probing_server2_container: APPContainer = mgr.addContainer(
        name="probing_server2_container",
        dhost="server2",
        dimage="mec_test",
        docker_args={},
        dcmd="python3.6 /tmp/probe_server.py",
    )
    probing_server3_container: APPContainer = mgr.addContainer(
        name="probing_server3_container",
        dhost="server3",
        dimage="mec_test",
        docker_args={},
        dcmd="python3.6 /tmp/probe_server.py",
    )
    probing_server4_container: APPContainer = mgr.addContainer(
        name="probing_server4_container",
        dhost="server4",
        dimage="mec_test",
        docker_args={},
        dcmd="python3.6 /tmp/probe_server.py",
    )
    if full_tree:
        probing_server5_container: APPContainer = mgr.addContainer(
            name="probing_server5_container",
            dhost="server5",
            dimage="mec_test",
            docker_args={},
            dcmd="python3.6 /tmp/probe_server.py",
        )
        probing_server6_container: APPContainer = mgr.addContainer(
            name="probing_server6_container",
            dhost="server6",
            dimage="mec_test",
            docker_args={},
            dcmd="python3.6 /tmp/probe_server.py",
        )
        probing_server7_container: APPContainer = mgr.addContainer(
            name="probing_server7_container",
            dhost="server7",
            dimage="mec_test",
            docker_args={},
            dcmd="python3.6 /tmp/probe_server.py",
        )
        probing_server8_container: APPContainer = mgr.addContainer(
            name="probing_server8_container",
            dhost="server8",
            dimage="mec_test",
            docker_args={},
            dcmd="python3.6 /tmp/probe_server.py",
        )

    time.sleep(5)

    print(
        f"client 1 : \n{client1_container.dins.logs().decode('utf-8')}\n"
        f"probe 1 : \n{probe1_container.dins.logs().decode('utf-8')}\n"
        f"probing server 1 : \n{probing_server1_container.dins.logs().decode('utf-8')}\n"
        f"probing server 2 : \n{probing_server2_container.dins.logs().decode('utf-8')}\n"
        f"probing server 3 : \n{probing_server3_container.dins.logs().decode('utf-8')}\n"
        f"probing server 4 : \n{probing_server4_container.dins.logs().decode('utf-8')}\n"
    )
    if full_tree:
        print(
            f"probing server 5 : \n{probing_server5_container.dins.logs().decode('utf-8')}\n"
            f"probing server 6 : \n{probing_server6_container.dins.logs().decode('utf-8')}\n"
            f"probing server 7 : \n{probing_server7_container.dins.logs().decode('utf-8')}\n"
            f"probing server 8 : \n{probing_server8_container.dins.logs().decode('utf-8')}\n"
        )

    # time.sleep(2)
    # CLI(net)
    time.sleep(30)

    server_container: APPContainer = None

    info(
        "\n*** Await REST instruction from Controller\n"
    )  # REST -> REpresentational State Transfer
    while True:
        data, addr = rx_socket.recvfrom(1024)
        _: str = data.decode()
        print(f"{_} {_[_.__len__()-1]}")
        if active_container:  # if container set, remove it
            mgr.removeContainer(server_container.name)
            time.sleep(2)  # prevent hang on waitContainerStart()
            print("removing container")
        server_container: APPContainer = mgr.addContainer(
            name="server_container",
            # update dhost appropriate to target host
            dhost=f"server{_[_.__len__()-1]}",
            dimage="mec_test",
            docker_args={},
            dcmd="python3.6 /tmp/server.py",
        )
        print(
            f"New container : \n{server_container.dins.logs().decode('utf-8')} on server{_[_.__len__()-1]}"
        )
        cnt += 1
        active_container = True
        time.sleep(10)  # dont allow container change too frequent
        if cnt > 10:
            break

    info("\n*** Removing Docker Containers\n")
    mgr.removeContainer(client1_container.name)
    mgr.removeContainer(probe1_container.name)

    mgr.removeContainer(probing_server1_container.name)
    mgr.removeContainer(probing_server2_container.name)
    mgr.removeContainer(probing_server3_container.name)
    mgr.removeContainer(probing_server4_container.name)
    if full_tree:
        mgr.removeContainer(probing_server5_container.name)
        mgr.removeContainer(probing_server6_container.name)
        mgr.removeContainer(probing_server7_container.name)
        mgr.removeContainer(probing_server8_container.name)

    info("\n*** Stopping Network\n")
    net.stop()
    mgr.stop()


if __name__ == "__main__":
    setLogLevel("info")
    start()
