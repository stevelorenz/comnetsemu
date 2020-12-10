#!/bin/sh
#SUBSCRIBER
mosquitto_sub -v -h 10.0.0.1 -t test/randomnumber2 -t test/randomnumber -t test/temperature -q 1 -d
