#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: This example shows how to manage application containers from one
       DockerHost instance instead of calling functions directly on manager
       object.
       This can be useful if you want to let one DockerHost node in the network
       to be the master node (like the master node in K8s) in to manage
       application containers on other worker nodes.

       In this example, h1 is the master node. h2 wants to create a APP
       container srv2_1 on it by sending ping packets to h1.
       When h1 receive the ping packet from h2, it uses REST API to request a
       creation of srv2_1 to the APPContainerManager's HTTP server.
       h1 also uses the DELETE request to remove the srv1_1 (created by the
       native API) on itself.
       Since all DockerHosts are connected to the docker0 bridge by default,
       docker0 is used as the bridge to connect DockerHosts and the
       AppContainerManager.

       For the REST API implementation, check comnetsemu/net.py for details.
"""

import os
import time

import pyroute2

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet, VNFManager
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller


def print_deployed_containers(mgr, hosts):
    """Print already deployed containers on the given DockerHosts."""
    tmp = list()
    for h in hosts:
        c = ", ".join(mgr.getContainersDhost(h))
        tmp.append(f"DockerHost: {h}, APP containers on it: {c}")

    print("*** Current deployed APP containers:")
    print("\n".join(tmp))


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
    print("*** Deploy srv1_1 on h1 with native API.")
    mgr.addContainer("srv1_1", "h1", "dev_test", "bash", docker_args={})
    print_deployed_containers(mgr, ["h1", "h2"])

    print("*** Run REST API server thread. It listens on docker0 interface")
    mgr.runRESTServerThread(ip=mgr_api_ip, port=8000)
    time.sleep(1)

    request_url = f"{mgr_api_ip}:8000/containers"
    print("**** h1 waits for one Ping message from h1.")
    h2.cmd("ping 10.0.0.1 &")
    ret = h1.cmd("tcpdump -i h1-eth0 -c 1 icmp")
    print(f"h1: output of tcpdump:\n {ret}")
    print("**** h1 request to create a container named srv2_1 on h2 via REST API.")
    h1.cmd(
        'curl -X POST --data \'{"name": "srv2_1", "dhost": "h2","dimage":"dev_test", "dcmd": "bash", "docker_args": {}}\' '
        + request_url
    )
    time.sleep(1)
    print_deployed_containers(mgr, ["h1", "h2"])

    print("**** h1 request to delete a container named srv1_1 on itself via REST API.")
    request_url += "/srv1_1"
    h1.cmd("curl -X DELETE " + request_url)
    time.sleep(1)
    print_deployed_containers(mgr, ["h1", "h2"])

    if not AUTOTEST_MODE:
        CLI(net)

    # Instead of remove srv2_1 manually, the mgr.stop method will remove all
    # remaining app containers.
    # mgr.removeContainer("srv2_1")
    net.stop()
    mgr.stop()
