#!/bin/sh
#mosquitto_pub

for i in 1 2 3 4 5 6 7 8 9 10
do
  mosquitto_pub -h 10.0.0.1 -t test/randomnumber2 -m $RANDOM -d  -p 1883 #--repeat 20
  sleep 5s
done
