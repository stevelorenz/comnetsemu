import time
import threading
from mininet.log import info


def linkDown(net):
    info('\n*** [scenario] s1 <-> s2 ned\n')
    net.configLinkStatus('s1', 's2', 'down')


def linkUp(net):
    info('\n*** [scenario] s1 <-> s2 opp\n')
    net.configLinkStatus('s1', 's2', 'up')


def addHost(net):
    info('\n*** [scenario] legger til h4\n')
    s1 = net.get('s1')
    h4 = net.addHost('h4', ip='10.0.0.4/8')
    link = net.addLink(h4, s1)
    s1.attach(link.intf2)            # switchen må få vite om den nye porten
    h4.configDefault()               # setter IP/MAC på h4-eth0
    h4.cmd('ping -c1 10.0.0.1')      # Ryu ser bare hosts som har sendt trafikk


def startTraffic(net):
    info('\n*** [scenario] starter trafikk h1 -> h3, 1 Mbit/s i 60 s\n')
    h1, h3 = net.get('h1', 'h3')
    h3.cmd('iperf -s -u > /dev/null 2>&1 &')
    h1.cmd('iperf -c %s -u -b 1M -t 60 > /dev/null 2>&1 &' % h3.IP())


# (sekunder etter start, funksjon)
SCENARIO = [
    (10, linkDown),
    (30, linkUp),
    (50, addHost),
    (70, startTraffic),
]


def runScenario(net, scenario=SCENARIO, stop=None):
    start = time.monotonic()
    for t, action in scenario:
        delay = t - (time.monotonic() - start)
        if stop is not None:
            if stop.wait(max(0, delay)):     # returnerer True hvis vi skal avbryte
                return
        else:
            time.sleep(max(0, delay))
        action(net) 
    info('\n*** [scenario] ferdig\n')


def startScenario(net, scenario=SCENARIO):
    stop = threading.Event()
    t = threading.Thread(target=runScenario, args=(net, scenario, stop), daemon=True)
    t.start()
    return stop