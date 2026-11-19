from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from nullswitch import NullSwitch






#her lager vi vårt nye nett
#Siden vi vet at nettverket vi kommuniserer med har en kontroller, kan denne "hardkodes inn fra start."
def newNet():
    net = Mininet( controller=RemoteController, switch=NullSwitch )

    info( '*** Adding controller\n' )
    net.addController( 'c0' )