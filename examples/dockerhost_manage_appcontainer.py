#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: This example shows how to manage application containers from one
       DockerHost instance instead of calling functions directly on manager
       object.
"""

import os
import time

import pyroute2

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet, VNFManager
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

if __name__ == "__main__":

    # Only used for auto-testing.
    AUTOTEST_MODE = os.environ.get("COMNETSEMU_AUTOTEST_MODE", 0)

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

    info("*** Adding switch and links\n")
    switch1 = net.addSwitch("s1")
    switch2 = net.addSwitch("s2")
    net.addLink(switch1, h1, bw=10, delay="10ms")
    net.addLink(switch1, switch2, bw=10, delay="10ms")
    net.addLink(switch2, h2, bw=10, delay="10ms")

    info("\n*** Starting network\n")
    net.start()

    ip_route = pyroute2.IPRoute()
    mgr_api_ip = ip_route.get_addr(label="docker0")[0].get_attr("IFA_ADDRESS")
    srv1 = mgr.addContainer("srv1", "h1", "dev_test", "bash", docker_args={})
    appcontainers = ", ".join(mgr.getAllContainers())
    print(f"*** Current deployed app containers: {appcontainers}")

    # Let the manager run the REST API server.
    mgr.runHTTPServerThread(interface="docker0", port=8000)
    time.sleep(1)

    request_url = f"{mgr_api_ip}:8000/container"
    print("**** h1 request to create a container named srv2 on itself via REST API.")
    h1.cmd(
        'curl -X POST --data \'{"name": "srv2", "dhost": "h1","dimage":"dev_test", "dcmd": "bash", "docker_args": {}}\' '
        + request_url
    )
    h1.cmd(
        'curl -X POST --data \'{"name": "srv3", "dhost": "h1","dimage":"dev_test", "dcmd": "bash", "docker_args": {}}\' '
        + request_url
    )
    time.sleep(1)
    appcontainers = ", ".join(mgr.getAllContainers())
    print(f"*** Current deployed app containers: {appcontainers}")

    print("**** h1 request to delete a container named srv3 on itself via REST API.")
    h1.cmd('curl -X DELETE --data \'{"name": "srv3"}\' ' + request_url)
    time.sleep(1)
    appcontainers = ", ".join(mgr.getAllContainers())
    print(f"*** Current deployed app containers: {appcontainers}")

    if not AUTOTEST_MODE:
        # Cannot spawn xterm for srv1 since BASH is not installed in the image:
        # echo_server.
        CLI(net)

    # Instead of remove srv1 and srv2 manually, the mgr.stop method will remove
    # all remaining app containers.
    # mgr.removeContainer("srv1")
    # mgr.removeContainer("srv2")
    net.stop()
    mgr.stop()
