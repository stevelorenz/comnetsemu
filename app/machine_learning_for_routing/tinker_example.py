from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from thread import start_new_thread
import os, stat
import json
import time
import csv
import requests
import sys
import math
sys.path.append("...")
sys.path.append("..")
sys.path.append("../controller")
sys.path.append(".")
print(os.getcwd())
print(sys.path.__str__())
from config import Config


#                s2
#  h11    10ms /     \ 10ms    h41
#     --     s1       s4 --
#  h12    14ms \     / 14ms   h42
#                s3


def four_switches_network():
    net = Mininet(topo=None,
                  build=False,
                  ipBase='10.0.0.0/8', link=TCLink)

    queue_lenght = Config.queue_lenght


    # linkarray
    controllerIP = '127.0.0.1'
    info('*** Adding controller\n')
    c0 = net.addController(name='c0',
                           controller=RemoteController,
                           ip=controllerIP,
                           protocol='tcp',
                           port=6633)

    info('*** Add switches\n')
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch)
    s2 = net.addSwitch('s2', cls=OVSKernelSwitch)
    s3 = net.addSwitch('s3', cls=OVSKernelSwitch)
    s4 = net.addSwitch('s4', cls=OVSKernelSwitch)

    info( '*** Add hosts\n')
    h11 = net.addHost('h11', cls=Host, ip='10.0.0.11', defaultRoute=None)
    h12 = net.addHost('h12', cls=Host, ip='10.0.0.12', defaultRoute=None)
    h13 = net.addHost('h13', cls=Host, ip='10.0.0.13', defaultRoute=None)

    h41 = net.addHost('h41', cls=Host, ip='10.0.0.41', defaultRoute=None)
    h42 = net.addHost('h42', cls=Host, ip='10.0.0.42', defaultRoute=None)
    h43 = net.addHost('h43', cls=Host, ip='10.0.0.43', defaultRoute=None)

    info('*** Add links\n')
    net.addLink(s1, s2, delay='10ms',use_tbf = True, bw=3, max_queue_size=queue_lenght)
    net.addLink(s2, s4, delay='10ms',use_tbf = True, bw=3, max_queue_size=queue_lenght)
    net.addLink(s1, s3, delay='14ms',use_tbf = True, bw=4, max_queue_size=queue_lenght)
    net.addLink(s3, s4, delay='14ms',use_tbf = True, bw=4, max_queue_size=queue_lenght)

    net.addLink(h11, s1)
    net.addLink(h12, s1)
    net.addLink(h13, s1)

    net.addLink(h41, s4)
    net.addLink(h42, s4)
    net.addLink(h43, s4)

    info('*** Starting network\n')
    net.build()
    info('*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info('*** Starting switches\n')
    net.get('s1').start([c0])
    net.get('s2').start([c0])
    net.get('s3').start([c0])
    net.get('s4').start([c0])

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')

four_switches_network()
