# Realizing Network Slicing #

## Short Introduction ##
This example demonstrates how to implement network slicing in an SDN to enable the isolation of network resources. The goal of this example is to show that the different requirements can be fulfilled on a shared physical infrastructure by using network slicing. A multi-hop topology is used for two emulation applications. Assume there are four hosts (h1, h2, h3, h4) and four switches (s1, s2, s3, s4) in the topology:

```text
h1 ----                               ---- h3
      |  |--10Mbps-- s3 --10Mbps--|  |
      |  |                        |  |
       s1                          s4
      |  |                        |  |
      |  |--1Mbps--  s2  --1Mbps--|  |
h2 ----                               ---- h4
```

This folder contains the following files:

1. network.py: Script to build a network with four hosts and four switches, bandwidth is 1Mbps and 10Mbps.

2. topology_slicing.py: Application to isolate the network topology into upper slice (h1 -> s1 -> s2 -> s4 -> h3, 10Mbps) and lower slice (h2 -> s1 -> s3 -> s4 -> h4, 1Mbps).

3. service_slicing.py: Application to isolate the service traffics into video traffic (UDP port 9999) obtaining 10Mbps and non-video traffic (the remaining services) obtaining 1Mbps.

## How to Run ##
You can simple run the emulation applications with following commands in ./app/network_slicing/.

1. Enabling Ryu controller to load each application and to run background.
    1. Application of topology slicing:
    ```bash
    $ ryu-manager topology_slicing.py &
    $ loading app topology_slicing.py
    loading app ryu.controller.ofp_handler
    instantiating app topology_slicing.py of TrafficSlicing
    instantiating app ryu.controller.ofp_handler of OFPHandler
    ```
    2. Application of service slicing:
    ```bash
    $ ryu-manager service_slicing.py &
    $ loading app service_slicing.py
    loading app ryu.controller.ofp_handler
    instantiating app service_slicing.py of TrafficSlicing
    instantiating app ryu.controller.ofp_handler of OFPHandler
    ```
2. Starting the network with Mininet:
```bash
$ sudo python3 network.py
```

Please stop the running Ryu controller before starting a new Ryu controller, e.g. 'kill pid'

## How to Verify ##
There are three modes to verify the slice:

1. ping mode: verifying connectivity, e.g.
```bash
mininet> pingall
*** Ping: testing ping reachability
h1 -> X h3 X 
h2 -> X X h4 
h3 -> h1 X X 
h4 -> X h2 X 
*** Results: 66% dropped (4/12 received)
```

2. iperf mode: verifying bandwidth
    1. Generate standard TCP traffic between two hosts:
    ```bash
    mininet> iperf h1 h3
    *** Iperf: testing TCP bandwidth between h1 and h3 
    *** Results: ['9.50 Mbits/sec', '12.4 Mbits/sec']
    mininet> iperf h2 h4
    *** Iperf: testing TCP bandwidth between h2 and h4 
    *** Results: ['958 Kbits/sec', '1.76 Mbits/sec']
    ```
    2. Generate sepecific traffic between two hosts. 

    For example, UDP connection from h1 to h3 with destination port 9999.
    
    Log on to h1 and h3 in new terminals:
    ```bash
    mininet> xterm h1 h3
    ```
    Start listening on the h3 as server:
    ```bash
    $ iperf -s -u -p 9999 -b 10M
    ```
    Start sending on the h1 as client:
    ```bash
    $ iperf -c 10.0.0.3 -u -p 9999 -b 10M -t 10 -i 1
    ```

3. client mode: verifying flows on each switch, e.g.
```bash
mininet> sh ovs-ofctl dump-flows s1
```
