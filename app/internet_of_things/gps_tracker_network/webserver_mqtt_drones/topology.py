#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from comnetsemu.cli import CLI, spawnXtermDocker
from comnetsemu.net import Containernet, VNFManager
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import RemoteController, Controller
    
    
if __name__ == "__main__":

    print("*** Creating the net")

    net = Containernet(controller=Controller, link=TCLink, xterms=False, autoSetMacs=False)
    
    mgr = VNFManager(net)

    print("*** Creating hosts")
    # In our topology we have 6 drones (h1->h6),
    # 1 MQTT broker (h7), 1 web server (h8) and 1 web client (h9)
    
    h1 = net.addDockerHost(
        "D1", dimage="dev_test", ip="10.0.0.1", mac="00:00:00:00:00:01", docker_args={"hostname":"drone1"}
    )
    h2 = net.addDockerHost(
        "D2", dimage="dev_test", ip="10.0.0.2", mac="00:00:00:00:00:02", docker_args={"hostname":"drone2"}
    )
    h3 = net.addDockerHost(
        "D3", dimage="dev_test", ip="10.0.0.3", mac="00:00:00:00:00:03", docker_args={"hostname":"drone3"}
    )
    h4 = net.addDockerHost(
        "D4", dimage="dev_test", ip="10.0.0.4", mac="00:00:00:00:00:04", docker_args={"hostname":"drone4"}
    )
    h5 = net.addDockerHost(
        "D5", dimage="dev_test", ip="10.0.0.5", mac="00:00:00:00:00:05", docker_args={"hostname":"drone5"}
    )
    h6 = net.addDockerHost(
        "D6", dimage="dev_test", ip="10.0.0.6", mac="00:00:00:00:00:06", docker_args={"hostname":"drone6"}
    )
    h7 = net.addDockerHost(
        "MB", dimage="dev_test", ip="10.0.0.7", mac="00:00:00:00:00:07", docker_args={"hostname":"broker"}
    )
    h8 = net.addDockerHost(
        "WS", dimage="dev_test", ip="10.0.0.8", mac="00:00:00:00:00:08", docker_args={"hostname":"server"}
    )
    h9 = net.addDockerHost(
        "WC", dimage="dev_test", ip="10.0.0.9", mac="00:00:00:00:00:09", docker_args={"hostname":"client"}
    )

    print("*** Creating switches")
    switch1 = net.addSwitch("s1")
    switch2 = net.addSwitch("s2")
    switch3 = net.addSwitch("s3")
    switch4 = net.addSwitch("s4")
    
    print("*** Creating links")
    # From broker to central switch
    net.addLink(switch4, h7, bw=10, delay="10ms")
    
    # From the central switch to the switches
    net.addLink(switch1, switch4, bw=10, delay="10ms")
    net.addLink(switch2, switch4, bw=10, delay="10ms")
    net.addLink(switch3, switch4, bw=10, delay="10ms")
    
    # From switch 1 to hosts
    net.addLink(switch1, h8, bw=10, delay="10ms")
    net.addLink(switch1, h9, bw=10, delay="10ms")
    
    # From switch 2 to drones 1,2,3
    net.addLink(switch2, h1, bw=10, delay="10ms")
    net.addLink(switch2, h2, bw=10, delay="10ms")
    net.addLink(switch2, h3, bw=10, delay="10ms")
    
    # From switch 3 to drones 4,5,6
    net.addLink(switch3, h4, bw=10, delay="10ms")
    net.addLink(switch3, h5, bw=10, delay="10ms")
    net.addLink(switch3, h6, bw=10, delay="10ms")
    
    print("*** Starting the network")
    net.start()
    
    print("*** Connecting nodes")
    os.system("sudo bash ./connect_nodes.sh")
    
    print("*** Adding the MQTT broker")
    srv7 = mgr.addContainer(
        "MQTTBroker", "MB", "broker_mqtt_broker", "/usr/sbin/mosquitto -c /mosquitto/config/mosquitto2.conf", docker_args={}
    )
    
    print("*** Adding the drones")
    srv1 = mgr.addContainer(
        "dr1", "D1", "drone_mqtt_client", "python3 /home/drone_client_mqtt.py", docker_args={}
    )
    srv2 = mgr.addContainer(
        "dr2", "D2", "drone_mqtt_client", "python3 /home/drone_client_mqtt.py", docker_args={}
    )
    srv3 = mgr.addContainer(
        "dr3", "D3", "drone_mqtt_client", "python3 /home/drone_client_mqtt.py", docker_args={}
    )
    srv4 = mgr.addContainer(
        "dr4", "D4", "drone_mqtt_client", "python3 /home/drone_client_mqtt.py", docker_args={}
    )
    srv5 = mgr.addContainer(
        "dr5", "D5", "drone_mqtt_client", "python3 /home/drone_client_mqtt.py", docker_args={}
    )
    srv6 = mgr.addContainer(
        "dr6", "D6", "drone_mqtt_client", "python3 /home/drone_client_mqtt.py", docker_args={}
    )
    
    print("*** Adding the MQTT client")
    srv8 = mgr.addContainer("WebServer", "WS", "server", "", docker_args={})
    
    print("*** Adding the web server")
    srv9 = mgr.addContainer("WebClient", "WC", "client", "bash", docker_args={})
    
    spawnXtermDocker("WebClient")
    CLI(net)
    
    mgr.removeContainer("dr1")
    mgr.removeContainer("dr2")
    mgr.removeContainer("dr3")
    mgr.removeContainer("dr4")
    mgr.removeContainer("dr5")
    mgr.removeContainer("dr6")
    mgr.removeContainer("MQTTBroker")
    mgr.removeContainer("WebClient")
    mgr.removeContainer("WebServer")

    net.stop()    
    mgr.stop()
