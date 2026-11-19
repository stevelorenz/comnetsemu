from mininet.net import Mininet
from mininet.node import RemoteController
from nullswitch import NullSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import json



#teller antall rutere/hosts i nettverket 
def findNumberOfHosts(fil="hosts.json"):
    with open(fil, "r") as file:
        data = json.load(file)
    return len(data)



#her lages hver host/ruter med copiverdier
def createHost():



    return





#her lager vi vårt nye nett
#Siden vi vet at nettverket vi kommuniserer med har en kontroller, kan denne "hardkodes inn fra start."
def newNet():
    net = Mininet( controller=RemoteController, switch=NullSwitch )

    info( '*** Adding controller\n' )
    net.addController( 'c0' )



    info( '*** Adding hosts\n' )
    for i in range(findNumberOfHosts()):
        createHost()
    
    
    return