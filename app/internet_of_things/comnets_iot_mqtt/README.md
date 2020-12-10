# ComNetsIot
This simple PoC is a way to implement a sample IoT project in mininet thanks to Containernet and ComNetsEmu.


### Step 1: Getting ComNets Emulator ready
  Use the guide at this [link](https://git.comnets.net/public-repo/comnetsemu) to setup comnets emulator.

### Step2: Setup Mininet Topology
  Once ComNetsEmu is built and working, we move ahead to the the mininet topology. The topology setup in this project is a star one. We can see that in [teststar.py](https://github.com/Nibamot/ComNetsIot/blob/master/teststar.py). We configure 5 hosts to be part of the star topology as  dockerhosts. They're connected to each other through a switch. At this point we can check whether the topology setup within mininet is working or not. We will come back to the part where containers are added to the dockerhosts setup.

### Step3: Create required Docker Images
  To add containers in the setup above, we need images ready to be containerised in docker. MQTT in brief is a protocol that uses the Publish-Subscribe model. A broker is the one that relays messages to the participants in the case of a MQTT setup. A subscriber subscribes to a particular topic and publisher publishes data to various topics. The broker knows which host is a subscriber to the pertinent data. We build upon a bare-bone version of eclipse mosquitto using [Dockerfilebroker](https://github.com/Nibamot/ComNetsIot/blob/master/Dockerfilebroker), [Dockerfilesubscriber](https://github.com/Nibamot/ComNetsIot/blob/master/Dockerfilesubscriber), [Dockerfilepublisher](https://github.com/Nibamot/ComNetsIot/blob/master/Dockerfilepublisher) to create broker, publisher and subscriber.


### Step4: Start containers in Mininet
  We can also go through [broker.sh](https://github.com/Nibamot/ComNetsIot/blob/master/broker.sh) which setups the broker. The publish scripts (2,4,5) are the same basically which looks to emulate different types of sensors on the dockerhosts.
  In the main [teststar.py](https://github.com/Nibamot/ComNetsIot/blob/master/teststar.py) script we setup h1 as the broker and h2, h4, h5 as the publishers. h3 is used as the subscriber.
  We can check the the number of containers `sudo docker ps -a`.   


  Please take a look at [mosquitto_pub](https://mosquitto.org/man/mosquitto_pub-1.html), [mosquitto](https://mosquitto.org/man/mosquitto-8.html) and [mosquitto_sub](https://mosquitto.org/man/mosquitto_sub-1.html) for information regarding parameters used for  publisher, broker and subscriber.  


## How to run
`sudo python3 teststar.py` sets up the following star topology. The hosts h1, h2, h3, h4, h5 are connected to each other by a switch.

```text
h1: MQTT broker (Eclipse Mosquitto)                     10.0.0.1:1883        
    - Manages the communication between the subscriber (h3) and the publishers (h2, h4, h5s)

h2, h4, h5: Publisher (Eclipse Mosquitto)               10.0.0.2, 10.0.0.4, 10.0.0.5     
    - Publishes data received from sensors running on this node. Placeholder values are published at the moment.

h3: Subscriber (Eclipse Mosquitto)                      10.0.0.3
    - Subscribes to different topics and hence receives data sent from sensors running on the publishing nodes.
```


We can check specific logs for specific containers by using `sudo docker logs **nameofcontainer**`.
On running the same we can see the logs of a sample broker, publisher and subscriber as below.

For example:

`sudo docker logs MQTT`
```text
1607611349: mosquitto version 1.6.12 starting
1607611349: Using default config.
1607611349: Opening ipv4 listen socket on port 1883.
1607611349: Opening ipv6 listen socket on port 1883.
1607611349: mosquitto version 1.6.12 running
1607611354: New connection from 10.0.0.3 on port 1883.
1607611354: New client connected from 10.0.0.3 as mosq-nwepcmcWMLM05A7z1n (p2, c1, k60).
1607611354: No will message specified.
1607611354: Sending CONNACK to mosq-nwepcmcWMLM05A7z1n (0, 0)
1607611355: Received SUBSCRIBE from mosq-nwepcmcWMLM05A7z1n
1607611355: test/randomnumber (QoS 1)
1607611355: mosq-nwepcmcWMLM05A7z1n 1 test/randomnumber
1607611355: test/temperature (QoS 1)
1607611355: mosq-nwepcmcWMLM05A7z1n 1 test/temperature
1607611355: test/randomnumber2 (QoS 1)
1607611355: mosq-nwepcmcWMLM05A7z1n 1 test/randomnumber2
1607611355: Sending SUBACK to mosq-nwepcmcWMLM05A7z1n
1607611360: New connection from 10.0.0.2 on port 1883.
1607611360: New client connected from 10.0.0.2 as mosq-Mf3TMLZ7DbK1e9Z8Cw (p2, c1, k60).
```


In the case of the broker we can see generic information from publishers and subscriber. For example we see that the host `10.0.0.3` subscribed to the topics `randomnumber, temperature and randomnumber2`. We also see information like the publish sent from `10.0.0.2` and sent from broker to `10.0.0.3`.   

`sudo docker logs MPUB1`

```text
Client mosq-Mf3TMLZ7DbK1e9Z8Cw sending CONNECT
Client mosq-Mf3TMLZ7DbK1e9Z8Cw received CONNACK (0)
Client mosq-Mf3TMLZ7DbK1e9Z8Cw sending PUBLISH (d0, q0, r0, m1, 'test/temperature', ... (5 bytes))
Client mosq-Mf3TMLZ7DbK1e9Z8Cw sending DISCONNECT
```

We see the host go through the process of `CONNECT, CONNACK, PUBLISH and DISCONNECT`.

`sudo docker logs MSUB`
```text
Client mosq-nwepcmcWMLM05A7z1n sending CONNECT
Client mosq-nwepcmcWMLM05A7z1n received CONNACK (0)
Client mosq-nwepcmcWMLM05A7z1n sending SUBSCRIBE (Mid: 1, Topic: test/randomnumber, QoS: 1, Options: 0x00)
Client mosq-nwepcmcWMLM05A7z1n sending SUBSCRIBE (Mid: 1, Topic: test/temperature, QoS: 1, Options: 0x00)
Client mosq-nwepcmcWMLM05A7z1n sending SUBSCRIBE (Mid: 1, Topic: test/randomnumber2, QoS: 1, Options: 0x00)
Client mosq-nwepcmcWMLM05A7z1n received SUBACK
Subscribed (mid: 1): 1, 1, 1
Client mosq-nwepcmcWMLM05A7z1n received PUBLISH (d0, q0, r0, m0, 'test/temperature', ... (5 bytes))
test/temperature 17951
Client mosq-nwepcmcWMLM05A7z1n received PUBLISH (d0, q0, r0, m0, 'test/temperature', ... (5 bytes))
test/temperature 12663
Client mosq-nwepcmcWMLM05A7z1n received PUBLISH (d0, q0, r0, m0, 'test/randomnumber', ... (5 bytes))
test/randomnumber 13081
Client mosq-nwepcmcWMLM05A7z1n received PUBLISH (d0, q0, r0, m0, 'test/temperature', ... (5 bytes))
test/temperature 29120
Client mosq-nwepcmcWMLM05A7z1n received PUBLISH (d0, q0, r0, m0, 'test/randomnumber', ... (5 bytes))
test/randomnumber 12314
Client mosq-nwepcmcWMLM05A7z1n received PUBLISH (d0, q0, r0, m0, 'test/randomnumber2', ... (5 bytes))
test/randomnumber2 13910
```

We see the host go through the process of `CONNECT, CONNACK, SUBSCRIBE and SUBACK and receive PUBLISH`. We can see the size and value of the message received through the broker from the publishers.
We can save these logs using [logs script](https://github.com/Nibamot/ComNetsIot/blob/master/logs.sh) to get respective mosquitto component logs.
