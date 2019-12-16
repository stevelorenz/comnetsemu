# ComNetsEmu Examples #

These examples are intended for two purposes:

1.  Get started using ComNetsEmu's Python API.
2.  Get started with core/essential tools/libraries/frameworks used in the [application folder](../app/).

#### dockerhost.py and dockerhostcli.py

These examples show how to use Docker containers as Mininet's hosts and spawn terminals (currently only Xterm is
supported) for them.

#### dockerindocker.py

This example demonstrate how to use ComNetsEmu's API to deploy Docker container **inside** Dockerhost instance.
Docker-in-Docker(dind) is used by ComNetsEmu as an lightweight emulation for nested-Virtualization.
The Dockerhost with internal Docker containers deployed is used to **mimic** an actual physical host that runs Docker containers.

#### DPDK

A basic example of running [DPDK](https://www.dpdk.org/) application inside Docker container and deploying it on ComNetsEmu.
Check the [doc](./dpdk/README.md) in the subdirectory for details.

#### mininet_demystify

Demystify technologies used in Mininet for lightweight network emulation.
Run two bash scripts inside the folder with root privilege:
-   [run.sh](./mininet_demystify/run.sh): Build a topology with three hosts connected to a single switch and run basic
    ping, iperf and Openflow tests.
-   [clean.sh](./mininet_demystify/clean.sh): Cleanup all network resources and processes created by run.sh.

#### tun_ebpf.py

This example shows how to create TUN interface inside Docker host and attach XDP program to veth interface.
This example requires installation of [BCC](https://github.com/iovisor/bcc) to manage eBPF programs.
BCC can be installed from source via [installer](../util/install.sh) with `-b` option.
