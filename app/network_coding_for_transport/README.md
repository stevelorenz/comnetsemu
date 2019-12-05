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

This folder contains following files:

1.  Dockerfile: The dockerfile to build encoder, recoder and decoder VNF containers.

2.  build_kodo_lib.sh: Script to build Kodo library on the system running the Testbed. Because Kodo requires
    [Licence](http://steinwurf.com/license.html), the binaries can not be released. The dynamic library file kodo.so must
    be built firstly and located in this directory to run the emulation. This script will build the library (source are
    downloaded in "$HOME/kodo-python") and copy it to this directory.

3.  build_docker_images.sh: Script to build all coder containers.

4.  encoder.py recoder.py decoder.py common.py rawsock_helpers.py log.py: Python program for coders and helpers. Since
    the VNF should work on network layer and handle Ethernet frames.
    [Linux Packet Socket](http://man7.org/linux/man-pages/man7/packet.7.html) is used.
    These programs are copied into VNF containers when run ./build_docker_images.sh

5.  multihop_topo.py: The emulation program. Contains the process to create the topology, deploy coder VNFs and run
    measurements (With [Iperf](https://iperf.fr/)).

You can simple run the emulation with following commands (The container images in ../../test_containers/ should be
already built):

```bash
$ bash ./build_kodo_lib.sh
$ bash ./build_docker_images.sh
$ sudo python3 ./multihop_topo.py
```

This application creates the chain topology with Docker hosts (require minimal 5 hosts) and the links between them has
loss rates (currently all links have the same and fixed loss rates).

There are multiple main profiles(test setups/scenarios) implemented in multihop_topo.py. In all profiles, encoder and
decoder use [on-the-fly full vector RLNC](https://github.com/steinwurf/kodo-python/blob/master/examples/encode_on_the_fly.py)
(field size, generation size and payload size are defined in [common.py](./common.py)).
The recode can either store-and-forward or recode-and-forward based on the configuration.

1.  mobile\_recoder\_deterministic: In this scenario, due to the latency/computation overhead. Only one recoder can
    enable the recode-and-forward mode. Other recoders perform store-and-forward. For the deterministic scenario, the
    recode function is enabled from left to right one by one.

1.  adaptive\_redundancy: All coders configure their redundancy based on the monitor statistics of the SDN controller.
    Please read the guide [adaptive_redundancy.md](./adaptive_redundancy.md) to run this profile.

For all profiles, UDP traffic is generated from Client to Server with Iperf to measure throughput and packet losses.
