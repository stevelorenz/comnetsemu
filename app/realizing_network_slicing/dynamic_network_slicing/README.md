# Network Softwarization - Network Slicing - Project 1 #

## Short Introduction ##
This is Project #1 for UNM ECE-595 Network Softwarization. The goal of this project is to demonstrate how to implement a network slicing strategy in order to adapt to an emergency situation within Comnetsemu environment. The original Comnetsemu source code with all the detailed examples can be found [here](https://git.comnets.net/public-repo/comnetsemu.git). 

*First you should follow all the respective instructions indicated in the [README.md](https://git.comnets.net/public-repo/comnetsemu/-/blob/master/README.md) file of the aforementioned link in order to build and install comnetsemu environment.*

Our project implementation can be found within this directory!


A multi-hop technology us used for this emulation, i.e., we assume that there are 6 hosts (h1, h2, h3 ,h4, h5, h6) and two routers (r1, r2) in the network:

```text
h1 ----                                    ---- h4
       |  |                            |  |      
       |  |                            |  |
h2 ---- r1 ---------- 10Mbps ---------- r2 ---- h5
       |  |                            |  |
       |  |                            |  |
h3 ----                                    ---- h6
```

## Project Description: Emergency Network Slicing ##
Initially, only 4 hosts are available (h1, h2, h4, h5) and can communicate with each other in 2 pairs, i.e., (h1, h4) and (h2, h5), based on a client-server model. Initially, only 2 slices are available for the aforementioned communications, equally sharing the total capacity (10Mbps) of the (r1, r2) link and as a result the link is equally divided in 5Mbps + 5Mbps but using only 50% of the respective capacity. A new slice is then built for emergency communications between hosts (h3, h6) -- requiring 4Mbps -- and the other slices are reduced to 3Mbps + 3Mbps for the remaining communications, i.e., (h1, h4) and (h2, h5). 

```text
The flow of the project is the following:
**Step 1:** The initial network is built where the (h1, h4) and (h2, h5) communications are enabled. The (r1, r2) 10Mbps link is shared for these communications leading to 2 equal slices, i.e., 5Mbps + 5Mbps. 

**Step 2:** After K seconds the emergency scenario is activated and as a result the (h3, h6) is also enabled. One additional 4Mbps slice is automatically created in the (r1, r2) link, whereas the initial two slices are dynamically reduced to 3Mbps + 3Mbps.

**Step 3:** After K seconds, the emergency situation is over and as a result the third 4Mbps slice is deleted, and everything is back to the *Step 1* situation (where only 2 slices of 5Mbps each exist).

*Note:* This process takes place in an automatic iterative manner. 
```

This folder contains the following files:
1. my_network.py: Python script to build a network with six hosts, 2 routers and the respective links.

2. common_scenario.sh: Bash script that automatically build two virtual queues in both routers r1 and r2 for the non-emergency situation. The virtual queues are actually utilized for the (h1, h4) and (h2, h5) communications. 

3. sos_scenario.sh: Bash script that automatically build a third virtual queue/slice in both routers r1 and r2 for the emergency communication of (h3, h6). Moreover, the two initial slices that are used by (h1, h4) and (h2, h5) are decreased by 2 Mbps each.

4. emergency_slicing.py: Application that utilizes the aforementioned scripts in an automatic manner, in order to dynamically implement the network slicing strategy for the emergency communication.

### How to Run ###
You can simply run the emulation application with the following commands within the /home/vagrant/comnetsemu/app/ece_595_Project1.

1. Enabling Ryu controller to load the application and to run in the background:
```bash
$ ryu-manager emergency_slicing.py &
```

2. Starting the network with Mininet: 
```bash
$ sudo python3 my_network.py
```

*Note 1:* Please stop the running Ryu controller before starting a new Ryu controller. For example, type `htop` in the terminal to show all running processes, press the key `F4` to look for the process *ryu-manager*, then press the key `F9` to stop the process, with the key `F10` to quite `htop`.

*Note 2:* When you want to stop the mininet, please delete the topology as follows:
```bash
mininet> exit
$ sudo mn -c
```

## How to Verify ##
There are four modes to verify the slices in the non-emergency and the emergency situation:

1. ping mode: verifying connecitvity, e.g.:
*Case 1: Non-Emergency Scenario* 
```bash
mininet> pingall
*** Ping: testing ping reachability
h1 -> X X h4 X X 
h2 -> X X X h5 X 
h3 -> X X X X X 
h4 -> h1 X X X X
h5 -> X h2 X X X
h6 -> X X X X X
*** Results: 86% dropped (4/30 received)
```

*Case 2: Emergency Scenario* 
```bash
mininet> pingall
*** Ping: testing ping reachability
h1 -> X X h4 X X 
h2 -> X X X h5 X 
h3 -> X X X X h6 
h4 -> h1 X X X X
h5 -> X h2 X X X
h6 -> X X h3 X X
*** Results: 80% dropped (6/30 received)
```

2. iperf mode: verifying slices' bandwidth, e.g. (in both emergency/non-emergency situations):
*Case 1: Non-Emergency Scenario* 
```bash
mininet> iperf h1 h4
*** Iperf: testing TCP bandwidth between h1 and h4 
*** Results: ['4.78 Mbits/sec', '5.30 Mbits/sec']
mininet> iperf h2 h5
*** Iperf: testing TCP bandwidth between h2 and h5 
*** Results: ['4.78 Mbits/sec', '5.28 Mbits/sec']
mininet> iperf h3 h6
*** Iperf: testing TCP bandwidth between h3 and h6 
(No Answer - Ctrl+C to exit)
```


*Case 2: Emergency Scenario* 
```bash
mininet> iperf h1 h4
*** Iperf: testing TCP bandwidth between h1 and h4 
*** Results: ['2.81 Mbits/sec', '3.93 Mbits/sec']
mininet> iperf h2 h5
*** Iperf: testing TCP bandwidth between h2 and h5 
*** Results: ['2.59 Mbits/sec', '3.50 Mbits/sec']
mininet> iperf h3 h6
*** Iperf: testing TCP bandwidth between h3 and h6 
*** Results: ['3.66 Mbits/sec', '4.65 Mbits/sec']
```


3. iperf mode: verifying slices' bandwidth, e.g. (in both emergency/non-emergency situations):
Start listening on the h4 as server and use h1 as client:
```bash
mininet> h4 iperf -s -b 2.5M &
mininet> h1 iperf -c h4 -b 2.5MB -t 10 -i 1
```

Start listening on the h5 as server and use h2 as client:
```bash
mininet> h5 iperf -s -b 2.5M &
mininet> h2 iperf -c h5 -b 2.5M -t 10 -i 1
```

Start listening on the h6 as server and use h3 as client:
```bash
mininet> h6 iperf -s -b 3.5M &
mininet> h3 iperf -c h6 -b 3.5M -t 10 -i 1
```


4. client mode: verifying flows in each router and check the virtual queues/slices, e.g.:
```bash
mininet> sh ovs-ofctl dump-flows r1
```

```bash
mininet> sh ovs-ofctl dump-flows r2
```

## Implementation Details ##
In this project we consider that exist three pairs of client-servers, i.e., (h1, h4), (h2, h5) and (h3, h6), where the last pair is activated only in the emergency scenario. As a result, during a non-emergency scenario the routers r1 and r2 drop the packets that come from h3 and h6. Additionally, we consider that only the hosts in each pair can communicate with each other. 

Non-emergency scenario: Only 2 slices are available for the communication of (h1, h4) and (h2, h5) respectively. Each slice equally shares the total capacity (10Mbps) to 5Mbps and 5Mbps respectively. In order to simulate the aforementioned network slicing we consider two virtual queues in both r1 and r2, thus simulating the two network slices. 

Emergency Scenario: A new slice is built for the emergency communication of (h3, h6) and the respective bandwidth is equal to 4Mbps. The other two slices' bandwidth is reduced to 3Mbps and 3Mpbs respectively during this scenario. Once this emergency scenario is gone then the capacity is back to normal and the new third slice is disabled. 

Assumption: We assume that (h1, h4) and (h2, h5) only use 50% of the slices' capacity, i.e., 2.5Mbps. As a result, even in the emergency scenario there will be no problem with the channels.

Note: In order to enable the ryu manager to listen to all the available functions in the emergency_slicing.py but also to automate the process of creating a new channel during an emergency scenario we create an additional thread (except the main thread). This thread is responsible to automate the process of activateing/deactivating the emergency scenario every K seconds. 

### [FAQ](./doc/faq.md)

### [Useful Links](./doc/ref_links.md)

### Contributing

The Contributors of this project are the following:
- Georgios Fragkos: gfragkos@unm.edu 
- Nathan Patrizi  : npatrizi@unm.edu 


### Contact

Project main maintainers:

- Georgios Fragkos: gfragkos@unm.edu 
- Nathan Patrizi  : npatrizi@unm.edu 
