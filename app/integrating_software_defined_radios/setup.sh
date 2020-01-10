#!/bin/bash

docker network create SDR-net
sudo apt install docker-compose
sudo sysctl net.ipv4.conf.all.forwarding=1
sudo iptables -P FORWARD ACCEPT
