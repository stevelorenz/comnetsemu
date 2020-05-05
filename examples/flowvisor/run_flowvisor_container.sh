#!/bin/bash
#
# About: Run FlowVisor docker image with host networking and interactive mode
#

docker run -it --rm --network host flowvisor:latest /bin/bash
