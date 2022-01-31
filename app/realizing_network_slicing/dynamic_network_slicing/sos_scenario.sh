#!/bin/sh

# 3 slices can be mapped to 3 virtual queues!
# Creating 3 virtual queues in Router 1.
echo ' ---------------------------------------------- '
echo '*** Network Slicing: Creating 3 slices ~ Emergency Scenario ...'
echo 'Router1:'
sudo ovs-vsctl set port r1-eth1 qos=@newqos -- \
--id=@newqos create QoS type=linux-htb \
other-config:max-rate=10000000 \
queues:123=@1q \
queues:234=@2q \
queues:345=@3q -- \
--id=@1q create queue other-config:min-rate=1000000 other-config:max-rate=3000000 -- \
--id=@2q create queue other-config:min-rate=1000000 other-config:max-rate=3000000 -- \
--id=@3q create queue other-config:min-rate=1000000 other-config:max-rate=4000000 

echo ' '

# 3 slices can be mapped to 3 virtual queues!
# Creating 3 virtual queues in Router 2.
echo 'Router2:'
sudo ovs-vsctl set port r2-eth1 qos=@newqos -- \
--id=@newqos create QoS type=linux-htb \
other-config:max-rate=10000000 \
queues:123=@1q \
queues:234=@2q \
queues:345=@3q -- \
--id=@1q create queue other-config:min-rate=1000000 other-config:max-rate=3000000 -- \
--id=@2q create queue other-config:min-rate=1000000 other-config:max-rate=3000000 -- \
--id=@3q create queue other-config:min-rate=1000000 other-config:max-rate=4000000 
echo '*** End of Creating the Slices ...'
echo ' ---------------------------------------------- '

# Mapping the r1 virtual queues to hosts: (h1, h4) --> queue123, (h2, h5) --> queue234, (h3, h6) --> queue(345)
sudo ovs-ofctl add-flow r1 ip,priority=65500,nw_src=10.0.0.1,nw_dst=10.0.0.4,idle_timeout=0,actions=set_queue:123,normal
sudo ovs-ofctl add-flow r1 ip,priority=65500,nw_src=10.0.0.2,nw_dst=10.0.0.5,idle_timeout=0,actions=set_queue:234,normal
sudo ovs-ofctl add-flow r1 ip,priority=65500,nw_src=10.0.0.3,nw_dst=10.0.0.6,idle_timeout=0,actions=set_queue:345,normal
# Making sure that only these hosts can communicate with each other: (h1, h3), (h2, h4), (h3, h6)
sudo ovs-ofctl add-flow r1 ip,priority=65500,nw_src=10.0.0.1,nw_dst=10.0.0.2,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r1 ip,priority=65500,nw_src=10.0.0.1,nw_dst=10.0.0.3,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r1 ip,priority=65500,nw_src=10.0.0.1,nw_dst=10.0.0.5,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r1 ip,priority=65500,nw_src=10.0.0.1,nw_dst=10.0.0.6,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r1 ip,priority=65500,nw_src=10.0.0.2,nw_dst=10.0.0.1,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r1 ip,priority=65500,nw_src=10.0.0.2,nw_dst=10.0.0.3,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r1 ip,priority=65500,nw_src=10.0.0.2,nw_dst=10.0.0.4,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r1 ip,priority=65500,nw_src=10.0.0.2,nw_dst=10.0.0.6,idle_timeout=0,actions=drop

# Mapping the r2 virtual queues to hosts: (h1, h4) --> queue123, (h2, h5) --> queue234, (h3, h6) --> queue(345)
sudo ovs-ofctl add-flow r2 ip,priority=65500,nw_src=10.0.0.4,nw_dst=10.0.0.1,idle_timeout=0,actions=set_queue:123,normal
sudo ovs-ofctl add-flow r2 ip,priority=65500,nw_src=10.0.0.5,nw_dst=10.0.0.2,idle_timeout=0,actions=set_queue:234,normal
sudo ovs-ofctl add-flow r2 ip,priority=65500,nw_src=10.0.0.6,nw_dst=10.0.0.3,idle_timeout=0,actions=set_queue:345,normal
# Making sure that only these hosts can communicate with each other: (h1, h3), (h2, h4), (h3, h6)
sudo ovs-ofctl add-flow r2 ip,priority=65500,nw_src=10.0.0.4,nw_dst=10.0.0.5,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r2 ip,priority=65500,nw_src=10.0.0.4,nw_dst=10.0.0.6,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r2 ip,priority=65500,nw_src=10.0.0.4,nw_dst=10.0.0.2,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r2 ip,priority=65500,nw_src=10.0.0.4,nw_dst=10.0.0.3,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r2 ip,priority=65500,nw_src=10.0.0.5,nw_dst=10.0.0.4,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r2 ip,priority=65500,nw_src=10.0.0.5,nw_dst=10.0.0.6,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r2 ip,priority=65500,nw_src=10.0.0.5,nw_dst=10.0.0.1,idle_timeout=0,actions=drop
sudo ovs-ofctl add-flow r2 ip,priority=65500,nw_src=10.0.0.5,nw_dst=10.0.0.3,idle_timeout=0,actions=drop