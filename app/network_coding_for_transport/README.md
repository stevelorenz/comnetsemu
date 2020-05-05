# Network Coding for Transport #

This application show how to leverage NFV/SDN to enable flexible network coding (Random Linear Network Coding) for
transport. A multi-hop chain topology is used for different emulation profiles. The goal of this application is to show
the network coding functions (packed into Docker containers as Virtualized Network Functions (VNF)) can be deployed and
operated adaptively to the links' loss rates of the underlying network topology. Assume there are N hosts (DockerHost)
in the chain topology:

```text
Programs: Client --- Encoder --- Recoder 1 --- Recoder 2 --- .... --- Recoder N-2 --- Decoder  --- Server

Topology: Host 1 --- Host 2  --- Host 3    --- Host 4    --- .... --- Host N-2    --- Host N-1 --- Host N
```

Examples in this folder are mainly developed with Python to easily demonstrate the concept.
These programs are **not** performance-oriented and optimized.
The throughput and latency performance of all coders are not good.
Contact us if you want highly optimized implementation of the concepts introduced in this book. 
For example, we have [DPDK](https://www.dpdk.org/) accelerated version (implemented with C) for low latency (sub-millisecond) Network Coding (NC) as a network function.

This folder contains following files:

1.  Dockerfile: The dockerfile to build encoder, recoder and decoder VNF Docker containers.

1.  build_kodo_lib.sh: Script to build Kodo library on the system running the Testbed. Because Kodo requires
    [Licence](http://steinwurf.com/license.html), the binaries can not be released. The dynamic library file kodo.so
    must be built firstly and located in this directory to run the emulation. This script will build the library (source
    are downloaded in "$HOME/kodo-python") and copy it to this directory.

1.  build_docker_images.sh: Script to build all coder containers.

1.  encoder.py, recoder.py, decoder.py, common.py, rawsock_helpers.py and log.py: Python program for coders and helpers.
    Since the VNF should work on network layer and handle Ethernet frames.  [Linux Packet Socket](http://man7.org/linux/man-pages/man7/packet.7.html) is used.
    These programs are copied into VNF containers when run ./build_docker_images.sh

1.  multihop_topo.py, adaptive_redundancy.py, adaptive_rlnc_sdn_controller.py and redundancy_calculator.py:
    Python programs for the multi-hop topology and different profiles (test setups/scenarios).

This application creates the chain topology with Docker hosts (require minimal seven hosts for multihop_topo.py setup)
and the links between them has loss rates (currently all links have the same and fixed loss rates).

There are two main profiles(test setups/scenarios) implemented in multihop_topo.py and adaptive_redundancy.py.

In all profiles, encoder and decoder use [on-the-fly full vector RLNC](https://github.com/steinwurf/kodo-python/blob/master/examples/encode_on_the_fly.py).
Coding parameters, including field size, generation size and payload size, are defined in [common.py](./common.py)). 
The recoder can either store-and-forward (act as a dummy relay) or recode-and-forward based on the configuration.

Before running following profiles, run following commands to prepare the required libraries and container images:

```bash
$ bash ./build_kodo_lib.sh
$ sudo bash ./build_docker_images.sh
$ sudo ./install_dependencies.sh
```

## Profile 1: Multi-hop Topology with Forwarding vs Recoding ###

In this scenario, the relays in the middle can either store-and-forward or recode-and-forward.
For each setup, UDP traffic is generated from client to server with Iperf to measure the packet losses.

You can simple run the automated emulation of forward\_vs\_recode profile with following commands:

```bash
$ sudo python3 ./multihop_topo.py
```

### Profile 2: Multi-hop Topology with Adaptive Redundancy ###

#### Motivation and Setup

This examples demonstrates how to leverage the SDN controller's knowledge about the network parameters to flexibly adapt
the redundancy created by Random Linear Network Coding (RLNC) to repair losses in the transmission.

A simple Client - Encoder - Decoder - Server topology is created with an unknown loss ratio between the encoder and decoder.
The goal of this example is to show, that the controller can estimate these losses and precisely adapt the amount of
redundancy to guarantee a certain delivery probability for each packet transmitted. 

The following figure depicts the setup:

```text
Control plane:                     SDN Controller
                                   /            \
Data plane:    Switch1 --- Switch2 --- Dummy --- Switch4 --- Switch5
                  |           |                     |           |
Hosts:         Host1       Host2                 Host3       Host4 
                  |           |                     |           |
Programs:      Client      Encoder    Loss emu.  Decoder     Server
```

#### Running the experiment

The experiment can be run with:

```bash
$ sudo python3 adaptive_redundancy.py
```

Coding parameters can be found in [common.py](./common.py)
