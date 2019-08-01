# ComNetsEmu Examples #

These examples are intended for two purposes:

1. Get started using ComNetsEmu's Python API
2. Get started with core/essential tools/libraries/frameworks used in the [application folder](../app/)

#### dockerhost.py and dockerhostcli.py

These examples show how to use Docker containers as Mininet's hosts and spawn terminals (currently only Xterm is
supported) for them.

#### dockerindocker.py

This example demonstrate how to use ComNetsEmu's API to deploy Docker container **inside** Dockerhost instance.
Docker-in-Docker(dind) is used by ComNetsEmu as an lightweight emulation for nested-Virtualization. The Dockerhost with
a internal Docker container deployed is used to **mimic** an actual physical host that runs Docker containers.

#### nftables.py and wireguard.py

@TODO(simon): Add description.

#### tun_ebpf.py

This example shows how to create TUN interface inside Docker host and attach XDP program to veth interface.

#### flowvisor

This example shows how to run [FlowVisor](https://github.com/OPENNETWORKINGLAB/flowvisor/wiki) inside Docker container.
