#!/usr/bin/python

import time
import argparse
from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def parse_args(parser):
    parser.add_argument("-k", type=int, default=1,
                        help="Create a dumbbell with k nodes")
    parser.add_argument("-a", "--autostart", action="store_true", 
                        help="Start flows automatically (always true for k > 1)")
    return parser.parse_args()

def create_dumbbell(k, autostart=False):

    "Create an empty network and add nodes to it."

    net = Mininet(controller=Controller, link=TCLink)

    info('*** Adding controller\n')
    net.addController('c0')

    info('*** Adding source and sink nodes\n')
    sources = []
    sinks = []
    for i in range(1, k + 1):
        sources.append(net.addHost('source' + str(i)))
        sinks.append(net.addHost('sink' + str(i)))

    info('*** Adding the two gateway nodes\n')
    g1 = net.addSwitch('g1')
    g2 = net.addSwitch('g2')

    # default loss=0, do not pass explicitly as an argument
    info('*** Creating links\n')
    for source, sink in zip(sources, sinks):
        net.addLink(source, g1, bw=50*8, delay='10ms', max_queue_size=1000)
        net.addLink(g2, sink, bw=50*8, delay='10ms', max_queue_size=1000)
    net.addLink(g1, g2, bw=3*8, delay='50ms', max_queue_size=373)

    info('*** Starting network\n')
    net.start()

    if autostart:
        # start all servers first and sleep for a little duration
        for i in range(k):
            sink = sinks[i]
            cmd = "python3 destination.py --server {} &".format(sink.IP())
            print("Running '{}' at sink{}".format(cmd, i+1))
            sink.cmd(cmd)
        time.sleep(0.2)

        # start source nodes in the background except the last one
        # to avoid running net.stop() immediately
        cmd = "python3 source.py --client {} --server {} -n {}"
        for i in range(k-1):
            source = sources[i]
            sink = sinks[i]
            fcmd = cmd.format(source.IP(), sink.IP(), "source" + str(i+1))
            print("Running '{} &' at source{}".format(fcmd, i+1))
            source.cmd(fcmd + " &")
        source = sources[k-1]
        sink = sinks[k-1]
        fcmd = cmd.format(source.IP(), sink.IP(), "source" + str(k))
        print("Running '{}' at source{}".format(fcmd, k))
        text = source.cmd(fcmd)
        print(text)
    else:
        info('*** Running CLI\n')
        CLI(net)

    info('*** Stopping network')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    name = "Dumbbell network with Mininet"
    parser = argparse.ArgumentParser(name)
    args = parse_args(parser)
    assert args.k > 0, "k must be larger than zero"
    create_dumbbell(args.k, autostart=args.autostart)
