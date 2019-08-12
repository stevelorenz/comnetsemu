from comnetsemu.net import Containernet
# from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf

import threading
# from thread import start_new_thread


from config import Config
import json
import time
import csv
import requests

#             s2
#  h11   10ms/     \10ms    h41
#     -- s1          s4 --
#  h12    14ms\     /14ms   h42
#             s3

###################################################################
########## Scenario - 4 Hosts    ##################################
###################################################################

def reset_load_level(loadLevel):
    requests.put('http://0.0.0.0:8080/simpleswitch/params/loadLevel', data=json.dumps({"loadLevel": loadLevel}))
    requests.put('http://0.0.0.0:8080/simpleswitch/params/reset_flag', data=json.dumps({"reset_flag": True}))

def reset_iteration(iteration):
    requests.put('http://0.0.0.0:8080/simpleswitch/params/iteration', data=json.dumps({"iteration": iteration}))
    requests.put('http://0.0.0.0:8080/simpleswitch/params/iteration_flag', data=json.dumps({"iteration_flag": True}))

def startIperf(host1, host2, amount, port, timeTotal, loadLevel):
    #host2.cmd("iperf -s -u -p {} &".format(port))
    bw = float(amount) * (float(loadLevel) / float(10))
    print("Host {} to Host {} Bw: {}".format(host1.name, host2.name, bw))
    command = "iperf -c {} -u -p {} -t {} -b {}M -l 700B &".format(host2.IP(), port, timeTotal, bw)
    host1.cmd(command)

def write_in_File(fileName, logs, loadlevel):

    dir = logs
    with open('{}/{}.csv'.format(dir, fileName), 'a') as csvfile:
        fileWriter = csv.writer(csvfile, delimiter=',')
        fileWriter.writerow([loadlevel, time.time()])

def clearingSaveFile(fileName, logs):
    dir = logs
    with open('{}/{}.csv'.format(dir, fileName), 'w') as file:
        file.write("# loadlevel, timestamp \n")

def minToSec(min):
    return min * 60


def four_switches_network():
    net = Containernet(topo=None,
                  build=False,
                  ipBase='10.0.0.0/8', link=TCLink)

    # linkarray
    linkArray = []
    splitUpLoadLevelsFlag = Config.splitUpLoadLevelsFlag
    logs = Config.log_path
    # importante! the load levels for measurements
    loadLevels = Config.loadLevels
    print("LoadLevel: {}".format(loadLevels))
    timeTotal = minToSec(Config.duration_iperf_per_load_level_minutes)
    controllerIP = '127.0.0.1'
    fileName = 'timestamp_changing_load_levels_mininet'
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
    linkArray.append(net.addLink(s1, s2, delay='100ms', bw=10, max_queue_size=100))
    linkArray.append(net.addLink(s2, s4, delay='100ms', bw=10, max_queue_size=100))
    linkArray.append(net.addLink(s1, s3, delay='140ms', bw=8, max_queue_size=100))
    linkArray.append(net.addLink(s3, s4, delay='140ms', bw=8, max_queue_size=100))

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
    if not splitUpLoadLevelsFlag:
        clearingSaveFile(fileName, logs)

    i = 0
    time.sleep(15)
    # incrementing the load
    for loadLevel in loadLevels:
    # iperf threads
        # number of iterations
        if not splitUpLoadLevelsFlag:
            write_in_File(fileName, logs, loadLevel)
        # send load level

        print("(Re)starting iperf -- loadLevel:  {}".format(loadLevel))
        threading.Thread(target=startIperf,
                         args=(h11, h41, 9.5, 5001, timeTotal, loadLevel),
                         ).start()
        time.sleep(0.2)
        threading.Thread(target=startIperf,
                         args=(h12, h42, 7.5, 5001, timeTotal, loadLevel),
                         ).start()

        # start_new_thread(startIperf, (h11, h41, 9.5, 5001, timeTotal, loadLevel))
        # time.sleep(0.2)
        # start_new_thread(startIperf, (h12, h42, 7.5, 5001, timeTotal, loadLevel))

        i = i + 1
        time.sleep(timeTotal + 3)
        # check that not last one
        if i < len(loadLevels) and splitUpLoadLevelsFlag:
            reset_load_level(loadLevels[i])

    # end
    if not splitUpLoadLevelsFlag:
        write_in_File(fileName, logs, -1)
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')

four_switches_network()
