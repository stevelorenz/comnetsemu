# Comparison #

## ComNetsEmu and Mininet ##

MARK: Detailed comparison can be found in the book.

Check the homepage of [Mininet](http://mininet.org/) for this great network emulator.
One main difference of this extension is: ComNetsEmu allows developer to deploy Docker containers *INSIDE* Mininet's
hosts (Instead of Mininet's default Host or CPULimitedHost, ComNetsEmu uses Docker containers for hosts), which is
beneficial to emulate many practical compute  and network setups.
By default all Mininet's hosts share the host file system and PID space. And it is non-trivial to let the application
containers to share the networking stack of the Mininet's host. So in ComNetsEmu, the Mininet's hosts are also Docker
containers. New (heavyweight but more isolated/practical) host/node types are also listed as potential enhancements to
Mininet in [Mininet's official hackathon](https://github.com/acmsigcomm18hackathon/hackathonprojects/wiki/Mininet#enhancements-to-mininet).
ComNetsEmu aims at adding **essential** features/enhancements to Mininet for better emulations for SDN/NFV applications.

A simple example is given with a ![sketch](./figures/motivation_real_deployment.pdf) for the emulation scenario: Assume Alice wants
to send packets to Bob with random linear network coding. Packet has to be transmitted through two switches S1 and S2.
Link losses (It is not true in the wired domain, however, we just want to simulate the channel losses, packets are
dropped in the queue of the switch manually.) exit in each link on the data plane. In order to mitigate the channel
losses, the recoding should be performed.
According to the Service Function Chain proposed in [RFC 7665](https://datatracker.ietf.org/doc/rfc7665/), instead of
directly forwarding packets to S2, the S1 can redirect the packets to a host on which multiple network functions are
running. Recoding can be deployed as a virtualized network function (VNF) on NF1 or NF2 based on the channel loss rates.
The recoding VNF can also migrate between NF1 and NF2 and be adaptive to the dynamics of the channel loss rates. For
teaching purpose, we want the students can emulate all practical and real-world scenarios on NFV/SDN deployment on a
single laptop.  It should be as lightweight as possible.  So in our Testbed, the physical machines (Alice, Bob, NFs) are
emulated with Mininet Hosts. They have long-and-alive PIPEs open (stdin, stdout and stderr) that can be used by the
Mininet manager to e.g. run arbitrary commands during the emulation. The VNFs or cloud applications are encapsulated in
Docker containers and deployed inside each Mininet Host.  In order to emulate this, the application containers (a.k.a
internal containers) should be isolated: It should inherent from the resource isolation of corresponded Mininet Host and
also inherent the network namespace of its Mininet Host.  This is currently not supported in the Mininet's default host,
therefore ComNetsEmu replaces it with Docker host (by integrating codes from [Containernet](https://github.com/containernet/containernet))
to have a "Docker-In-Docker" (sibling containers) setup.
This approach is inspired by the design of Pod in the de-facto standard container orchestration platform Kubernetes.
