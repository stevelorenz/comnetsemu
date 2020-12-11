#!/bin/bash
touch broker.log
touch publisher3.log
touch publisher2.log
touch publisher1.log
touch subscriber.log
sudo docker logs MQTT > broker.log
sudo docker logs MSUB > subscriber.log
sudo docker logs MPUB1 > publisher1.log
sudo docker logs MPUB2 > publisher2.log
sudo docker logs MPUB3 > publisher3.log
