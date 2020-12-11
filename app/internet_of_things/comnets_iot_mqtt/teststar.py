#! /usr/bin/env python3


import time


from comnetsemu.cli import CLI
from comnetsemu.net import Containernet, VNFManager
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller



if __name__ == "__main__":


    setLogLevel("info")

    net = Containernet(controller=Controller, link=TCLink, xterms=False)
    mgr = VNFManager(net)

    info("*** Add controller\n")
    net.addController("c0")

    info("*** Creating hosts\n")
    h1 = net.addDockerHost(
        "h1", dimage="dev_test", ip="10.0.0.1", docker_args={"hostname": "h1"},
    )

    h2 = net.addDockerHost(
        "h2", dimage="dev_test", ip="10.0.0.2", docker_args={"hostname": "h2"},
    )

    h3 = net.addDockerHost(
        "h3", dimage="dev_test", ip="10.0.0.3", docker_args={"hostname": "h3"},
    )
    h4 = net.addDockerHost(
        "h4", dimage="dev_test", ip="10.0.0.4", docker_args={"hostname": "h4"},
    )

    h5 = net.addDockerHost(
        "h5", dimage="dev_test", ip="10.0.0.5", docker_args={"hostname": "h5"},
    )
    info("*** Adding switch and links\n")
    switch1 = net.addSwitch("s1")
    net.addLink(switch1, h1, bw=10, delay="10ms")
    net.addLink(switch1, h2, bw=10, delay="10ms")
    net.addLink(switch1, h3, bw=10, delay="10ms")
    net.addLink(switch1, h4, bw=10, delay="10ms")
    net.addLink(switch1, h5, bw=10, delay="10ms")
    
    info("\n*** Starting network\n")
    net.start()

    #Broker
    ad = mgr.addContainer("MQTT", "h1", "mqttbroker","sh broker.sh", docker_args={})
    time.sleep(5)
    print(ad.dins.logs().decode("utf-8"))

    #Subscriber
    add = mgr.addContainer("MSUB", "h3", "mqttsubscriber","sh subscribeh3.sh", docker_args={})
    time.sleep(5)
    print(add.dins.logs().decode("utf-8"))

    #All publishers
    adc = mgr.addContainer("MPUB1", "h2", "mqttpublisher","sh publishh2.sh", docker_args={})
    time.sleep(5)
    print(adc.dins.logs().decode("utf-8"))

    ade = mgr.addContainer("MPUB2", "h4", "mqttpublisher","sh publishh4.sh", docker_args={})
    time.sleep(5)
    print(ade.dins.logs().decode("utf-8"))

    adf = mgr.addContainer("MPUB3", "h5", "mqttpublisher","sh publishh5.sh", docker_args={})
    time.sleep(5)
    print(adf.dins.logs().decode("utf-8"))

    CLI(net)

    net.stop()
    mgr.stop()
