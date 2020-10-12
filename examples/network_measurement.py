#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example to introduce network measurement approaches using
       well-known tools.
"""

import os
import time

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

    cwd = os.getcwd()
    info("*** Creating hosts\n")
    h1 = net.addDockerHost(
        "h1",
        dimage="network_measurement",
        ip="10.0.0.1",
        docker_args={"hostname": "h1"},
    )
    h2 = net.addDockerHost(
        "h2",
        dimage="network_measurement",
        ip="10.0.0.2",
        docker_args={
            "hostname": "h2",
            "volumes": {f"{cwd}": {"bind": "/flent_data", "mode": "rw"}},
        },
    )

    info("*** Adding switch and links\n")
    switch1 = net.addSwitch("s1")
    switch2 = net.addSwitch("s2")
    net.addLink(switch1, h1, bw=10, delay="10ms")
    net.addLink(switch1, switch2, bw=10, delay="10ms")
    net.addLink(switch2, h2, bw=10, delay="10ms")

    info("\n*** Starting network\n")
    net.start()

    info("*** Run ping and UDP latency measurement with single flow.\n")
    srv1_1 = mgr.addContainer(
        "srv1_1", "h1", "network_measurement", "sockperf server", docker_args={}
    )
    ret = h2.cmd("ping -c 10 -i 0.01 10.0.0.1")
    print(f"- Result of ping: \n{ret}")

    ret = h2.cmd("sockperf under-load -i 10.0.0.1 -t 3 --reply-every 1")
    print(f"- Result of Sockperf: \n{ret}")
    mgr.removeContainer("srv1_1")

    # Run netserver not in daemon mode, avoid container termination.
    srv1_1 = mgr.addContainer(
        "srv1_1", "h1", "network_measurement", "netserver -D", docker_args={},
    )
    # Wait netserver to start.
    time.sleep(1)

    print("** Run flent RRUL and ping tests (each 15 seconds.)")
    h2.cmd("flent rrul -p all_scaled -l 15 -H 10.0.0.1 -o /flent_data/rrul.png")
    h2.cmd("flent rrul -p ping_cdf -l 15 -H 10.0.0.1 -o /flent_data/ping.png")
    print("Generated plot and data are located in ./examples/.")

    if not AUTOTEST_MODE:
        CLI(net)

    net.stop()
    mgr.stop()
