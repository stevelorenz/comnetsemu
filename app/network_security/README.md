# Network Security #

## Introduction ##
This folder contains exercises for packet filter and secure network tunnels. We use nftables and Wireguard to give a hands-on introduction with
state of the art implementations for packet filters and secure network tunnels.
The exercises should be completed in ascending order, starting with exercise 1.
Besides these exercises there exist also an example implementation for both in
the ../../examples folder (nftables.py and wireguard.py).



This folder contains the following files:

1. Three exercises for the packet filter

2. Two exercises for secure network tunnels

3. A folder with the solutions to the exercise


The exercises are annotated with TODO and a description that tell you what kind
of protection should be implemented at that location. The book chapter offers
more detailed explanations on how to solve the exercises.


## Nftables: Exercise 1 ##


In the first exercise, there is a server (h3) that must be secured from an attacker (h3) while allowing the legitimate client (h1) to still access the server. All three hosts are connected to the same switch, therefore the firewall must be implemented directly on the server. The first task is to implement a blacklist that denies h3 access to the server. The second task is to implement a whitelist the only allows h1 access to the server.


```text
h1 (Client)   ---- |  |
                    s1  ---- h2 (Server)
h3 (Attacker) ---- |  |
```


## Nftables: Exercise 2 ##

The second exercise uses the same topology and scenario than exercise 1. The whitelist from exercise 1 is still in place and the attacker is blocked from accessing the server. Unfortunately h2 is also blocked from accessing the internet because incoming traffic is blocked by the whitelist. The first task is to implement a rule that allows the server to establish connections to the internet but disallows the internet to establish connections to the server. The second task is to rate-limit the traffic coming from the client to 10 Mbit/s.  


```text
h1 (Client)   ---- |  | 
                    s1  ---- h2 (Server) ---- Internet (8.8.8.8)
h3 (Attacker) ---- |  |
```

## Nftables: Exercise 3 ##

In the third exercise we have a router (r1) that connects three networks (s1,s2,s3) with each other. Each of the networks contains an example host (h1,h2,h3). The first task is to rewrite the existing nftables ruleset on the router to use one chain per network (split the traffic by using the incoming interface). Then deny access to the ports 22 and 1337 on the router and h2.


```text
h1 (Client) ---- s1 ---- |  | 
                          r1  ---- s2 ---- h2 (Client)
h3 (Client) ---- s3 ---- |  |
```

## Wireguard: Exercise 1 ##

In the first Wireguard exercise the client (h1) wants to access the FTP-server (h2) to download a file. For this reason he must transmit his password to the FTP-server. The MitM attacker (h3) uses ARP spoofing to intercept and read the traffic. In order to prevent the attacker from learning any passwords setup a Wireguard tunnel between client and server.

```text
h1 (Client) ---- h3 (Man-in-the-Middle) ---- s1 ---- h2 (FTP-Server)
```


## Wireguard: Exercise 2 ##

The second Wireguard exercise we want to connect multiple hosts via Wireguard tunnels. In order to keep the number of connections low, we use a star topology with h1 as its core. The clients (h2,h3,h4) must only open a tunnel to the core. Instead of using Wireguard directly make use of a configuration file and create the Wireguard interface and setup with 'wg-quick'.

```text
h1 (Core)   ---- |  | ---- h2 (Client)
                  s1  
h3 (Client) ---- |  | ---- h4 (Client)
```


```text
                 |  | ---- h2 (Client)
               h1 (Core)  
h3 (Client) ---- |  | ---- h4 (Client)
```









