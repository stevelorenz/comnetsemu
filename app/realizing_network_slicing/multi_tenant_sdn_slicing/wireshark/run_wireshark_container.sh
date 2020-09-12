#!/bin/bash
#
# About: Run Wireshark docker image with host networking and GUI
#

docker run -v /home/vagrant/comnetsemu/SVMN_project/wireshark:/root/wireshark --name test2 --net=host --env="DISPLAY" --volume="$HOME/.Xauthority:/root/.Xauthority:rw" costache2mihai/dockerizedwiresharkformsources

