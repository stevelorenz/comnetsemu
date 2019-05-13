#!/usr/bin/python

"""
relaychannel.py: example of a simple relays channel model
"""

from mininet.net import Mininet
from mininet.link import TCIntf
from mininet.node import CPULimitedHost
from mininet.topolib import TreeTopo
from mininet.util import custom, quietRun
from mininet.log import setLogLevel, info

from typing import List


def start(bw=150):
    intf = custom(TCIntf, bw=bw)
    net = Mininet(intf=intf)
    nodelist: List = []

    ### Alice ###

    h1_rx_a = net.addHost("h1_rx_a")
    nodelist.append(h1_rx_a)
    h1_tx_a = net.addHost("h1_tx_a")
    nodelist.append(h1_tx_a)

    ### Bob ###

    h2_rx_b = net.addHost("h2_rx_b")
    nodelist.append(h2_rx_b)
    h2_tx_b = net.addHost("h2_tx_b")
    nodelist.append(h2_tx_b)

    ### Relais ###

    h3_rx_a = net.addHost("h3_rx_a")
    nodelist.append(h3_rx_a)
    h3_tx_a = net.addHost("h3_tx_a")
    nodelist.append(h3_tx_a)
    h3_rx_b = net.addHost("h3_rx_b")
    nodelist.append(h3_rx_b)
    h3_tx_b = net.addHost("h3_tx_b")
    nodelist.append(h3_tx_b)

    net.addLink(h1_rx_a, h3_tx_a)
    net.addLink(h1_tx_a, h3_rx_a)

    net.addLink(h2_rx_b, h3_tx_b)
    net.addLink(h2_tx_b, h3_rx_b)

    net.start()
    info(f"*** Testing Network with {bw} Mbps bandwidth limit\n")
    net.pingAll()
    net.iperf()
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    start()
