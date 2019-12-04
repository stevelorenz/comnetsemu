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

#             s2
#  h11   10ms/     \10ms    h41
#     -- s1          s4 --
#  h12    14ms\     /14ms   h42
#             s3

def startIperf(host1, host2, amount, port, timeTotal, loadLevel ):
    #host2.cmd("iperf -s -u -p {} &".format(port))
    bw = float(amount) * (float(loadLevel) / float(10))
    print("Host {} to Host {} Bw: {}".format(host1.name, host2.name, bw))
    command = "iperf -c {} -u -p {} -t {} -b {}M &".format(host2.IP(), port, timeTotal, bw)
    host1.cmd(command)

def write_in_File(fileName, loadlevel):
    with open('../../reward_mininet.csv', 'a') as csvfile:
        fileWriter = csv.writer(csvfile, delimiter=',')
        fileWriter.writerow([-1, loadlevel, time.time()])

def clearingTheSaveFile():
    open('../../reward_mininet.csv', 'w').close()

def four_switches_network():
    net = Mininet(topo=None,
                  build=False,
                  ipBase='10.0.0.0/8', link=TCLink)
    # linkarray
    linkArray = []
    # importante! the load levels for measurements
    loadLevels = [10]
    print("LoadLevel: {}".format(loadLevels))
    timeTotal = 3600
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

    h41 = net.addHost('h41', cls=Host, ip='10.0.0.41', defaultRoute=None)
    h42 = net.addHost('h42', cls=Host, ip='10.0.0.42', defaultRoute=None)

    info('*** Add links\n')
    linkArray.append(net.addLink(s1, s2, delay='10ms', bw=10, max_queue_size=500))
    linkArray.append(net.addLink(s2, s4, delay='10ms', bw=10, max_queue_size=500))
    linkArray.append(net.addLink(s1, s3, delay='14ms', bw=8, max_queue_size=500))
    linkArray.append(net.addLink(s3, s4, delay='14ms', bw=8, max_queue_size=500))

    net.addLink(h11, s1)
    net.addLink(h12, s1)

    net.addLink(h41, s4)
    net.addLink(h42, s4)

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

    # erasing previous file
    clearingTheSaveFile()

    # incrementing the load
    for loadLevel in loadLevels:
    # iperf threads
        write_in_File('Reward_Mininet', loadLevel)
        time.sleep(15)
        start_new_thread(startIperf, (h11, h41, 9, 5001, timeTotal, loadLevel))
        time.sleep(0.2)
        start_new_thread(startIperf, (h12, h42, 7, 5001, timeTotal, loadLevel))
        #time.sleep(0.2)
        #start_new_thread(startIperf, (h41, h11, 9, 5002, timeTotal, loadLevel))
        #time.sleep(0.2)
        #start_new_thread(startIperf, (h42, h12, 7, 5002, timeTotal, loadLevel))
        time.sleep(timeTotal+3)
        loadLevel = loadLevel + 1
        print("restarting iperf -- loadLevel:  {}".format(loadLevel))
    # end
    write_in_File('Reward_Mininet', -1)
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')

four_switches_network()