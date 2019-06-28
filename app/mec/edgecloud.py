#!/usr/bin/python

"""
"""

import docker
import time

from mininet.net import Mininet, Containernet, VNFManager
from mininet.link import TCIntf, Intf
from mininet.node import CPULimitedHost, Controller, RemoteController, Node
from mininet.topolib import TreeTopo
from mininet.util import custom, quietRun
from mininet.log import setLogLevel, info
from mininet.cli import CLI


def cleanup() -> bool:
    try:
        client = docker.from_env()

        images = client.images.list()
        print(f"found {images.__len__()} images")
        for img in images:
            img = str(img)
            if "dev_test" in img:
                print("found \"dev_test\"")
                break
        else:
            raise Exception

        containers = client.containers.list()  # consider supplementing cleanup with "docker rm $(docker ps -aq)"
        print(f"found {containers.__len__()} containers")
        for container_id in containers:
            container_id = str(container_id).replace(">", "").split(" ")[1]
            container = client.containers.get(container_id=container_id)
            print(f"putting container {container_id} to sleep . . .")
            container.stop()
            time.sleep(2)

        return True

    except Exception:
        return False


def start() -> None:
    net = Containernet()  # use build=false ?
    mgr = VNFManager(net)

    info('*** Adding controller\n')  # run 2 instances of custom controller
    controller1 = net.addController("controller1", controller=RemoteController, port=6653)  # controller=RemoteController, ip=127.0.0.1, port=6633
    # controller2 = net.addController("controller2", controller=RemoteController, port=6633)  # controller=RemoteController, ip=127.0.0.1, port=6633
    controller1.start()
    # controller2.start()

    cleanup()

    info('*** Adding hosts\n')
    client1 = net.addDockerHost(
        "client1",
        dimage='dev_test',
        ip='10.0.0.10',
        mac="00:00:00:00:00:01",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"])

    server1_1 = net.addDockerHost(
        "server1_1",
        dimage='dev_test',
        ip='10.0.0.20',
        mac="00:00:00:00:01:01",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"])
    server1_2 = net.addDockerHost(
        "server1_2",
        dimage='dev_test',
        ip='10.0.0.20',
        mac="00:00:00:00:01:01",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"])
    server1_3 = net.addDockerHost(
        "server1_3",
        dimage='dev_test',
        ip='10.0.0.20',
        mac="00:00:00:00:01:01",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"])

    server2_1 = net.addDockerHost(
        "server2_1",
        dimage='dev_test',
        ip='10.0.0.40',
        mac="00:00:00:00:01:01",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"])
    server2_2 = net.addDockerHost(
        "server2_2",
        dimage='dev_test',
        ip='10.0.0.40',
        mac="00:00:00:00:01:01",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"])
    server2_3 = net.addDockerHost(
        "server2_3",
        dimage='dev_test',
        ip='10.0.0.40',
        mac="00:00:00:00:01:01",
        volumes=["/var/run/docker.sock:/var/run/docker.sock:rw"])

    info('*** Adding switches\n')
    switch1 = net.addSwitch('switch1')  # listenPort=6634, switch1.start([controller1])
    # switch1.start([controller1])
    switch1.cmdPrint("ovs-vsctl show")

    switch2 = net.addSwitch('switch2')  # listenPort=6634, switch1.start([controller1])
    # switch1.start([controller2])
    switch2.cmdPrint("ovs-vsctl show")
    # net.waitConnected(timeout=5, delay=.1)

    info('*** Creating links\n')
    net.addLink(node1=switch1, node2=client1)
    net.addLink(node1=switch2, node2=client1)

    net.addLink(switch1, server1_1)
    net.addLink(switch1, server1_2)
    net.addLink(switch1, server1_3)

    net.addLink(switch2, server2_1)
    net.addLink(switch2, server2_2)
    net.addLink(switch2, server2_3)

    # configure interfaces of client

    info('*** Starting network\n')
    net.start()
    # net.pingAll()

    try:
        intf: Intf = client1.intfs[1]
        intf.config(mac="00:00:00:00:00:01", ip="10.0.0.11", up=True)
        client1.setHostRoute(ip="10.0.0.11", intf="client1-eth1")
        client1.setDefaultRoute(intf="client1-eth1")
        client1.cmd("ifconfig client1-eth0 down")
        # intf: Intf = client1.intfs[0]
        # intf.config(up=False)
        # intf.config(ifconfig="client1-eth1 10.0.0.10 netmask 255.0.0.0 broadcast 10.255.255.255")
        # setHostRoute
    except Exception:
        pass
        info("err in config intfs")

    info('*** Adding Containers\n')  # sudo docker exec -it mn.server1_1 python3.6 /tmp/server1_1.py
    server1_1_container = mgr.addContainer(
        name="server1_1_container", dhost="server1_1", dimage="dev_test", dcmd="python3.6 /tmp/server.py")
    server1_2_container = mgr.addContainer(
        name="server1_2_container", dhost="server1_2", dimage="dev_test", dcmd="python3.6 /tmp/server.py")
    server1_3_container = mgr.addContainer(
        name="server1_3_container", dhost="server1_3", dimage="dev_test", dcmd="python3.6 /tmp/server.py")

    server2_1_container = mgr.addContainer(
        name="server2_1_container", dhost="server2_1", dimage="dev_test", dcmd="python3.6 /tmp/server.py")
    server2_2_container = mgr.addContainer(
        name="server2_2_container", dhost="server2_2", dimage="dev_test", dcmd="python3.6 /tmp/server.py")
    server2_3_container = mgr.addContainer(
        name="server2_3_container", dhost="server2_3", dimage="dev_test", dcmd="python3.6 /tmp/server.py")

    client1_container = mgr.addContainer(
        name="client1_container", dhost="client1", dimage="dev_test", dcmd="python3.6 /tmp/client.py")

    time.sleep(2)

    print(f"client 1 : \n{client1_container.dins.logs().decode('utf-8')}")

    print(f"server 1 : \n{server1_1_container.dins.logs().decode('utf-8')}")
    print(f"server 2 : \n{server1_2_container.dins.logs().decode('utf-8')}")
    print(f"server 3 : \n{server1_3_container.dins.logs().decode('utf-8')}")

    print(f"server 1 : \n{server2_1_container.dins.logs().decode('utf-8')}")
    print(f"server 2 : \n{server2_2_container.dins.logs().decode('utf-8')}")
    print(f"server 3 : \n{server2_3_container.dins.logs().decode('utf-8')}")

    time.sleep(2)
    try:
        pass
        info(f"info client 1 : {client1.IP()} {client1.intfs} {client1.MAC()} {client1.ports}\n")
    except:
        pass

    CLI(net)
    time.sleep(5)

    info('*** Removing Containers\n')
    mgr.removeContainer(client1_container)

    mgr.removeContainer(server1_1_container)
    mgr.removeContainer(server1_2_container)
    mgr.removeContainer(server1_3_container)

    mgr.removeContainer(server2_1_container)
    mgr.removeContainer(server2_2_container)
    mgr.removeContainer(server2_3_container)

    info('*** Stopping network\n')
    net.stop()
    mgr.stop()


if __name__ == '__main__':
    setLogLevel('info')
    start()
