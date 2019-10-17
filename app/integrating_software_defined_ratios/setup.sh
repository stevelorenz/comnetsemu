sudo docker network create SDR-net
sudo apt install docker-compose
sysctl net.ipv4.conf.all.forwarding=1
sudo iptables -P FORWARD ACCEPT
