# Mobile Edge-Cloud - MEC

## Implementation Specifications / Introduction to general thoughts

Emulated is a mobile Edge-Cloud Scenario, where client is connected to an Autonomous System (AS), via Basestation (BS) for example if a case of mobile communication is assumed.
The client wants to have a task performed (up to imagination, maybe a calculation like FFT, generally speaking some kind of processing / calculation) by a Server that is located in Autonomous System.
The Basestation is the Gatewaypoint for the client to access the AS, furthermore the BS Controller takes care of finding a suitable Server for Service request from client.
Also, the client is mobile. It is assumed that client can leave area of BS_1 and while entering area of BS_2 and vice versa. Whenever client changes Basestations he still wants his service (processed in the AS hes leaving) to continue (maybe a phone call, stream, ...). When connection to a different Basestation the 'Service Delay' or 'Downtime' should be minimal. 
Therefore some kind of Handover management is necessary, that establishes synchronisation between the client request processing servers inside each AS.
Note that the client at any given moment is only connected to one specific BS and therefore only one AS. 

````text
AS_1            AS_2
|               |
|               |
BS_1            BS_2
\              /
 \            /
     Client
````

This structure now needs to be translated into something that can be implemented in mininet.
* Client -> Node / DockerHost, needs to execute an client application that sends requests
* Basestation -> OVSwitch, with custom Contoller to choose optimal Server in AS to process request
* Autonomous System -> Fat Tree topology, end Nodes are the Servers, which are modeled as DockerHosts (it is assumed that every Server offers the Option to process the Client request), Nodes inbeween are simple switches

````text
Server_1_1  Server_1_2 ... Server_1_N-1 Server_1_N          Server_2_1  Server_2_2 ... Server_2_N-1 Server_2_N          
    \           /               \           /                   \           /               \           /
       Switch          ...          Switch                         Switch          ...          Switch
          \                           /                               \                           /
                  OVSwitch_1                                                    OVSwitch_2
                       \                                                             /
                        \                                                           /
                         \                                                         /
                           ------------------------ Client -----------------------
````

For ease of implementation, currently during development the Switches inside AS are left out and the ammount of Servers in each AS is three.
Each inter-connection has a specific latency (also Bandwidth, but not a relevant Parameter) and is Loss-free.

## MEC only forwarding

In this simplified Version of the Emulation, it is assumed that client is statically connected to only one BS and the associated AS.
Focus here is the forwarding decision that is done by the OVSwitch controller.
For testing purpose, the inbetween switches in AS are left out and the amount of Servers is limited to two, for simple comparison.
 
 ````text
Server_1        Server_2
    \               /
        OVSwitch
            |
            |
         Client   
````

Based on the individual latencys and processing times, OVSwitch now has to pick the Optimal Server (each Server has identical CPU time).

* latency OVS <---> Server_1 != latency OVS <---> Server_2
* to simulate temporary stress, a server has to process the same request multiple (ten for example) times (Server under stress picked randomly)

OVS at first floods incoming packets from Client to both servers, after some time decides based on measured latency the optimal Server (Detects Link State). 
Now it is possible to forward the requests only to the optimal Server, reducing the overall load on AS.

[Max Flow Routing](https://www.researchgate.net/publication/4375185_MFMP_Max_flow_multipath_routing_algorithm)

## Handover

* rely on client side ARQ when continous packet loss (~> from handover)
* implement an active sync mechanism between both AS, parameter shall be the latency beween BS_1 and BS_2, which are the gateways for handover / sync between Servers from AS_1 and AS_2

## Use-case Scenarios 

* ideas for different kinds of requests the client could have
* focus is not on the application specification detail but on creating similar traffic and associated requirements

## Running 

Before running, a dedicated docker image needs to be created with 

```sh
sudo docker build -t dev_test -f ./Dockerfile.dev_test .
```

... ,where `dev_test` is the image name used in both, `mec` and `mec_only_forwarding` and `Dockerfile.dev_test` is the dockerfile located in `/app/mec`.

In the next step the Controllers need to be started

```sh
ryu-manager --verbose --log-file log.txt --ofp-tcp-listen-port 6633 ~/Documents/comnetsemu/app/mec/controller.py
```

The `--log-file` option is optional, but `--ofp-tcp-listen-port` should match the one in `edgecloud.py` / `only_forwarding.py` (relevant when using multiple controllers).

To launch the emulation 

```sh
sudo python3.6 ~/Documents/comnetsemu/app/mec/only_forwarding/only_forwarding.py
```
It is recommended to have a seperate terminal session for each controller and the application.


