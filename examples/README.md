# ComNetsEmu Examples #

These examples are intended for two purposes:

1. Get started using ComNetsEmu's Python API.
2. Get started with core/essential tools/libraries/frameworks used in the [application folder](../app/).

#### dockerhost.py and dockerhostcli.py

These examples show how to use Docker containers as Mininet's hosts and spawn terminals (currently only Xterm is
supported) for them.

#### dockerindocker.py

This example demonstrate how to use ComNetsEmu's API to deploy Docker container **inside** Dockerhost instance.
Docker-in-Docker(dind) is used by ComNetsEmu as an lightweight emulation for nested-Virtualization. The Dockerhost with
a internal Docker container deployed is used to **mimic** an actual physical host that runs Docker containers.

#### flowvisor

This example shows how to run [FlowVisor](https://github.com/OPENNETWORKINGLAB/flowvisor/wiki) inside Docker container.

### nftables.py:

This examples shows the basic setup of a firewall with nftables. It first creates
a table and chain to filter on the netfilter input hook and then adds a rule to
filter the traffic of IP address '10.0.0.2'. In the end the table is listed.

#### tun_ebpf.py

This example shows how to create TUN interface inside Docker host and attach XDP program to veth interface.

### wireguard.py:

This example demonstrates how to setup a Wireguard network tunnel between two
hosts. First the required keys are generated and then the Wireguard interfaces
are created and configured.
