#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic test of TUN interfaces and XDP (eBPF)

The compiling and attachment of the XDP program use IOVisor/BCC, please install
it with ../util/install.sh -b before running this example.
"""

from bcc import BPF  # pylint: disable=import-error

from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

b = BPF(
    text="""
#include <uapi/linux/bpf.h>
int drop_all() {
    return XDP_DROP;
}
"""
)


def testTopo():
    "Create an empty network and add nodes to it."

    net = Containernet(controller=Controller, link=TCLink)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    h1 = net.addDockerHost(
        "h1",
        dimage="dev_test",
        ip="10.0.0.1",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8)},
    )
    h2 = net.addDockerHost(
        "h2",
        dimage="dev_test",
        ip="10.0.0.2",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8)},
    )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")

    info("*** Creating links\n")
    net.addLinkNamedIfce(s1, h1, bw=10, delay="10ms")
    net.addLinkNamedIfce(s1, h2, bw=10, delay="10ms")

    info("*** Starting network\n")
    net.start()

    info("*** Create TUN interfaces in h1\n")
    h1.cmd("ip tuntap add mode tun tun-test")
    h1.cmd("ip link set tun-test up")
    print("* Interfaces in the main namespace of h1:")
    ret = h1.cmd("ip link")
    print(ret)

    info("*** Load a XDP(eBPF) program to drop all frames sent to and from h2\n")
    fn = b.load_func("drop_all", BPF.XDP)
    b.attach_xdp("s1-h2", fn, 0)
    net.ping([h1, h2])
    info("*** Remove the XDP(eBPF) program\n")
    b.remove_xdp("s1-h2", 0)
    net.ping([h1, h2])

    info("*** Stopping network")
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    testTopo()
