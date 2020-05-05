#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Test topology for FlowVisor

Ref  : https://github.com/onstutorial/onstutorial/wiki/Flowvisor-Exercise
"""

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import RemoteController


def testTopo():
    "Create an empty network and add nodes to it."

    net = Containernet(
        build=False, link=TCLink, xterms=False, autoSetMacs=True, autoStaticArp=True
    )

    info("*** Adding Controller\n")
    controller = net.addController(
        "c0", controller=RemoteController, ip="127.0.0.1", port=6633
    )

    controller.start()

    info("*** Add switches\n")
    for i in range(4):
        sw = net.addSwitch("s%d" % (i + 1), dpid="%016x" % (i + 1))
        sw.start([controller])
        sw.cmdPrint("ovs-ofctl show s%d" % (i + 1))
    sw.cmdPrint("ovs-vsctl show")

    info("Add hosts\n")
    for i in range(4):
        net.addDockerHost("h%d" % (i + 1), dimage="dev_test", ip="10.0.0.%d" % (i + 1))

    info("*** Add links\n")
    http_link_config = {"bw": 1}
    video_link_config = {"bw": 10}
    net.addLinkNamedIfce("s1", "s2", **http_link_config)
    net.addLinkNamedIfce("s2", "s4", **http_link_config)
    net.addLinkNamedIfce("s1", "s3", **video_link_config)
    net.addLinkNamedIfce("s3", "s4", **video_link_config)

    net.addLinkNamedIfce("s1", "h1", bw=100, use_htb=True)
    net.addLinkNamedIfce("s1", "h2", bw=100, use_htb=True)
    net.addLinkNamedIfce("s4", "h3", bw=100, use_htb=True)
    net.addLinkNamedIfce("s4", "h4", bw=100, use_htb=True)

    net.build()
    info("*** Starting network\n")
    net.start()

    info("*** Enter CLI\n")
    info("Use help command to get CLI usages\n")
    CLI(net)

    info("*** Stopping network")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
