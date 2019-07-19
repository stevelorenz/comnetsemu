# FlowVisor inside Docker Container #

The ./Dockerfile.flowvisor can be used to build a Container with FlowVisor installed. This image use a relative old
CentOS base image (6.10), which has Java 6 required by FlowVisor. The image can be built with
`bash ./build_flowvisor_image.sh`.

In order to use FlowVisor, the container can run with host network mode, namely sharing the network stack of the host
OS. So inside the FlowVisor container, the FlowVisor can listen on a host's address which is configured for SDN switches
to connect. Then the SDN controller can connect to FlowVisor. For example, this address can be `127.0.0.1:6633`, namely
the lo interface of the host OS. Run `bash ./run_flowvisor_container.sh` to run a FlowVisor container in interactive
mode with host network option. If run `ifconfig` inside the container, all interfaces of the host OS should be listed.
