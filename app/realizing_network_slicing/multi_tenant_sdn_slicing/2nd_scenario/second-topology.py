#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os

from comnetsemu.cli import CLI, spawnXtermDocker
from comnetsemu.net import Containernet, VNFManager
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller, RemoteController

if __name__ == "__main__":

    # Only used for auto-testing.
    AUTOTEST_MODE = os.environ.get("COMNETSEMU_AUTOTEST_MODE", 0)

    # Create template host, switch, and link
    hconfig = {"inNamespace": True}
    http_link_config = {"bw": 1}
    video_link_config = {"bw": 10}
    host_link_config = {}

    setLogLevel("info")

    net = Containernet(
        controller=Controller,
        link=TCLink,
        xterms=False,
        autoSetMacs=True,
        autoStaticArp=True,
    )
    mgr = VNFManager(net)

    info("*** Add controller\n")
    controller = RemoteController("c1", ip="127.0.0.1", port=6633)
    net.addController(controller)

    info("*** Creating hosts\n")
    h1 = net.addDockerHost(
        "h1",
        dimage="dev_test",
        ip="10.0.0.1",
        docker_args={"hostname": "h1"},
    )
    h2 = net.addDockerHost(
        "h2",
        dimage="dev_test",
        ip="10.0.0.2",
        docker_args={"hostname": "h2"},
    )
    h3 = net.addDockerHost(
        "h3",
        dimage="dev_test",
        ip="10.0.0.3",
        docker_args={"hostname": "h3"},
    )
    h4 = net.addDockerHost(
        "h4",
        dimage="dev_test",
        ip="10.0.0.4",
        docker_args={"hostname": "h4"},
    )
    h5 = net.addDockerHost(
        "h5",
        dimage="dev_test",
        ip="10.0.0.5",
        docker_args={"hostname": "h5"},
    )
    h6 = net.addDockerHost(
        "h6",
        dimage="dev_test",
        ip="10.0.0.6",
        docker_args={"hostname": "h6"},
    )
    h7 = net.addDockerHost(
        "h7",
        dimage="dev_test",
        ip="10.0.0.7",
        docker_args={"hostname": "h7"},
    )
    h8 = net.addDockerHost(
        "h8",
        dimage="dev_test",
        ip="10.0.0.8",
        docker_args={"hostname": "h8"},
    )

    info("*** Adding switch and links\n")

    for i in range(7):
        sconfig = {"dpid": "%016x" % (i + 1)}
        net.addSwitch("s%d" % (i + 1), protocols="OpenFlow10", **sconfig)

    # s1 = net.addSwitch("s1")
    # s2 = net.addSwitch("s2")
    # s3 = net.addSwitch("s3")
    # s4 = net.addSwitch("s4")
    # s5 = net.addSwitch("s5")
    # s6 = net.addSwitch("s6")
    # s7 = net.addSwitch("s7")

    # Add switch links
    net.addLink("s1", "s3", **http_link_config)
    net.addLink("s1", "s4", **http_link_config)
    net.addLink("s2", "s4", **http_link_config)
    net.addLink("s2", "s5", **http_link_config)
    net.addLink("s3", "s6", **http_link_config)
    net.addLink("s4", "s6", **http_link_config)
    net.addLink("s4", "s7", **http_link_config)
    net.addLink("s5", "s7", **http_link_config)

    # Add host links
    net.addLink("h1", "s1", **host_link_config)
    net.addLink("h2", "s1", **host_link_config)
    net.addLink("h3", "s2", **host_link_config)
    net.addLink("h4", "s2", **host_link_config)
    net.addLink("h5", "s6", **host_link_config)
    net.addLink("h6", "s6", **host_link_config)
    net.addLink("h7", "s7", **host_link_config)
    net.addLink("h8", "s7", **host_link_config)

    info("\n*** Starting network\n")
    net.start()

    srv4 = mgr.addContainer(
        "srv4",
        "h4",
        "echo_server",
        "python /home/server.py",
        docker_args={},
    )
    srv7 = mgr.addContainer(
        "srv7",
        "h7",
        "echo_server",
        "python /home/server.py",
        docker_args={},
    )
    srv8 = mgr.addContainer(
        "srv8",
        "h8",
        "echo_server",
        "python /home/server.py",
        docker_args={},
    )
    srv1 = mgr.addContainer("srv1", "h1", "dev_test", "bash", docker_args={})
    srv2 = mgr.addContainer("srv2", "h2", "dev_test", "bash", docker_args={})
    srv3 = mgr.addContainer("srv3", "h3", "dev_test", "bash", docker_args={})
    srv5 = mgr.addContainer("srv5", "h5", "dev_test", "bash", docker_args={})
    srv6 = mgr.addContainer("srv6", "h6", "dev_test", "bash", docker_args={})

    if not AUTOTEST_MODE:
        # Cannot spawn xterm for srv1 since BASH is not installed in the image:
        # echo_server.
        spawnXtermDocker("srv3")
        CLI(net)

    mgr.removeContainer("srv1")
    mgr.removeContainer("srv2")
    mgr.removeContainer("srv3")
    mgr.removeContainer("srv4")
    mgr.removeContainer("srv5")
    mgr.removeContainer("srv6")
    mgr.removeContainer("srv7")
    mgr.removeContainer("srv8")
    net.stop()
    mgr.stop()
