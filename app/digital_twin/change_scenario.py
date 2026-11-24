import time
import threading
from mininet.log import info


def linkDown(net):
    info('\n*** [scenario] h1 <-> s1 ned\n')
    net.configLinkStatus('h1', 's1', 'down')


def linkUp(net):
    info('\n*** [scenario] h1 <-> s1 opp\n')
    net.configLinkStatus('h1', 's1', 'up')


def addHost(net):
    info('\n*** [scenario] legger til h4\n')
    s1 = net.get('s1')
    h4 = net.addHost('h4', ip='10.0.0.4/8')
    link = net.addLink(h4, s1)
    s1.attach(link.intf2)            # switchen må få vite om den nye porten
    h4.configDefault()               # setter IP/MAC på h4-eth0
    h4.cmd('ping -c1 10.0.0.1')      # Ryu ser bare hosts som har sendt trafikk


def startTraffic(net):
    info('\n*** [scenario] starter trafikk h2 -> h3\n')
    h2, h3 = net.get('h2', 'h3')
    h3.cmd('iperf -s -u &')
    h2.cmd('iperf -c 10.0.0.3 -u -b 1M -t 60 &')


# (sekunder etter start, funksjon)
SCENARIO = [
    (30, linkDown),
    (45, linkUp),
    (60, addHost),
    (75, startTraffic),
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