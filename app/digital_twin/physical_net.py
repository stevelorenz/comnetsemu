from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def createNet():
    # Create an empty net and add some nodes and links to it
    net = Mininet( controller=RemoteController, switch=OVSSwitch, autoSetMacs=True )

    info( '*** Adding controller\n' )
    net.addController( 'c0', ip='127.0.0.1', port=6653 )

    info( '*** Adding hosts\n' )
    h1 = net.addHost( 'h1')
    h2 = net.addHost( 'h2')
    h3 = net.addHost( 'h3')

    info( '*** Adding switch\n' )
    s1 = net.addSwitch( 's1', protocols='OpenFlow13' )

    info( '*** Creating links\n' )
    net.addLink( h1, s1 )
    net.addLink( h2, s1 )
    net.addLink( h3, s1 )

    info( '*** Starting network\n')
    net.start()

    info( '*** Running CLI\n' )
    CLI( net )

    info( '*** Stopping network' )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    createNet()