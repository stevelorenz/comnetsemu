from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from thread import start_new_thread
import time
import csv
#                s2 (10MBits/s)
#   h11    10ms/     \10ms h41
#   h12 -- s1        s4 -- h42
#   h13    14ms\     /14ms h43
#                s3 (7MBits/s)


def four_switches_network():
    net = Mininet(topo=None,
                  build=False,
                  ipBase='10.0.0.0/8', link=TCLink)
    # linkarray
    linkArray = []

    #controllerIP = '192.168.56.129'
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
    linkArray.append(net.addLink(s1, s2, delay='10ms', bw=10, max_queue_size=500))
    linkArray.append(net.addLink(s2, s4, delay='10ms', bw=10, max_queue_size=500))
    linkArray.append(net.addLink(s1, s3, delay='14ms', bw=7, max_queue_size=500))
    linkArray.append(net.addLink(s3, s4, delay='14ms', bw=7, max_queue_size=500))

    net.addLink(h11, s1)
    net.addLink(h12, s1)
    net.addLink(h13, s1)

    net.addLink(h41, s4)
    net.addLink(h42, s4)
    net.addLink(h43, s4)

    info( '*** Starting network\n')
    net.build()
    info( '*** Starting controllers\n')
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
    setLogLevel( 'info' )

four_switches_network()
