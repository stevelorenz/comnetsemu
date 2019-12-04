# Security for Mobile Edge Cloud #

## Introduction ##

This folder contains exercises for packet filter and secure network tunnels.
As packet filter, we use nftables, which is the state-of-the-art
packet filter on Linux systems. For securing network traffic in transit we use
WireGuard as secure network tunnel.

To run all exercises, two container images named sec_test and nginx are required.
Images can be built by running:

```bash
$ sudo ./build_docker_images.sh
```

Example usage of nftables and WireGuard is shown in ./nftables.py and ./wireguard.py.

1. nftables.py:

This examples shows the basic setup of a firewall with nftables.
It first creates a table and chain to filter on the netfilter input hook and then adds a rule to filter the traffic of IP address '10.0.0.2'.
In the end the table is listed.

2. wireguard.py:

This example demonstrates how to setup a Wireguard network tunnel between two hosts.
First the required keys are generated and then the Wireguard interfaces are created and configured.

The exercises should be completed in ascending order, starting with exercise 1.
The exercise scripts check if the tasks have been concluded and then deconstruct
the virtual networks of the exercises. Since all exercises deal with
connectivity between endpoints the Linux utility "ping" can be used to test
these connections. Further tools that are useful are "nmap" and "iperf".


This folder contains the following files:

1. Three exercises for the packet filter.

2. Two exercises for secure network tunnels.

3. A folder with the solutions to the exercise.

4. A command reference for nftables and WireGuard.


## Nftables: Exercise 1 ##

In the first exercise, we want to secure a server with a packet filter from an
attacker in the network, while not locking out the legitimate client. All three
hosts are connected to the same switch (same Layer 2 network), therefore the
filter must be implemented directly on the server. The first task is to
implement a blacklist that denies the attacker access to the server. The second
task is to implement a whitelist the only allows the client to access the
server.


```text
Client   ---- |  |
               s1  ---- Server
Attacker ---- |  |
```


## Nftables: Exercise 2 ##

The second exercise uses the same topology and scenario than exercise 1. The
whitelist from exercise 1 is still in place and the attacker is blocked from
accessing the server. Unfortunately, the server is also blocked from accessing
the internet because incoming traffic is blocked by the whitelist. The first
task is to implement a rule that allows the server to establish connections to
the internet but disallows the internet to establish connections to the server.
The second task is to rate-limit the traffic coming from the client to 10
Mbit/s.


```text
  Client ---- |  |
               s1  ---- Server ---- Internet (8.8.8.8)
Attacker ---- |  | 
```

## Nftables: Exercise 3 ##

In the third exercise, we have a router that connects three networks (s1,s2,s3)
with each other. Each of the networks contains an example host (internal1,
internal2, external). The first task is to rewrite the existing nftables ruleset
on the router to use one chain per network (split the traffic by using the
incoming interface). Then deny access to the ports 22 and 1337 on the router and
internal2.


```text
Internal1 ---- s1 ---- |  |
                        r1  ---- s2 ---- Internal2
 External ---- s3 ---- |  |
```

## Wireguard: Exercise 1 ##

In the first Wireguard exercise the client wants to access the FTP-server to
download a file. For this reason, he must transmit his password to the FTP-
server. The MitM attacker uses ARP spoofing to intercept and read the traffic.
In order to prevent the attacker from learning any passwords setup a Wireguard
tunnel between client and server.

```text
Client ---- Man-in-the-Middle ---- s1 ---- FTP-Server
```


## Wireguard: Exercise 2 ##

The second Wireguard exercise we want to connect multiple hosts via Wireguard
tunnels. In order to keep the number of connections low, we use a star topology
with center as its core. The clients (h2,h3,h4) must only open a tunnel to the
core. Instead of using Wireguard directly make use of a configuration file and
create the Wireguard interface and setup with 'wg-quick'.

Logical network setup:

```text
center ---- |  | ---- h2
             s1
    h3 ---- |  | ---- h4
```

WireGuard routing setup:

```text                  
        |  | ---- h2
       center
h2 ---- |  | ---- h4
```

